import type { Action, Queue, QueueList } from '../../api/contracts';
import { QueryState, useLive, useAction, ErrorMessage, Connection } from '../../components/feedback';
import { Heading } from '../../components/layout';
import { Button } from '../../components/ui/button';
function QueueCard({ queue }: { queue: Queue }) {
  const call=useAction<Action>('/staff/services/'+queue.id+'/call');
  const finish=useAction<Action>('/staff/tickets/'+queue.called?.id+'/complete');
  const skip=useAction<Action>('/staff/tickets/'+queue.called?.id+'/skip');
  const busy=call.isPending || finish.isPending || skip.isPending;
  return <article className="card queue-card"><span className="eyebrow">{queue.business} · {queue.branch}</span><div className="section-heading"><h2>{queue.name}</h2><span className="badge">{queue.waiting.length} waiting</span></div><p className="hint">{queue.counter}{!queue.active && ' · Closed to new joins'}</p><div className="metric-grid" style={{marginTop: '1rem', marginBottom: '1.5rem'}}><div><strong>{queue.waiting.length}</strong><span>Remaining queue</span></div><div><strong>{queue.completed_today}</strong><span>Completed today</span></div></div><div className="current-ticket"><span>Currently serving</span><div className="token-display">{queue.called?.number ?? '—'}</div>{queue.called && <div className="actions"><Button disabled={busy} onClick={() => finish.mutate({})}>Mark Reviewed</Button><Button variant="destructive" disabled={busy} onClick={() => skip.mutate({})}>Skip</Button></div>}</div><ErrorMessage error={call.error ?? finish.error ?? skip.error}/><Button disabled={busy || !!queue.called || !queue.waiting.length} onClick={() => call.mutate({})}>Call Next</Button><h3>Waiting tickets</h3><ol className="waiting-list">{queue.waiting.map((t,i) => <li key={t.id}><span>{i+1}</span><strong>{t.number}</strong></li>)}</ol>{!queue.waiting.length && <p className="hint">No visitors waiting.</p>}</article>;
}
export function StaffPage() {
  const query=useLive<QueueList>('/staff/queues',3000);
  return <><Heading eyebrow="LIVE OPERATIONS" title="Staff console" description="Assigned queues. One active ticket per service."><Connection query={query}/></Heading><QueryState query={query}><div className="card-grid">{query.data?.map(q => <QueueCard key={q.id} queue={q}/>)}</div>{!query.data?.length && <div className="empty-state"><h2>No assigned queues</h2><p>Ask your business owner to assign a service. Revoked permissions take effect immediately.</p></div>}</QueryState></>;
}

export function ReceptionPage() {
  const query=useLive<QueueList>('/staff/queues',3000);
  return (
    <>
      <Heading eyebrow="RECEPTION" title="Front Desk" description="Queue display and registration access."><Connection query={query}/></Heading>
      <QueryState query={query}>
        <div className="card-grid">
          {query.data?.map(q => (
             <article key={q.id} className="card">
                <span className="eyebrow">{q.business} · {q.branch}</span>
                <div className="section-heading" style={{marginBottom:'0'}}><h2>{q.name}</h2></div>
                <div style={{display:'flex', gap:'2rem', marginTop:'1.5rem', flexWrap:'wrap', alignItems:'flex-start'}}>
                   <div style={{textAlign:'center'}}>
                     {/* QR endpoint will be implemented by backend team as documented */}
                     <img src={`/api/v1/staff/services/${q.id}/qr.png`} alt="QR Code" className="qr" style={{margin:'0 auto 1rem'}} />
                     <a href={`/api/v1/staff/services/${q.id}/qr.png?download=1`} className="button button-secondary" download>Print QR</a>
                   </div>
                   <div className="metric-grid" style={{flex: 1, margin: 0, gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))'}}>
                     <div><strong>{q.waiting.length}</strong><span>Patients waiting</span></div>
                     <div><strong>{q.called?.number ?? '—'}</strong><span>Currently serving</span></div>
                     <div><strong>{q.completed_today}</strong><span>Completed today</span></div>
                   </div>
                </div>
             </article>
          ))}
        </div>
        {!query.data?.length && <div className="empty-state"><h2>No assigned queues</h2></div>}
      </QueryState>
    </>
  );
}
