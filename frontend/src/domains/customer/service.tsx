import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { DisplayList, Service, Ticket } from '../../api/contracts';
import { useAction, useLive, ErrorMessage, Connection } from '../../components/feedback';
import { Button } from '../../components/ui/button';
import { KPIStatCard, StatusBadge } from '../../components/system';
export function ServiceCard({service,branch,slug}: {service:Service;branch:string;slug:string}){
  const [key]=useState(()=>crypto.randomUUID());const navigate=useNavigate();
  const action=useAction<Ticket>('/services/'+service.id+'/tickets',t=>navigate('/ticket/'+t.token));
  const query=useLive<DisplayList>('/display/'+encodeURIComponent(slug),3000);const queue=query.data?.find(q=>q.service_id===service.id);
  const closed=!service.is_active||queue?.availability==='CLOSED';
  return <article className="card patient-service-card"><div className="section-heading"><span className="eyebrow">{branch}</span><StatusBadge status={closed?'CLOSED':queue?.availability==='ON_BREAK'?'ON_BREAK':'OPEN'}/></div><h2>{service.name}</h2><p>{service.description||'Get an anonymous digital token. No patient account required.'}</p><div className="kpi-grid"><KPIStatCard label="Waiting now" value={queue?.waiting_count??'—'}/><KPIStatCard label="Approximate wait" value={queue?(queue.waiting_count+(queue.currently_called==='---'?0:1))*service.average_minutes+' min':'—'}/></div><p className="hint">Approx. {service.average_minutes} min per visitor {service.counter_label&&'· '+service.counter_label}</p>{queue?.availability==='ON_BREAK'&&<p className="notice">Doctor on break. You can join; the wait may be longer than this estimate.</p>}<Connection query={query}/><ErrorMessage error={action.error}/><Button className="join-queue" disabled={action.isPending||closed} onClick={()=>action.mutate({request_key:key})}>{action.isPending?'Joining…':'Join Queue'}</Button><p className="hint">Your token updates automatically while the app is open. This demonstration uses fictional records only.</p></article>;
}
