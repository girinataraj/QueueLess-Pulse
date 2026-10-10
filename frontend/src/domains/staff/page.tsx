import type { Action, Queue, QueueList } from '../../api/contracts';
import { QueryState, useLive, useAction, ErrorMessage, Connection } from '../../components/feedback';
import { Heading } from '../../components/layout';
import { Button } from '../../components/ui/button';
function QueueCard({ queue }: { queue: Queue }) {
  const call=useAction<Action>('/staff/services/'+queue.id+'/call');
  const finish=useAction<Action>('/staff/tickets/'+queue.called?.id+'/complete');
  const skip=useAction<Action>('/staff/tickets/'+queue.called?.id+'/skip');
  const busy=call.isPending || finish.isPending || skip.isPending;
  return <article className="card queue-card"><span className="eyebrow">{queue.business} · {queue.branch}</span><div className="section-heading"><h2>{queue.name}</h2><span className="badge">{queue.waiting.length} waiting</span></div><p className="hint">{queue.counter}{!queue.active && ' · Closed to new joins'}</p><div className="current-ticket"><span>Currently serving</span><div className="token-display">{queue.called?.number ?? '—'}</div>{queue.called && <div className="actions"><Button disabled={busy} onClick={() => finish.mutate({})}>Complete</Button><Button variant="destructive" disabled={busy} onClick={() => skip.mutate({})}>Skip</Button></div>}</div><ErrorMessage error={call.error ?? finish.error ?? skip.error}/><Button disabled={busy || !!queue.called || !queue.waiting.length} onClick={() => call.mutate({})}>Call Next</Button><h3>Waiting tickets</h3><ol className="waiting-list">{queue.waiting.map((t,i) => <li key={t.id}><span>{i+1}</span><strong>{t.number}</strong></li>)}</ol>{!queue.waiting.length && <p className="hint">No visitors waiting.</p>}</article>;
}
export function StaffPage() {
  const query=useLive<QueueList>('/staff/queues',3000);
  return <><Heading eyebrow="LIVE OPERATIONS" title="Staff console" description="Assigned queues. One active ticket per service."><Connection query={query}/></Heading><QueryState query={query}><div className="card-grid">{query.data?.map(q => <QueueCard key={q.id} queue={q}/>)}</div>{!query.data?.length && <div className="empty-state"><h2>No assigned queues</h2><p>Ask your business owner to assign a service. Revoked permissions take effect immediately.</p></div>}</QueryState></>;
}
