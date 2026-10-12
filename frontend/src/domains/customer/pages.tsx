export { TicketPage } from './ticket';
import { ServiceCard } from './service';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { session } from '../../api/client';

import type { BusinessList, PublicBusiness, TicketList } from '../../api/contracts';
import { useLive, QueryState } from '../../components/feedback';

import { Heading } from '../../components/layout';
export function Directory({ displays = false }: { displays?: boolean }) {
  const auth=useQuery({queryKey:['session'],queryFn:session});
  const query = useLive<BusinessList>('/businesses');
  return <><Heading eyebrow="LESS WAITING. BETTER SERVICE." title={displays ? 'Reception displays' : 'Your place in line. Your time back.'} description={displays ? 'Choose a business to open its live, public display.' : 'Find your business, choose a service and follow your queue from anywhere.'}/><QueryState query={query}><div className="card-grid">{query.data?.map(b => <Link key={b.id} to={'/b/'+b.slug+(displays ? '/display' : '')} className="card link-card"><span className="eyebrow">{b.category}</span><h2>{b.name}</h2><p>{b.description || 'Choose your branch and join the queue.'}</p><span className="text-link">{displays ? 'Open display' : 'View branches'} →</span></Link>)}</div>{!query.data?.length && <div className="empty-state"><h2>No businesses available yet</h2><p>New branches will appear here when they are ready.</p>{auth.data?.owner_registration_enabled && <Link to="/owner/register">Bring your business to Pulse</Link>}</div>}</QueryState></>;
}
export function BusinessPage() {
  const { slug = '', branchId, serviceId } = useParams(); const query = useLive<PublicBusiness>('/businesses/'+encodeURIComponent(slug)); const data = query.data;
  const branch = data?.branches.find(b => String(b.id) === branchId); const service = data?.services.find(s => String(s.id) === serviceId);
  const invalid = Boolean(data && ((branchId && !branch) || (serviceId && !service)));
  return <QueryState query={query}>{data && <><Heading eyebrow={data.business.category} title={service?.name ?? branch?.name ?? data.business.name} description={data.business.description || 'Choose a branch. No customer account required.'}><Link className="button button-secondary" to={'/b/'+slug+'/display'}>Reception display</Link></Heading><p className="hint">Business time: {data.business.timezone}</p>{invalid ? <div role="alert" className="empty-state">This entry link is unavailable. Choose an active branch.</div> : branchId || serviceId ? <><Link to={'/b/'+slug}>All branches</Link><div className="card-grid">{data.services.filter(s => serviceId ? String(s.id)===serviceId : String(s.branch_id)===branchId).map(s => <ServiceCard slug={slug} key={s.id} service={s} branch={data.branches.find(b => b.id===s.branch_id)?.name ?? ''}/>)}</div>{!data.services.some(s => serviceId ? String(s.id)===serviceId : String(s.branch_id)===branchId) && <p className="empty-state">No services are accepting new tickets.</p>}</> : <div className="card-grid">{data.branches.map(b => <Link key={b.id} className="card link-card" to={'/b/'+slug+'/branch/'+b.id}><span className="eyebrow">BRANCH</span><h2>{b.name}</h2><p>{b.address || 'Visit us for your service.'}</p><span className="text-link">Choose a service →</span></Link>)}{!data.branches.length && <p className="empty-state">Branches are being set up. Check back soon.</p>}</div>}</>}</QueryState>;
}
export function MyTickets() {
  const query=useLive<TicketList>('/my-tickets');
  return <><Heading eyebrow="PRIVATE BROWSER HISTORY" title="My tickets" description="Tickets issued in this browser. Use a saved recovery link if you changed devices."/><QueryState query={query}><div className="card-grid">{query.data?.map(t => <Link className="card link-card" key={t.token} to={'/ticket/'+t.token}><span className="eyebrow">{t.business_name} · {t.branch_name}</span><h2>{t.display_number}</h2><p>{t.service_name} · {t.status} · {t.business_date}</p></Link>)}</div>{!query.data?.length && <p className="empty-state">No tickets in this browser yet.</p>}</QueryState></>;
}
