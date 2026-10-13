export { TicketPage } from './ticket';
import { ServiceCard } from './service';
import { Link, Navigate, useParams, useSearchParams } from 'react-router-dom';
import type { BusinessList, PublicBusiness } from '../../api/contracts';
import { useLive, QueryState } from '../../components/feedback';
import { MapPin } from 'lucide-react';
import { Heading } from '../../components/layout';
export function Directory() {
  const [params]=useSearchParams();const displays=params.get('view')==='display';const query=useLive<BusinessList>('/businesses');
  const single=query.data?.length===1?query.data[0]:undefined;
  if(single)return <Navigate replace to={'/b/'+single.slug+(displays?'/display':'')+(!displays&&params.size?'?'+params:'')}/>;
  return <div className="patient-entry"><Heading eyebrow="QUEUELESS PULSE" title={displays?'Choose a waiting-room display':'Where are you visiting?'} description={displays?'Open the live public queue for your location.':'Choose your clinic to see available services.'}/><QueryState query={query}><div className="entry-options">{query.data?.map(b=><Link key={b.id} to={'/b/'+b.slug+(displays?'/display':'')} className="entry-option"><span><small>{b.category}</small><strong>{b.name}</strong>{b.description&&<p>{b.description}</p>}</span><span aria-hidden>→</span></Link>)}</div>{!query.data?.length&&<div className="empty-state"><h2>No queue is available</h2><p>Check the service QR address or ask Reception for the correct link.</p></div>}</QueryState></div>;
}
export function BusinessPage() {
  const {slug='',serviceId}=useParams();const [params]=useSearchParams();const branchId=params.get('branch_id');
  const query=useLive<PublicBusiness>('/businesses/'+encodeURIComponent(slug));const data=query.data;
  const branch=data?.branches.find(b=>String(b.id)===branchId);const service=data?.services.find(s=>String(s.id)===serviceId);
  const invalid=Boolean(data&&(branchId&&!branch||serviceId&&(!service||branchId&&String(service.branch_id)!==branchId)));
  const services=data?.services.filter(s=>serviceId?String(s.id)===serviceId:branchId?String(s.branch_id)===branchId:true)??[];
  if(data&&!invalid&&!serviceId&&services.length===1){const next=new URLSearchParams(params);next.delete('branch_id');return <Navigate replace to={'/b/'+slug+'/service/'+services[0]!.id+(next.size?'?'+next:'')}/>;}
  return <QueryState query={query}>{data&&<div className="patient-entry">{service&&!invalid?<header className="patient-hero"><p className="clinic-context"><MapPin size={16} aria-hidden/>{data.business.name} · {data.branches.find(b=>b.id===service.branch_id)?.name}</p><span className="eyebrow">A LITTLE LESS WAIT. A LITTLE MORE CLARITY.</span><h1>{/eye/i.test(service.name)?<>Your eyes deserve<br/><span>your time. Not a queue.</span></>:<>Your time matters.<br/><span>Keep your place, clearly.</span></>}</h1><p>Join the queue for {service.name.toLowerCase()}.<br/>Follow your token and know when it is your turn.</p></header>:<Heading eyebrow={data.business.name+(branch?' · '+branch.name:'')} title="Choose your service" description="Join the right queue directly. No patient account is needed."/>}
    {invalid?<div className="empty-state" role="alert"><h2>This service link is unavailable</h2><p>The specified service or branch is not available. No other queue has been selected.</p><Link to={'/b/'+slug}>Choose an available service</Link></div>:<div className={'patient-services'+(services.length>1?' multiple-services':'')}>{services.map(s=><ServiceCard key={s.id} slug={slug} service={s} branch={data.branches.find(b=>b.id===s.branch_id)?.name??''} multiple={services.length>1} business={data.business.name}/>)}</div>}
    {!invalid&&!services.length&&<div className="empty-state"><h2>No services configured here</h2><p>Ask Reception which queue to use. Existing tickets remain available through Your tickets.</p></div>}
  </div>}</QueryState>;
}
