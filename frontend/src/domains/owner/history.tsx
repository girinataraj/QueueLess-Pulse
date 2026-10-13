import { Link, useSearchParams } from 'react-router-dom';
import type { History, OwnerBusiness } from '../../api/contracts';
import { Form } from '../../components/form';
import { useLive, QueryState, Connection } from '../../components/feedback';
import { DataTable, Pagination, StatusBadge } from '../../components/system';
import { ownerSectionPath } from '../../lib/navigation';
export function ReviewHistory({data}: {data:OwnerBusiness}){
  const [params,setParams]=useSearchParams();const todayOnly=params.get('review')!=='history';
  const filters=new URLSearchParams(params);filters.delete('section');filters.delete('review');
  if(todayOnly){filters.set('date',data.stats.business_date);filters.set('date_basis','finished');filters.set('status','COMPLETED');}
  const query=useLive<History>('/owner/businesses/'+data.business.id+'/history?'+filters,4000,params.get('section')==='reviews');
  return <section id="reviews" className="review-workspace"><div className="section-heading"><div><h2>{todayOnly?"Today's Reviews":'Ticket history'}</h2><p className="hint">{todayOnly?`Completed on ${data.stats.business_date} · ${data.business.timezone}`:'Search preserved consultations and their audit history.'}</p></div><Connection query={query}/></div>
    <div className="review-navigation"><Link className={todayOnly?'active':''} to={ownerSectionPath(data.business.id,'reviews',new URLSearchParams(),'today')}>Today</Link><Link className={!todayOnly?'active':''} to={ownerSectionPath(data.business.id,'reviews',new URLSearchParams(),'history')}>History & filters</Link><Link to={ownerSectionPath(data.business.id,'overview')}>Back to dashboard</Link></div>
    {!todayOnly&&<section className="card history-filter"><Form fields={[
      {name:'date',label:'Date',type:'date',hint:'Business-local date; empty includes all history.'},
      {name:'date_basis',label:'Date basis',type:'select',options:[{value:'issued',label:'Ticket issue date'},{value:'finished',label:'Review / skip date'}]},
      {name:'status',label:'Status',type:'select',options:[{value:'',label:'All terminal states'},{value:'COMPLETED',label:'Completed'},{value:'SKIPPED',label:'Skipped'}]},
      {name:'service_id',label:'Service',type:'select',options:[{value:'',label:'All services'},...data.services.map(s=>({value:String(s.id),label:s.name}))]}
    ]} key={filters.toString()} initial={{date:params.get('date')??'',date_basis:params.get('date_basis')??'issued',status:params.get('status')??'',service_id:params.get('service_id')??''}} submit="Filter history" onSubmit={async values=>setParams({...Object.fromEntries(Object.entries(values).map(([k,v])=>[k,String(v)])),section:'reviews',review:'history'})}/></section>}
    <QueryState query={query}><section className="card"><DataTable caption={todayOnly?"Today's completed consultations":'Completed and skipped tickets'} headings={['Token','Service / location','Issued','Status','Audit trail']}>
      {query.data?.items.map((t,i)=><tr key={i}><td><strong className="table-token">{t.number}</strong></td><td>{t.service}<small className="table-secondary">{t.branch}</small></td><td>{t.date}</td><td><StatusBadge status={t.status}/></td><td><details><summary>{t.events.length} events</summary>{t.events.map((e,j)=><p className="hint" key={j}>{e.action} · {new Date(e.at).toLocaleString()}</p>)}</details></td></tr>)}
    </DataTable>{!query.data?.items.length&&<p className="empty-state">No tickets match this filter.</p>}</section><div className="history-pagination"><p className="hint">{query.data?.total??0} consultations</p><Pagination page={query.data?.page??1} pages={query.data?.pages??0} onChange={page=>setParams(prev=>{prev.set('page',String(page));return prev;})}/></div></QueryState>
  </section>;
}
