import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Clock3, Users, Eye, Stethoscope, ShieldCheck } from 'lucide-react';
import type { DisplayList, Service, Ticket, TicketList } from '../../api/contracts';
import { useAction, useLive, ErrorMessage, Connection } from '../../components/feedback';
import { Button } from '../../components/ui/button';
import { EyeArtwork } from '../../components/eye-artwork';
import { StatusBadge } from '../../components/system';
export function ServiceCard({service,branch,slug,business,multiple=false}: {service:Service;branch:string;slug:string;business:string;multiple?:boolean}){
  const storageKey='queueless-pending-join:'+service.id;
  const [key,setKey]=useState(()=>{try{return sessionStorage.getItem(storageKey)??crypto.randomUUID();}catch{return crypto.randomUUID();}});const navigate=useNavigate();
  const [unresolved,setUnresolved]=useState(()=>{try{return sessionStorage.getItem(storageKey)!==null;}catch{return false;}});
  const owned=useLive<TicketList>('/my-tickets',3000);
  const matching=owned.data?.filter(t=>t.entry_path===`/app/b/${slug}/service/${service.id}`)??[];
  const active=matching.find(t=>t.status==='WAITING'||t.status==='CALLED');
  // A terminal ownership snapshot cannot resolve an outstanding POST. Retain its
  // key across retries/reloads until the server confirms that exact issuance.
  const action=useAction<Ticket>('/services/'+service.id+'/tickets',t=>{try{sessionStorage.removeItem(storageKey);}catch{/* In-page retries still retain their key. */}setUnresolved(false);setKey(crypto.randomUUID());navigate('/ticket/'+t.token);});
  const query=useLive<DisplayList>('/display/'+encodeURIComponent(slug),3000);const queue=query.data?.find(q=>q.service_id===service.id);
  const closed=!service.is_active||queue?.availability==='CLOSED';
  return <article className="patient-service-card"><div className="join-panel">
    <div className="service-topline"><span className="service-icon">{/eye/i.test(service.name)?<Eye size={25} aria-hidden/>:<Stethoscope size={25} aria-hidden/>}</span><StatusBadge status={closed?'CLOSED':queue?.availability==='ON_BREAK'?'ON_BREAK':queue?'OPEN':'CONNECTING'}/></div>
    <p className="clinic-name">{business}{multiple&&' · '+branch}</p><h2>{service.name}</h2><p>{service.description||'A digital place in the queue. No patient details or account required.'}</p>
    <div className="arrival-facts"><div><Users aria-hidden size={19}/><span>Waiting now<strong>{queue?.waiting_count??'—'}</strong></span></div><div><Clock3 aria-hidden size={19}/><span>Estimated wait<strong>{queue?(queue.waiting_count+(queue.currently_called==='---'?0:1))*service.average_minutes+' min':'—'}</strong></span></div></div>
    <ErrorMessage error={owned.error}/><ErrorMessage error={query.error}/>{query.isError&&<Button variant="secondary" onClick={()=>void query.refetch()}>Retry live queue</Button>}<ErrorMessage error={action.error}/>
    <Button className="join-queue" disabled={action.isPending||(!active&&(closed||!queue||!owned.isSuccess))} onClick={()=>{if(active){navigate('/ticket/'+active.token);return;}try{sessionStorage.setItem(storageKey,key);}catch{/* Existing in-page idempotency remains available. */}setUnresolved(true);action.mutate({request_key:key});}}>{action.isPending?'Joining…':active?'View my token':unresolved?'Recover interrupted join':'Join Queue'}<ArrowRight aria-hidden size={20}/></Button>
    <p className="join-note"><ShieldCheck size={15} aria-hidden/>{active?'Your active token is saved in this browser.':unresolved?'Confirm the earlier join before starting a new visit. Its original token will be recovered if issued.':'No account needed. Just your place in line.'}</p>
  </div><aside className="arrival-context"><div className="art-top"><span>{service.name}</span><span>{service.counter_label||branch}</span></div>{/eye/i.test(service.name)?<EyeArtwork/>:<div className="service-art-generic"><Stethoscope size={92} aria-hidden/><span>Your next consultation</span></div>}<div className="art-serving"><span className="serving-dot"/><span>Now serving</span><strong>{queue?.currently_called==='---'?'—':queue?.currently_called??'—'}</strong><small>{service.counter_label||branch}</small></div></aside>
    <div className="patient-live-note"><Connection query={query}/>{closed?<span>Closed to new arrivals. Existing tickets remain available.</span>:queue?.availability==='ON_BREAK'?<span>Doctor on break. Joining remains open; the wait may be longer.</span>:queue?.availability==='NOT_RECORDED'?<span>Doctor availability has not been recorded.</span>:<span>Live queue · Approximate wait, using {service.average_minutes} min per visitor.</span>}</div>
  </article>;
}
