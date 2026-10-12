import { Link, useParams, useSearchParams } from 'react-router-dom';
import type { History, OwnerBusiness } from '../../api/contracts';
import { Form } from '../../components/form';
import { useLive, QueryState } from '../../components/feedback';
import { Heading } from '../../components/layout';
import { DataTable, Pagination, StatusBadge } from '../../components/system';

export function TodayReviewsPage(){return <HistoryPage todayOnly/>;}
export function HistoryPage({todayOnly=false}: {todayOnly?:boolean}){
  const {businessId=''}=useParams();const [params,setParams]=useSearchParams();
  const owner=useLive<OwnerBusiness>('/owner/businesses/'+businessId,4000);
  const filters=new URLSearchParams(params);
  if(todayOnly&&owner.data){
    filters.set('date',owner.data.stats.business_date);
    filters.set('date_basis','finished');filters.set('status','COMPLETED');
  }
  const query=useLive<History>('/owner/businesses/'+businessId+'/history?'+filters.toString(),4000,!todayOnly||!!owner.data);
  const page=query.data?.page??1;
  if(todayOnly&&!owner.data)return <QueryState query={owner}>{null}</QueryState>;
  return <>
    <Heading eyebrow="BUSINESS AUDIT" title={todayOnly?"Today's Reviews":"Ticket history"}
      description={todayOnly?`Completed today · ${owner.data?.stats.business_date} · ${owner.data?.business.timezone}`:'Completed and skipped tickets, preserved for your business.'}>
      <Link to={'/owner/business/'+businessId}>Back to dashboard</Link>
      {todayOnly&&<Link to={'/owner/business/'+businessId+'/history'}>Filter historical tickets</Link>}
    </Heading>
    {!todayOnly&&<section className="card"><Form fields={[
      {name:'date',label:'Date',type:'date',hint:'Business-local date; leave empty for all history.'},
      {name:'date_basis',label:'Date basis',type:'select',options:[{value:'issued',label:'Ticket issue date'},{value:'finished',label:'Review / skip date'}]},
      {name:'status',label:'Status',type:'select',options:[{value:'',label:'All terminal states'},{value:'COMPLETED',label:'Completed'},{value:'SKIPPED',label:'Skipped'}]},
      {name:'service_id',label:'Service',type:'select',options:[{value:'',label:'All services'},...(owner.data?.services.map(s=>({value:String(s.id),label:s.name}))??[])]}
    ]} key={params.toString()} initial={{date:params.get('date')??'',date_basis:params.get('date_basis')??'issued',status:params.get('status')??'',service_id:params.get('service_id')??''}}
      submit="Filter history" onSubmit={async values=>setParams(Object.fromEntries(Object.entries(values).map(([k,v])=>[k,String(v)])))}/></section>}
    <QueryState query={query}>
      <section className="card"><DataTable caption={todayOnly?"Today's completed consultations":'Completed and skipped tickets'} headings={['Issue date','Branch / Service','Token','Status','Audit trail']}>
        {query.data?.items.map((t,i)=><tr key={i}><td>{t.date}</td><td>{t.branch} / {t.service}</td><td>{t.number}</td><td><StatusBadge status={t.status}/></td><td>{t.events.map((e,j)=><p className="hint" key={j}>{e.action} · {new Date(e.at).toLocaleString()}</p>)}</td></tr>)}
      </DataTable>{!query.data?.items.length&&<p className="empty-state">No tickets match this filter.</p>}</section>
      <p className="hint">{query.data?.total} tickets</p>
      <Pagination page={page} pages={query.data?.pages??0} onChange={next=>setParams(prev=>{prev.set('page',String(next));return prev;})}/>
    </QueryState>
  </>;
}
