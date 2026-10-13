import { Link, Outlet, useLocation, useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Activity, LogOut, Ticket } from 'lucide-react';
import { api, session } from '../api/client';
import { Button } from './ui/button';
import { useState } from 'react';
import { ErrorMessage, QueryState } from './feedback';
import { TicketRecovery } from '../domains/customer/recovery';
import { experience } from '../lib/navigation';
export { PageHeader as Heading } from './system';
export function Brand({to='/'}: {to?:string}) {
  return <Link to={to} className="brand" aria-label="QueueLess Pulse home"><span className="brand-mark"><Activity aria-hidden size={21}/></span><span>QueueLess<b> Pulse</b><small>CLINICAL OPERATIONS</small></span></Link>;
}
export function Layout() {
  const auth=useQuery({queryKey:['session'],queryFn:session,staleTime:0});
  const cache=useQueryClient();const [signingOut,setSigningOut]=useState(false);const [logoutError,setLogoutError]=useState<Error|null>(null);
  const location=useLocation();const [params,setParams]=useSearchParams();const role=experience(location.pathname,location.search);
  const internal=['owner','doctor','reception'].includes(role);
  const home=role==='owner'?'/owner':role==='doctor'?'/staff/dashboard':role==='reception'?'/staff/reception':'/';
  async function logout(){setSigningOut(true);setLogoutError(null);try{await api('/auth/logout',{});cache.clear();await session();window.location.assign('/app/'+(role==='owner'?'owner/login':'staff/login'+(role==='reception'?'?experience=reception':'')));}catch(e){setLogoutError(e instanceof Error?e:new Error('Unable to sign out. Please retry.'));}finally{setSigningOut(false);}}
  function tickets(open:boolean){setParams(prev=>{if(open)prev.set('tickets','1');else prev.delete('tickets');return prev;},{replace:!open});}
  return <div className={'experience-shell experience-'+role}>
    <a className="skip-link" href="#main">Skip to content</a>
    {role!=='display'&&<header className="workspace-header"><div className="brand-area"><Brand to={home}/>{internal&&<span className="workspace-label">{role==='doctor'?'Doctor console':role==='reception'?'Reception desk':'Hospital operations'}</span>}</div>
      {role==='patient'?<Button variant="secondary" className="ticket-access" onClick={()=>tickets(true)}><Ticket aria-hidden size={17}/>Your tickets</Button>:internal?<div className="account">{role==='owner'&&<Link to="/owner?manage=businesses">Businesses</Link>}<span className="account-name">{auth.data?.user?.username}</span>{auth.data?.user&&<Button variant="secondary" disabled={signingOut} onClick={()=>void logout()}><LogOut size={17} aria-hidden/>Sign out</Button>}</div>:<Link to="/" className="text-link">Patient queue</Link>}
    </header>}
    <main id="main" className="content">{auth.data?.demo_mode&&<p className="demo-indicator" role="status">Synthetic demonstration · Fictional records only</p>}<ErrorMessage error={logoutError}/><QueryState query={auth}><Outlet/></QueryState></main>
    {role==='patient'&&<TicketRecovery open={params.get('tickets')==='1'} onOpenChange={tickets}/>}
  </div>;
}
