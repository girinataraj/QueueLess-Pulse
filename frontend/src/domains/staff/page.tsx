export { ReceptionPage } from './reception';
import { DoctorQueueCard } from './doctor';


import type { QueueList } from '../../api/contracts';

import { QueryState, useLive, Connection } from '../../components/feedback';
import { Heading } from '../../components/layout';

export function StaffPage() {
  const query=useLive<QueueList>('/staff/queues',3000);
  return <><Heading eyebrow="LIVE OPERATIONS" title="Consultation console" description="Resolve the current call, then continue in arrival order."><Connection query={query}/></Heading><QueryState query={query}><div className="doctor-workspaces">{query.data?.map(q => <DoctorQueueCard key={q.id} queue={q}/>)}</div>{!query.data?.length && <div className="empty-state"><h2>No assigned queues</h2><p>Ask your business owner to assign a service. Revoked permissions take effect immediately.</p></div>}</QueryState></>;
}
