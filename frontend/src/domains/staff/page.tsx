import { DoctorQueueCard } from './doctor';
import { useQuery } from '@tanstack/react-query';
import { session } from '../../api/client';
import type { QueueList, ReceptionList } from '../../api/contracts';
import { Link } from 'react-router-dom';
import { QueryState, useLive, Connection } from '../../components/feedback';
import { Heading } from '../../components/layout';
import { Button } from '../../components/ui/button';
export function StaffPage() {
  const query=useLive<QueueList>('/staff/queues',3000);
  return <><Heading eyebrow="LIVE OPERATIONS" title="Staff console" description="Assigned queues. One active ticket per service."><Connection query={query}/></Heading><QueryState query={query}><div className="card-grid">{query.data?.map(q => <DoctorQueueCard key={q.id} queue={q}/>)}</div>{!query.data?.length && <div className="empty-state"><h2>No assigned queues</h2><p>Ask your business owner to assign a service. Revoked permissions take effect immediately.</p></div>}</QueryState></>;
}

export function ReceptionPage() {
  const auth=useQuery({queryKey:['session'],queryFn:session});
  const query=useLive<ReceptionList>('/reception/queues',3000);
  return (
    <>
      <Heading eyebrow="RECEPTION" title="Reception desk" description="Service QR and live queue counts. Sign in with your Reception account."><Connection query={query}/><Link to="/staff/login?experience=reception">Reception sign in</Link></Heading>
      <QueryState query={query}>
        <div className="card-grid">
          {query.data?.map(q => (
             <article key={q.service_id} className="card reception-card">
                <span className="eyebrow">{q.business_name} · {q.branch_name}</span>
                <div className="section-heading"><h2>{q.service_name}</h2><span className="badge">{q.business_date}</span></div>
                <div className="reception-layout">
                   <div className="reception-qr">
                     <img src={`/api/v1/staff/services/${q.service_id}/qr.png`} alt={`${q.service_name} service QR`} className="qr" width="280" height="280" />
                     <p>Scan to receive your digital token.</p>
                     <a className="text-link patient-link" href={q.patient_url}>Open patient queue</a>
                     <div className="actions no-print"><a href={`/api/v1/staff/services/${q.service_id}/qr.png?download=1`} className="button button-secondary" download>Download QR</a><Button variant="secondary" onClick={() => window.print()}>Print QR</Button></div>
                     {auth.data?.demo_mode && <p className="hint">Fictional demonstration only.{auth.data.gateway_required && ' The browser gateway is required.'}</p>}
                   </div>
                   <div className="reception-status">
                     <div className="current-ticket"><span>Currently serving · {q.counter_label}</span><div className="token-display">{q.currently_called}</div></div>
                     <div className="metric-grid"><div><strong data-testid="waiting-count">{q.waiting_count}</strong><span>Patients waiting</span></div>
                     <div><strong>{q.completed_today}</strong><span>Completed today</span></div>
                     <div><strong>{q.skipped_today}</strong><span>Skipped today</span></div></div>
                     <Link className="text-link no-print" to={'/b/'+q.business_slug+'/display'}>Open Public Display →</Link>
                   </div>
                </div>
             </article>
          ))}
        </div>
        {!query.data?.length && <div className="empty-state"><h2>No reception services</h2><p>Your Owner must activate your business membership and its service.</p></div>}
      </QueryState>
    </>
  );
}
