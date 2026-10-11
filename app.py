from datetime import datetime, timezone
from functools import wraps
import os
import secrets
import uuid
from zoneinfo import ZoneInfo
from pathlib import Path
import click
from flask import Flask, abort, g, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from config import Config
from models import db, Staff, Service, Ticket, TicketEvent, Business, Branch, Membership, ServiceAssignment
from access import current_user, allowed_services, require_service
from universal import universal, display_rows, public_services, reception_services, business_day


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if app.config['PRODUCTION']:
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['DEBUG'] = False
        if not os.getenv('SECRET_KEY') or len(os.getenv('SECRET_KEY', '')) < 32:
            raise RuntimeError('Production requires SECRET_KEY with at least 32 characters')
        if not app.config['SQLALCHEMY_DATABASE_URI'].startswith(('postgresql://', 'postgresql+')):
            raise RuntimeError('Production requires an explicit PostgreSQL DATABASE_URL')
    ZoneInfo(app.config['BUSINESS_TIMEZONE'])
    if app.config['AVERAGE_SERVICE_TIME_MINUTES'] <= 0:
        raise RuntimeError('Average service time must be positive')
    if app.config['APP_STAGE'] == 'staging':
        from staging import validate_configuration
        validate_configuration(app.config)
        options = dict(app.config['SQLALCHEMY_ENGINE_OPTIONS'])
        options['connect_args'] = {**options.get('connect_args', {}), 'sslmode': 'require'}
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = options
        app.config['SESSION_COOKIE_NAME'] = 'queueless_staging'
    db.init_app(app)
    app.register_blueprint(universal)
    from api import api
    app.register_blueprint(api)
    from demo_access import configure as configure_demo_access
    configure_demo_access(app)
    from rate_limit import configure as configure_rate_limits
    configure_rate_limits(app)

    def csrf_token():
        session.setdefault('csrf_token', secrets.token_urlsafe(32))
        session.setdefault('owner_id', str(uuid.uuid4()))
        return session['csrf_token']

    def csp_nonce():
        if not hasattr(g, 'csp_nonce'):
            g.csp_nonce = secrets.token_urlsafe(24)
        return g.csp_nonce

    @app.context_processor
    def helpers():
        return {'owner_registration_enabled': app.config['OWNER_REGISTRATION_ENABLED'], 'csrf_token': csrf_token, 'csp_nonce': csp_nonce(), 'request_key': lambda: str(uuid.uuid4()), 'current_user': current_user}

    @app.before_request
    def csrf_check():
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            expected = session.get('csrf_token', '')
            actual = request.headers.get('X-CSRF-Token', request.form.get('csrf_token', '')) if request.path.startswith('/api/v1/') else request.form.get('csrf_token', '')
            if not expected or not secrets.compare_digest(expected, actual):
                abort(400, 'Invalid form token. Reload the page and retry.')

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=(), payment=(), usb=()'
        if app.config['PRODUCTION']:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
            response.headers['Content-Security-Policy'] = (
                "default-src 'self'; base-uri 'self'; object-src 'none'; "
                "frame-ancestors 'none'; form-action 'self'; connect-src 'self'; "
                "img-src 'self' data:; font-src 'self'; "
                "style-src 'self' 'unsafe-inline'; script-src 'self' 'nonce-" + csp_nonce() + "'"
            )
        if not request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.errorhandler(SQLAlchemyError)
    def database_error(error):
        db.session.rollback()
        app.logger.error('Database operation failed: %s', type(error).__name__)
        if request.path.startswith('/api/v1/'):
            return jsonify(error={'code':'database_unavailable','message':'Database temporarily unavailable. Please retry.'}),503
        return 'Database temporarily unavailable. Please retry.', 503

    @app.errorhandler(IntegrityError)
    def integrity_error(error):
        db.session.rollback()
        from werkzeug.exceptions import Conflict
        conflict=Conflict('The request conflicts with saved data. Reload and check names, prefixes and submission keys.')
        if request.path.startswith('/api/v1/'):
            return jsonify(error={'code':'conflict','message':conflict.description}),409
        return render_template('error.html',error=conflict),409

    from werkzeug.exceptions import HTTPException
    @app.errorhandler(HTTPException)
    def request_error(error):
        db.session.rollback()
        if request.path.startswith('/api/v1/'):
            response=jsonify(error={'code':error.name.lower().replace(' ','_'),'message':error.description})
            response.status_code=error.code
            if error.code == 429:
                response.headers['Retry-After']=str(error.retry_after)
            return response
        response=app.make_response((render_template('error.html',error=error),error.code))
        if error.code == 429:
            response.headers['Retry-After']=str(error.retry_after)
        return response

    def staff_required(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if current_user() is None:
                abort(401)
            return fn(*args, **kwargs)
        return wrapped

    def locked_service(service_id):
        service = db.session.scalar(select(Service).where(Service.id == service_id).with_for_update().execution_options(populate_existing=True))
        if service is None:
            abort(404)
        return service

    def event(ticket, action, staff_id=None):
        db.session.add(TicketEvent(ticket_id=ticket.id, event_type=action, staff_id=staff_id))

    def state(ticket):
        ahead = 0
        if ticket.status == 'WAITING':
            ahead = Ticket.query.filter(Ticket.service_id == ticket.service_id, Ticket.status.in_(('WAITING', 'CALLED')), Ticket.id < ticket.id).count()
        return {'status': ticket.status, 'display_number': ticket.display_number, 'people_ahead': ahead,
                'estimated_time': ahead * ticket.service.average_minutes,
                'currently_called': (Ticket.query.filter_by(service_id=ticket.service_id,status='CALLED').first().display_number if Ticket.query.filter_by(service_id=ticket.service_id,status='CALLED').first() else '---'),
                'service_name':ticket.service.name,'branch_name':ticket.service.branch.name,'business_name':ticket.service.branch.business.name,'counter_label':ticket.service.counter_label}

    app.extensions['queue_state']=state

    @app.get('/app')
    @app.get('/app/')
    @app.get('/app/<path:path>')
    def react_frontend(path=''):
        from flask import send_from_directory
        root=Path(app.root_path)/'frontend'/'dist'
        if path.startswith('assets/'):
            return send_from_directory(root,path)
        if not (root/'index.html').exists():
            abort(503,'React build unavailable. Use the existing UI or build frontend first.')
        return send_from_directory(root,'index.html')

    @app.get('/app.webmanifest')
    def react_manifest():
        import json
        manifest=json.loads((Path(app.static_folder)/'manifest.json').read_text(encoding='utf-8'))
        manifest.update(id='/app',start_url='/app/',scope='/app/',name='QueueLess Pulse Workspace')
        return jsonify(manifest)

    @app.cli.command('initdb')
    def initdb():
        """Create a fresh schema. Existing schemas must be migrated first."""
        inspector = inspect(db.engine)
        if inspector.has_table('services') and 'branch_id' not in {c['name'] for c in inspector.get_columns('services')}:
            raise click.ClickException('Legacy schema detected. Back up and run upgrade-db --apply first.')
        db.create_all()
        db.session.commit()
        click.echo('Universal schema initialized. Register an owner to create your business.')

    @app.cli.command('create-staff')
    @click.option('--username', prompt=True)
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option('--business-id', type=int)
    def create_staff(username, password, business_id):
        if len(password) < 12:
            raise click.ClickException('Password must be at least 12 characters')
        if Staff.query.filter_by(username=username).first():
            raise click.ClickException('Username already exists')
        businesses=Business.query.all()
        if business_id is None and len(businesses)==1:
            business_id=businesses[0].id
        if business_id is None or not db.session.get(Business,business_id):
            raise click.ClickException('Select an existing business with --business-id')
        staff = Staff(username=username)
        staff.set_password(password)
        db.session.add(staff)
        db.session.flush()
        member=Membership(business_id=business_id,staff_id=staff.id,role='staff')
        db.session.add(member)
        db.session.flush()
        for service in Service.query.join(Branch).filter(Branch.business_id==business_id):
            db.session.add(ServiceAssignment(membership_id=member.id,service_id=service.id))
        db.session.commit()
        click.echo('Staff created.')

    def upgrade_schema():
        if db.engine.dialect.name != 'postgresql':
            raise click.ClickException('Schema upgrade requires PostgreSQL')
        inspector=inspect(db.engine)
        if not inspector.has_table('tickets'):
            raise click.ClickException('No schema found; run initdb for a fresh database')
        old_numbering='business_date' not in {c['name'] for c in inspector.get_columns('tickets')}
        old_tenants='branch_id' not in {c['name'] for c in inspector.get_columns('services')}
        old_limits=not inspector.has_table('rate_limit_buckets')
        if not old_numbering and not old_tenants and not old_limits:
            click.echo('Schema already current.')
            return
        try:
            with db.engine.begin() as connection:
                connection.execute(text("SELECT set_config('app.business_timezone', :tz, true)"), {'tz': app.config['BUSINESS_TIMEZONE']})
                for needed,filename in [(old_numbering,'001_queue_integrity.sql'),(old_tenants,'002_universal.sql'),(old_tenants,'003_assignment_guard.sql'),(old_limits,'004_rate_limits.sql')]:
                    if needed:
                        connection.execute(text((Path(app.root_path)/'migrations'/filename).read_text(encoding='utf-8')))
        except SQLAlchemyError as error:
            raise click.ClickException('Migration rejected and rolled back. Inspect conflicts and back up before retrying.') from error
        click.echo('Universal schema migrated; history retained. Claim the legacy business using create-owner.')

    @app.cli.command('migrate-legacy')
    @click.option('--apply', is_flag=True, required=True)
    def migrate_legacy(apply):
        if not apply:
            raise click.ClickException('Pass --apply after taking a database backup')
        upgrade_schema()

    @app.cli.command('upgrade-db')
    @click.option('--apply', is_flag=True, required=True)
    def upgrade_db(apply):
        if not apply:
            raise click.ClickException('Pass --apply after taking a database backup')
        upgrade_schema()

    @app.cli.command('create-owner')
    @click.option('--business-id',type=int,required=True)
    @click.option('--username',prompt=True)
    @click.option('--password',prompt=True,hide_input=True,confirmation_prompt=True)
    def create_owner(business_id,username,password):
        if len(password)<12 or not db.session.get(Business,business_id):
            raise click.ClickException('Existing business and password of at least 12 characters required')
        user=Staff.query.filter_by(username=username).first()
        if user and not user.check_password(password):
            raise click.ClickException('Existing account password does not match')
        if not user:
            user=Staff(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
        member=Membership.query.filter_by(business_id=business_id,staff_id=user.id).first()
        if not member:
            member=Membership(business_id=business_id,staff_id=user.id,role='owner')
            db.session.add(member)
        member.role='owner'
        member.is_active=True
        db.session.commit()
        click.echo('Owner provisioned for selected business.')

    @app.get('/health')
    def health():
        db.session.execute(text('SELECT 1'))
        db.session.execute(select(Service.seq_date, Service.branch_id, Service.average_minutes).limit(0))
        db.session.execute(select(Membership.business_id).limit(0))
        db.session.execute(select(Ticket.business_date, Ticket.request_key).limit(0))
        from models import RateLimitBucket
        db.session.execute(select(RateLimitBucket.hits).limit(0))
        return jsonify(status='ok')

    @app.get('/sw.js')
    def worker():
        response = app.send_static_file('sw.js')
        response.headers['Service-Worker-Allowed'] = '/'
        return response

    @app.get('/staff/manifest.webmanifest')
    def staff_manifest():
        import json
        manifest=json.loads((Path(app.static_folder)/'manifest.json').read_text(encoding='utf-8'))
        manifest.update(id='/staff-app',name='QueueLess Pulse Staff',short_name='Pulse Staff',start_url='/staff/dashboard')
        return jsonify(manifest)

    @app.get('/')
    def index():
        businesses=Business.query.filter_by(is_active=True).order_by(Business.id).all()
        services=public_services(businesses[0]) if len(businesses)==1 else []
        return render_template('customer/directory.html', businesses=businesses, services=services)

    @app.post('/service/<int:service_id>/join')
    def join_queue(service_id):
        key = request.form.get('request_key', '')
        try:
            key = str(uuid.UUID(key))
        except (ValueError, TypeError):
            abort(400, 'Invalid submission key')
        service = locked_service(service_id)
        db.session.refresh(service.branch)
        db.session.refresh(service.branch.business)
        if not service.is_active or not service.branch.is_active or not service.branch.business.is_active:
            abort(409, 'Service unavailable')
        existing = Ticket.query.filter_by(request_key=key).first()
        if existing:
            if existing.owner_id != session.get('owner_id') or existing.service_id != service_id:
                abort(409, 'Submission key already used')
            return redirect(url_for('view_ticket', token=existing.token), code=303)
        day = datetime.now(ZoneInfo(service.branch.business.timezone)).date()
        if service.seq_date != day:
            service.seq_date, service.last_number = day, 0
        service.last_number += 1
        ticket = Ticket(service_id=service.id, business_date=day, daily_number=service.last_number,
                        display_number=f'{service.prefix}{service.last_number:03d}', request_key=key, owner_id=session['owner_id'])
        db.session.add(ticket)
        db.session.flush()
        event(ticket, 'CREATED')
        db.session.commit()
        return redirect(url_for('view_ticket', token=ticket.token), code=303)

    @app.get('/ticket/<token>')
    def view_ticket(token):
        ticket = Ticket.query.filter_by(token=token).first_or_404()
        return render_template('customer/ticket.html', ticket=ticket, can_cancel=ticket.owner_id == session.get('owner_id'), **{k: v for k, v in state(ticket).items() if k in ('people_ahead', 'estimated_time')})

    @app.get('/ticket/<token>/status')
    def ticket_status(token):
        return jsonify(state(Ticket.query.filter_by(token=token).first_or_404()))

    @app.get('/my-tickets')
    def my_tickets():
        tickets = Ticket.query.filter_by(owner_id=session['owner_id']).order_by(Ticket.id.desc()).limit(30).all() if session.get('owner_id') else []
        return render_template('customer/my_tickets.html', tickets=tickets)

    @app.post('/ticket/<token>/cancel')
    def cancel_ticket(token):
        ticket = Ticket.query.filter_by(token=token).first_or_404()
        locked_service(ticket.service_id)
        db.session.refresh(ticket)
        if ticket.owner_id != session.get('owner_id'):
            abort(403)
        if ticket.status == 'CANCELLED':
            return redirect(url_for('view_ticket', token=token), code=303)
        if ticket.status != 'WAITING':
            abort(409, 'Only waiting tickets can be cancelled')
        ticket.status = 'CANCELLED'
        event(ticket, 'CANCELLED')
        db.session.commit()
        return redirect(url_for('view_ticket', token=token), code=303)

    @app.route('/staff/login', methods=['GET', 'POST'])
    def staff_login():
        if request.method == 'POST':
            staff = Staff.query.filter_by(username=request.form.get('username', '').strip().lower(), is_active=True).first()
            if staff and staff.check_password(request.form.get('password', '')):
                owner = session.get('owner_id')
                session.clear()
                session['staff_id'] = staff.id
                session['owner_id'] = owner or str(uuid.uuid4())
                return redirect(url_for('staff_dashboard'), code=303)
            return render_template('staff/login.html', error='Invalid credentials'), 401
        return render_template('staff/login.html')

    @app.post('/staff/logout')
    def staff_logout():
        session.clear()
        return redirect(url_for('staff_login'), code=303)

    @app.get('/staff/dashboard')
    @staff_required
    def staff_dashboard():
        queues = {s: {'waiting': Ticket.query.filter_by(service_id=s.id, status='WAITING').order_by(Ticket.id).all(),
                      'called': Ticket.query.filter_by(service_id=s.id, status='CALLED').first()}
                  for s in allowed_services()}
        return render_template('staff/dashboard.html', queues=queues)

    @app.post('/staff/call/<int:service_id>')
    @staff_required
    def staff_call(service_id):
        service = locked_service(service_id)
        require_service(service)
        if Ticket.query.filter_by(service_id=service_id, status='CALLED').first():
            abort(409, 'Complete or skip the active ticket first')
        ticket = Ticket.query.filter_by(service_id=service_id, status='WAITING').order_by(Ticket.id).first()
        if ticket:
            ticket.status = 'CALLED'
            ticket.called_at=datetime.now(timezone.utc)
            event(ticket, 'CALLED', session['staff_id'])
        db.session.commit()
        return redirect(url_for('staff_dashboard'), code=303)

    @app.get('/staff/fragment')
    @staff_required
    def staff_fragment():
        queues = {s: {'waiting': Ticket.query.filter_by(service_id=s.id, status='WAITING').order_by(Ticket.id).all(),
                      'called': Ticket.query.filter_by(service_id=s.id, status='CALLED').first()} for s in allowed_services()}
        return render_template('staff/queue_cards.html', queues=queues)

    def finish(ticket_id, target):
        ticket = db.get_or_404(Ticket, ticket_id)
        service=locked_service(ticket.service_id)
        require_service(service)
        db.session.refresh(ticket)
        if ticket.status == target:
            return redirect(url_for('staff_dashboard'), code=303)
        if ticket.status != 'CALLED':
            abort(409, 'Ticket is no longer called')
        ticket.status = target
        ticket.finished_at=datetime.now(timezone.utc)
        event(ticket, target, session['staff_id'])
        db.session.commit()
        return redirect(url_for('staff_dashboard'), code=303)

    @app.post('/staff/complete/<int:ticket_id>')
    @staff_required
    def staff_complete(ticket_id):
        return finish(ticket_id, 'COMPLETED')

    @app.post('/staff/skip/<int:ticket_id>')
    @staff_required
    def staff_skip(ticket_id):
        return finish(ticket_id, 'SKIPPED')

    @app.get('/staff/live')
    @staff_required
    def staff_live():
        rows=[]
        for service in allowed_services():
            waiting=Ticket.query.filter_by(service_id=service.id,status='WAITING').order_by(Ticket.id).all()
            called=Ticket.query.filter_by(service_id=service.id,status='CALLED').first()
            today,start,end=business_day(service.branch.business)
            terminal=Ticket.query.filter(Ticket.service_id==service.id,Ticket.finished_at>=start,Ticket.finished_at<end)
            rows.append({'id':service.id,'name':service.name,'branch':service.branch.name,'business':service.branch.business.name,'counter':service.counter_label,'active':service.is_active,'waiting':[{'id':t.id,'number':t.display_number,'business_date':str(t.business_date)} for t in waiting], 'called':{'id':called.id,'number':called.display_number,'business_date':str(called.business_date)} if called else None, 'completed_today':terminal.filter_by(status='COMPLETED').count(),'skipped_today':terminal.filter_by(status='SKIPPED').count(),'business_date':str(today)})
        return jsonify(rows)

    @app.get('/display')
    def public_display():
        businesses=Business.query.filter_by(is_active=True).order_by(Business.id).all()
        if len(businesses)!=1:
            return render_template('customer/directory.html',businesses=businesses,services=[],display_mode=True)
        return render_template('public/display.html',business=businesses[0],display_url=url_for('display_data'))

    @app.get('/api/display_data')
    def display_data():
        business=Business.query.filter_by(is_active=True).order_by(Business.id).first()
        return jsonify(display_rows(reception_services(business)) if business else [])

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', debug=os.getenv('FLASK_DEBUG') == '1')
