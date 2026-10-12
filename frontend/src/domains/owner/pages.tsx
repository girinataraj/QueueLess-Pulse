export { HistoryPage, TodayReviewsPage } from './history';
import { OperationsOverview } from './operations';
import { useState } from 'react';
import { Tabs } from '../../components/system';
import { Link, useNavigate, useParams } from 'react-router-dom';
import type { Action, BusinessList, OwnerBusiness, History } from '../../api/contracts';
import { Form } from '../../components/form';
import { useLive, useAction, QueryState, Connection } from '../../components/feedback';
import { Heading } from '../../components/layout';
import { businessFields, slugField } from './fields';
import { Analytics } from './analytics';
import { BranchCard, ServiceEditor, CreateBranch, CreateService, MemberCard, TeamTools } from './management';
export function OwnerHome() {
  const query=useLive<BusinessList>('/owner/businesses');const navigate=useNavigate();
  const create=useAction<Action>('/owner/businesses',data=>navigate(data.resource_path));
  return <><Heading eyebrow="OWNER WORKSPACE" title="Your businesses" description="Organize every branch, service and team in one place."/><QueryState query={query}><div className="card-grid">{query.data?.map(b=><Link to={'/owner/business/'+b.id} className="card link-card" key={b.id}><span className="eyebrow">{b.category}</span><h2>{b.name}</h2><p>/b/{b.slug}</p><span className="text-link">Manage business →</span></Link>)}</div>{!query.data?.length && <p className="empty-state">Create your first business below.</p>}<section className="card"><h2>Create a business</h2><Form fields={[businessFields[0]!,slugField,...businessFields.slice(1)]} initial={{category:'Clinic',timezone:'Asia/Kolkata'}} submit="Create business" onSubmit={create.mutateAsync} busy={create.isPending} error={create.error}/></section></QueryState></>;
}
function Profile({ data }: { data: OwnerBusiness }) {
  const update=useAction<Action>('/owner/businesses/'+data.business.id);
  return <section className="card" id="profile"><h2>Business profile</h2><Form fields={businessFields} initial={{name:data.business.name,category:data.business.category,timezone:data.business.timezone,description:data.business.description}} submit="Save profile" onSubmit={update.mutateAsync} busy={update.isPending} error={update.error}/></section>;
}
function TodayHistory({ businessId, date }: { businessId: number; date: string }) {
  const query=useLive<History>(`/owner/businesses/${businessId}/history?date=${date}&date_basis=finished&status=COMPLETED`,4000);
  return <section className="card table-wrap today-reviews" id="reviews" tabIndex={0} aria-label="Today's completed consultations" role="region"><div className="section-heading"><h2>Today's Reviews</h2><Connection query={query}/></div><p className="hint">Completed consultations on {date}, using the business timezone. Carried-over tickets are included when reviewed today.</p><QueryState query={query}><table><caption>Today's completed consultations</caption><thead><tr><th scope="col">Token</th><th scope="col">Service</th><th scope="col">Issued on</th><th scope="col">Status</th></tr></thead><tbody>{query.data?.items.map((t,i)=><tr key={i}><td>{t.number}</td><td>{t.service}</td><td>{t.date}</td><td>{t.status}</td></tr>)}</tbody></table>{!query.data?.items.length && <p className="empty-state">No consultations reviewed today.</p>}<p>{query.data?.total ?? 0} completed consultations today</p><Link to={`/owner/business/${businessId}/history?date=${date}&date_basis=finished&status=COMPLETED`} className="text-link">View today's complete audit →</Link></QueryState></section>;
}

export function OwnerDashboard() {
  const {businessId=''}=useParams();const query=useLive<OwnerBusiness>('/owner/businesses/'+businessId,4000);const data=query.data;
  const [section,setSection]=useState('overview');
  return <QueryState query={query}>{data && <>
    <Heading eyebrow={'YOUR BUSINESSES / '+data.business.category} title={data.business.name} description={'Business time: '+data.business.timezone+' · One active ticket per service'}>
      <div className="actions"><Link className="button button-secondary" to={'/b/'+data.business.slug}>Customer portal</Link><Link className="button button-primary" to={'/b/'+data.business.slug+'/display'}>Reception display</Link><Link className="button button-secondary" to={'/owner/business/'+businessId+'/history'}>Ticket history</Link></div>
    </Heading>
    <Tabs label="Business sections" value={section} onValueChange={setSection} items={[
      {id:'overview',label:'Overview',content:<section id="overview">
        <div className="section-heading"><h2>Queue overview</h2><Connection query={query}/></div>
        <OperationsOverview businessId={data.business.id} waiting={data.stats.waiting} called={data.stats.called} completed={data.stats.completed_today} skipped={data.stats.skipped_today} date={data.stats.business_date}/>
        <details className="card historical-details"><summary>Historical analytics — all recorded data</summary><Analytics stats={data.stats}/></details>
      </section>},
      {id:'reviews',label:"Today's Reviews",content:<TodayHistory businessId={data.business.id} date={data.stats.business_date}/>},
      {id:'branches',label:'Branches',content:<section id="branches"><div className="section-heading"><h2>Branches</h2><span>{data.branches.length} locations</span></div><div className="card-grid">{data.branches.map(b=><BranchCard key={b.id} branch={b} slug={data.business.slug}/>)}</div><CreateBranch businessId={data.business.id}/></section>},
      {id:'services',label:'Services',content:<section id="services"><h2>Services</h2><div className="card-grid">{data.services.map(s=><ServiceEditor key={s.id} service={s} businessId={data.business.id}/>)}</div><CreateService data={data}/></section>},
      {id:'team',label:'Team',content:<section id="team"><h2>Team & permissions</h2><div className="card-grid">{data.members.map(m=><MemberCard key={m.id} member={m} data={data}/>)}</div><TeamTools businessId={data.business.id} slug={data.business.slug}/></section>},
      {id:'profile',label:'Profile',content:<Profile data={data}/>}
    ]}/>
  </>}</QueryState>;
}
