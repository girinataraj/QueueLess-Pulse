import { useQuery } from '@tanstack/react-query';
import { session } from '../../api/client';
import type { Action, Queue, QueueList, ReceptionList } from '../../api/contracts';
import { Link } from 'react-router-dom';
import { QueryState, useLive, useAction, ErrorMessage, Connection } from '../../components/feedback';
import { Heading } from '../../components/layout';
import { Button } from '../../components/ui/button';
function QueueCard({ queue }: { queue: Queue }) {
  const call=useAction<Action>('/staff/services/'+queue.id+'/call');
  const finish=useAction<Action>('/staff/tickets/'+queue.called?.id+'/complete');
  const skip=useAction<Action>('/staff/tickets/'+queue.called?.id+'/skip');
  const busy=call.isPending || finish.isPending || skip.isPending;
  return <article className="card queue-card"><span className="eyebrow">{queue.business} · {queue.branch}</span><div className="section-heading"><h2>{queue.name}</h2><span className="badge">{queue.waiting.length} waiting</span></div><p className="hint">{queue.counter}{!queue.active && ' · Closed to new joins'} · {queue.business_date}</p><div className="metric-grid queue-metrics"><div><strong>{queue.completed_today}</strong><span>Reviewed today</span></div><div><strong>{queue.skipped_today}</strong><span>Skipped today</span></div></div><div className="current-ticket"><span>Currently serving</span><div className="token-display">{queue.called?.number ?? '—'}</div>{queue.called && <><p className="hint">Issued {queue.called.business_date}{queue.called.business_date !== queue.business_date && ' · Carried over: finish this ticket before Call Next.'}</p><div className="actions"><Button disabled={busy} onClick={() => finish.mutate({})}>Mark Reviewed</Button><Button variant="destructive" disabled={busy} onClick={() => skip.mutate({})}>Skip</Button></div></>}</div><ErrorMessage error={call.error ?? finish.error ?? skip.error}/><Button disabled={busy || !!queue.called || !queue.waiting.length} onClick={() => call.mutate({})}>Call Next</Button><h3>Waiting tickets</h3><ol className="waiting-list">{queue.waiting.map((t,i) => <li key={t.id}><span>{i+1}</span><strong>{t.number}</strong><small>{t.business_date}</small></li>)}</ol>{!queue.waiting.length && <p className="hint">No visitors waiting.</p>}</article>;
}
export function StaffPage() {
  const query=useLive<QueueList>('/staff/queues',3000);
  return <><Heading eyebrow="LIVE OPERATIONS" title="Staff console" description="Assigned queues. One active ticket per service."><Connection query={query}/></Heading><QueryState query={query}><div className="card-grid">{query.data?.map(q => <QueueCard key={q.id} queue={q}/>)}</div>{!query.data?.length && <div className="empty-state"><h2>No assigned queues</h2><p>Ask your business owner to assign a service. Revoked permissions take effect immediately.</p></div>}</QueryState></>;
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
