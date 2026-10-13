import { ReviewHistory } from './history';
import { OperationsOverview } from './operations';
import { Tabs } from '../../components/system';
import { Link, Navigate, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import type { Action, BusinessList, OwnerBusiness } from '../../api/contracts';
import { Form } from '../../components/form';
import { useLive, useAction, QueryState } from '../../components/feedback';
import { Heading } from '../../components/layout';
import { ownerSectionPath } from '../../lib/navigation';
import { businessFields, slugField } from './fields';
import { Analytics } from './analytics';
import { BranchCard, ServiceEditor, CreateBranch, CreateService, MemberCard, TeamTools } from './management';
export function OwnerHome() {
  const query=useLive<BusinessList>('/owner/businesses');const navigate=useNavigate();const [params]=useSearchParams();
  const create=useAction<Action>('/owner/businesses',data=>navigate(data.resource_path));
  if(query.data?.length===1&&params.get('manage')!=='businesses')return <Navigate replace to={'/owner/business/'+query.data[0]!.id}/>;
  return <><Heading eyebrow="OWNER WORKSPACE" title="Your businesses" description="Organize every branch, service and team in one place."/><QueryState query={query}><div className="entry-options">{query.data?.map(b=><Link to={'/owner/business/'+b.id} className="entry-option" key={b.id}><span><small>{b.category}</small><strong>{b.name}</strong></span><span>Manage →</span></Link>)}</div>{!query.data?.length && <p className="empty-state">Create your first business below.</p>}<details className="card inline-create" open={!query.data?.length}><summary>Create a business</summary><Form fields={[businessFields[0]!,slugField,...businessFields.slice(1)]} initial={{category:'Clinic',timezone:'Asia/Kolkata'}} submit="Create business" onSubmit={create.mutateAsync} busy={create.isPending} error={create.error}/></details></QueryState></>;
}
function Profile({ data }: { data: OwnerBusiness }) {
  const update=useAction<Action>('/owner/businesses/'+data.business.id);
  return <section className="card" id="profile"><h2>Business profile</h2><Form fields={businessFields} initial={{name:data.business.name,category:data.business.category,timezone:data.business.timezone,description:data.business.description}} submit="Save profile" onSubmit={update.mutateAsync} busy={update.isPending} error={update.error}/></section>;
}
export function OwnerDashboard() {
  const {businessId=''}=useParams();const query=useLive<OwnerBusiness>('/owner/businesses/'+businessId,4000);const data=query.data;
  const [params,setParams]=useSearchParams();const requested=params.get('section')??'overview';
  const section=['branches','services','team','management'].includes(requested)?'management':['profile','settings'].includes(requested)?'settings':requested==='reviews'?'reviews':'overview';
  function setSection(value:string){setParams(prev=>{prev.set('section',value);if(value==='reviews'&&!prev.has('review'))prev.set('review','today');return prev;});}
  return <QueryState query={query}>{data && <>
    <Heading eyebrow={'OWNER WORKSPACE · '+data.stats.business_date} title={data.business.name} description={"Today's operations, at a glance. · "+data.business.timezone}>
      <div className="actions"><Link className="button button-secondary" to={'/b/'+data.business.slug}>Customer portal</Link><Link className="button button-primary" to={'/b/'+data.business.slug+'/display'}>Reception display</Link><Link className="button button-secondary" to={ownerSectionPath(businessId,'reviews',new URLSearchParams(),'history')}>Ticket history</Link></div>
    </Heading>
    <Tabs label="Business sections" value={section} onValueChange={setSection} items={[
      {id:'overview',label:'Overview',content:<section id="overview"><OperationsOverview businessId={data.business.id} waiting={data.stats.waiting} called={data.stats.called} completed={data.stats.completed_today} skipped={data.stats.skipped_today} date={data.stats.business_date}/><details className="card historical-details"><summary>Historical analytics — all recorded data</summary><Analytics stats={data.stats}/></details></section>},
      {id:'management',label:'Team & Services',content:<section className="owner-management"><div className="section-heading"><div><h2>One team. A shared flow.</h2><p className="hint">Service configuration, assignments and scoped Reception permissions.</p></div></div>
        <details className="management-section" id="services" open={!['team','branches'].includes(requested)}><summary>Services <span>{data.services.length} configured</span></summary><div className="card-grid">{data.services.map(s=><ServiceEditor key={s.id} service={s} businessId={data.business.id}/>)}</div><CreateService data={data}/></details>
        <details className="management-section" id="team" open={requested==='team'}><summary>Team & permissions <span>{data.members.length} memberships</span></summary><div className="card-grid">{data.members.map(m=><MemberCard key={m.id} member={m} data={data}/>)}</div><TeamTools businessId={data.business.id} slug={data.business.slug}/></details>
        <details className="management-section" id="branches" open={requested==='branches'}><summary>Branches <span>{data.branches.length} locations</span></summary><div className="card-grid">{data.branches.map(b=><BranchCard key={b.id} branch={b} slug={data.business.slug}/>)}</div><CreateBranch businessId={data.business.id}/></details>
      </section>},
      {id:'reviews',label:'Reviews',content:<ReviewHistory data={data}/>},
      {id:'settings',label:'Settings',content:<Profile data={data}/>}
    ]}/>
  </>}</QueryState>;
}
