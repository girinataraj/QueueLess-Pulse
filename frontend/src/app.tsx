import { Routes, Route, Link } from 'react-router-dom';
import { Layout } from './components/layout';
import { lazy, Suspense } from 'react';
import { Loading } from './components/feedback';
const Directory=lazy(()=>import('./domains/customer/pages').then(m=>({default:m.Directory})));
const BusinessPage=lazy(()=>import('./domains/customer/pages').then(m=>({default:m.BusinessPage})));
const TicketPage=lazy(()=>import('./domains/customer/pages').then(m=>({default:m.TicketPage})));
const MyTickets=lazy(()=>import('./domains/customer/pages').then(m=>({default:m.MyTickets})));
const AuthPage=lazy(()=>import('./domains/auth/pages').then(m=>({default:m.AuthPage})));
const InvitePage=lazy(()=>import('./domains/auth/pages').then(m=>({default:m.InvitePage})));
const StaffPage=lazy(()=>import('./domains/staff/page').then(m=>({default:m.StaffPage})));
const ReceptionPage=lazy(()=>import('./domains/staff/page').then(m=>({default:m.ReceptionPage})));
const OwnerHome=lazy(()=>import('./domains/owner/pages').then(m=>({default:m.OwnerHome})));
const OwnerDashboard=lazy(()=>import('./domains/owner/pages').then(m=>({default:m.OwnerDashboard})));
const HistoryPage=lazy(()=>import('./domains/owner/pages').then(m=>({default:m.HistoryPage})));
const DisplayPage=lazy(()=>import('./domains/display/page').then(m=>({default:m.DisplayPage})));
export function App() {
  return <Suspense fallback={<Loading/>}><Routes><Route element={<Layout/>}><Route index element={<Directory/>}/><Route path="b/:slug" element={<BusinessPage/>}/><Route path="b/:slug/branch/:branchId" element={<BusinessPage/>}/><Route path="b/:slug/service/:serviceId" element={<BusinessPage/>}/><Route path="ticket/:token" element={<TicketPage/>}/><Route path="my-tickets" element={<MyTickets/>}/><Route path="staff/login" element={<AuthPage staff/>}/><Route path="owner/login" element={<AuthPage/>}/><Route path="owner/register" element={<AuthPage register/>}/><Route path="invite/:token" element={<InvitePage/>}/><Route path="staff/dashboard" element={<StaffPage/>}/><Route path="staff/reception" element={<ReceptionPage/>}/><Route path="owner" element={<OwnerHome/>}/><Route path="owner/business/:businessId" element={<OwnerDashboard/>}/><Route path="owner/business/:businessId/history" element={<HistoryPage/>}/><Route path="display" element={<Directory displays/>}/><Route path="b/:slug/display" element={<DisplayPage/>}/><Route path="*" element={<div className="empty-state"><h1>Page unavailable</h1><Link to="/">Find a business</Link></div>}/></Route></Routes></Suspense>;
}
