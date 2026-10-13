import { Routes, Route, Link, Navigate, useParams, useSearchParams } from 'react-router-dom';
import { Layout } from './components/layout';
import { lazy, Suspense } from 'react';
import { Loading } from './components/feedback';
import { ownerSectionPath } from './lib/navigation';
const Directory=lazy(()=>import('./domains/customer/pages').then(m=>({default:m.Directory})));
const BusinessPage=lazy(()=>import('./domains/customer/pages').then(m=>({default:m.BusinessPage})));
const TicketPage=lazy(()=>import('./domains/customer/pages').then(m=>({default:m.TicketPage})));
const AuthPage=lazy(()=>import('./domains/auth/pages').then(m=>({default:m.AuthPage})));
const InvitePage=lazy(()=>import('./domains/auth/pages').then(m=>({default:m.InvitePage})));
const StaffPage=lazy(()=>import('./domains/staff/page').then(m=>({default:m.StaffPage})));
const ReceptionPage=lazy(()=>import('./domains/staff/page').then(m=>({default:m.ReceptionPage})));
const OwnerHome=lazy(()=>import('./domains/owner/pages').then(m=>({default:m.OwnerHome})));
const OwnerDashboard=lazy(()=>import('./domains/owner/pages').then(m=>({default:m.OwnerDashboard})));
const DisplayPage=lazy(()=>import('./domains/display/page').then(m=>({default:m.DisplayPage})));
function BranchRedirect(){const {slug='',branchId=''}=useParams();const [params]=useSearchParams();const next=new URLSearchParams(params);next.set('branch_id',branchId);return <Navigate replace to={'/b/'+encodeURIComponent(slug)+'?'+next}/>;}
function ReviewsRedirect({today=false}: {today?:boolean}){const {businessId=''}=useParams();const [params]=useSearchParams();return <Navigate replace to={ownerSectionPath(businessId,'reviews',params,today?'today':'history')}/>;}
export function App() {
  return <Suspense fallback={<Loading/>}><Routes><Route element={<Layout/>}>
    <Route index element={<Directory/>}/><Route path="b/:slug" element={<BusinessPage/>}/>
    <Route path="b/:slug/branch/:branchId" element={<BranchRedirect/>}/><Route path="b/:slug/service/:serviceId" element={<BusinessPage/>}/>
    <Route path="ticket/:token" element={<TicketPage/>}/><Route path="my-tickets" element={<Navigate replace to="/?tickets=1"/>}/>
    <Route path="staff/login" element={<AuthPage staff/>}/><Route path="owner/login" element={<AuthPage/>}/><Route path="owner/register" element={<AuthPage register/>}/><Route path="invite/:token" element={<InvitePage/>}/>
    <Route path="staff/dashboard" element={<StaffPage/>}/><Route path="staff/reception" element={<ReceptionPage/>}/>
    <Route path="owner" element={<OwnerHome/>}/><Route path="owner/business/:businessId" element={<OwnerDashboard/>}/>
    <Route path="owner/business/:businessId/reviews" element={<ReviewsRedirect today/>}/><Route path="owner/business/:businessId/history" element={<ReviewsRedirect/>}/>
    <Route path="display" element={<Navigate replace to="/?view=display"/>}/><Route path="b/:slug/display" element={<DisplayPage/>}/>
    <Route path="*" element={<div className="empty-state"><h1>Page unavailable</h1><p>Check your QR or return to the patient queue.</p><Link to="/">Open patient entry</Link></div>}/>
  </Route></Routes></Suspense>;
}
