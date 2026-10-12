import { NavLink, Link, Outlet, useLocation } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Activity, Building2, ClipboardList, Monitor, LogOut, Users, Menu, ShieldCheck, Stethoscope } from 'lucide-react';
import { api, session } from '../api/client';
import { Button } from './ui/button';
import { useState } from 'react';
import { ErrorMessage, QueryState } from './feedback';
import { Breadcrumbs, Drawer, IconButton } from './system';
export { PageHeader as Heading } from './system';
const allLinks=[{to:'/',name:'Patient portal',icon:Building2},{to:'/my-tickets',name:'My tickets',icon:ClipboardList},{to:'/staff/dashboard',name:'Staff console',icon:Stethoscope},{to:'/staff/reception',name:'Reception',icon:Users},{to:'/owner',name:'Owner workspace',icon:ShieldCheck},{to:'/display',name:'Public display',icon:Monitor}];
export function RoleSidebar({ owner, signedIn, role, onNavigate }: { owner: boolean; signedIn: boolean; role: string; onNavigate?: () => void }) {
  const links=allLinks.filter(link=>owner || !signedIn || !link.to.startsWith('/owner') && (role!=='Reception' || link.to!=='/staff/dashboard'));
  return <><span className="nav-label">{signedIn?'YOUR WORKSPACE':'QUEUELESS PULSE'}</span><nav aria-label="Main navigation">{links.map(({to,name,icon:Icon})=><NavLink key={to} to={to} onClick={onNavigate} end={to==='/' || to==='/owner'}><Icon aria-hidden size={20}/>{name}</NavLink>)}</nav><div className="sidebar-note"><span className="dot"/>Synthetic demonstration<p>Anonymous tokens. No clinical records.</p><a href="/">Open existing interface</a></div></>;
}
export function TopBar({ user, signingOut, onLogout, onMenu }: { user?: string; signingOut: boolean; onLogout: () => void; onMenu: () => void }) {
  return <header className="app-header"><div className="brand-area"><IconButton label="Open navigation" className="mobile-menu" onClick={onMenu}><Menu size={22}/></IconButton><Link to="/" className="brand"><span className="brand-mark"><Activity aria-hidden size={23}/></span><span>QueueLess <b>Pulse</b><small>HOSPITAL QUEUE OPERATIONS</small></span></Link></div><div className="account"><span>{user ?? 'Patient & visitor access'}</span>{user?<Button variant="secondary" disabled={signingOut} onClick={onLogout}><LogOut aria-hidden size={16}/><span>Sign out</span></Button>:<Link className="button button-secondary" to="/staff/login">Team sign in</Link>}</div></header>;
}
export function Layout() {
  const auth=useQuery({queryKey:['session'],queryFn:session,staleTime:0});
  const queryClient=useQueryClient();const [signingOut,setSigningOut]=useState(false);const [logoutError,setLogoutError]=useState<Error|null>(null);const [menu,setMenu]=useState(false);const location=useLocation();
  const role=location.pathname.startsWith('/owner')?'Owner':location.pathname.includes('/staff/reception')?'Reception':location.pathname.includes('/staff')?'Doctor':location.pathname.endsWith('/display')||location.pathname==='/display'?'Public display':'Patient';
  async function logout(){setSigningOut(true);setLogoutError(null);try{await api('/auth/logout',{});queryClient.clear();await session();window.location.assign('/app/');}catch(error){setLogoutError(error instanceof Error?error:new Error('Unable to sign out. Please retry.'));}finally{setSigningOut(false);}}
  const navigation={owner:auth.data?.memberships.some(m=>m.role==='owner')??false,signedIn:!!auth.data?.user,role};
  return <div className={'app-shell role-'+role.toLowerCase().replace(' ','-')}><a className="skip-link" href="#main">Skip to content</a><TopBar user={auth.data?.user?.username} signingOut={signingOut} onLogout={()=>void logout()} onMenu={()=>setMenu(true)}/><aside className="sidebar"><RoleSidebar {...navigation}/></aside><Drawer open={menu} onOpenChange={setMenu} title="Workspaces"><RoleSidebar {...navigation} onNavigate={()=>setMenu(false)}/></Drawer><main id="main" className="content" key={location.pathname}><Breadcrumbs items={[{label:'Pulse',to:'/'},{label:role}]}/>{auth.data?.demo_mode&&<p className="notice" role="status">Synthetic demonstration · Fictional data only · Not approved for real customer use.</p>}<ErrorMessage error={logoutError}/><QueryState query={auth}><Outlet/></QueryState></main><footer className="app-footer"><span>QueueLess Pulse</span><span>Secure queue operations · Synthetic demonstration</span></footer></div>;
}
