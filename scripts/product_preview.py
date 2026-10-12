"""Explicit, loopback-only preview; never consumes DATABASE_URL from the shell."""
import argparse, json, sys
from pathlib import Path
from sqlalchemy import create_engine, make_url, text
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--profile',type=Path,required=True);parser.add_argument('--port',type=int,default=5002);args=parser.parse_args()
    if not 1024<=args.port<=65535:parser.error('Use an unprivileged local port.')
    profile=json.loads(args.profile.read_text());url=make_url(profile['url'])
    if (url.get_backend_name(),url.host,url.port,url.database,url.username)!=('postgresql','127.0.0.1',55436,'queueless_product_demo','queueless_product'):
        raise RuntimeError('Preview requires the dedicated loopback product database; inherited or hosted connections are refused.')
    engine=create_engine(url)
    with engine.connect() as connection:
        if connection.execute(text('SELECT current_database()')).scalar()!=url.database or connection.execute(text('SELECT inet_server_port()')).scalar()!=55436 or not connection.connection.driver_connection.info.ssl_in_use:
            raise RuntimeError('Local product database identity or TLS verification failed.')
    engine.dispose()
    from app import create_app
    app=create_app({'PRODUCTION':False,'DEBUG':False,'APP_STAGE':'','DEMO_MODE':False,'STAGING_AUTH_MODE':'basic','OWNER_REGISTRATION_ENABLED':False,'SECRET_KEY':profile['session_secret'],'SESSION_COOKIE_NAME':'queueless_product_preview','SESSION_COOKIE_SECURE':False,'SQLALCHEMY_DATABASE_URI':profile['url'],'PUBLIC_BASE_URL':f'http://127.0.0.1:{args.port}','TRUSTED_HOSTS':['127.0.0.1','localhost']})
    app.run(host='127.0.0.1',port=args.port,debug=False,use_reloader=False)

if __name__=='__main__':main()
