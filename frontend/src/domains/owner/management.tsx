import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { Action, Branch, Service, Member, OwnerBusiness, InviteCreated } from '../../api/contracts';
import { useAction, ErrorMessage } from '../../components/feedback';
import { Form, type Field } from '../../components/form';
import { Dialog } from '../../components/ui/dialog';
import { Button } from '../../components/ui/button';
import { accountFields } from '../auth/pages';
import { branchFields, activeField, serviceFields } from './fields';
export function BranchCard({ branch, slug }: { branch: Branch; slug: string }) {
  const action=useAction<Action>('/owner/businesses/'+branch.business_id+'/branches/'+branch.id);
  return <article className="card"><span className="badge">{branch.is_active ? 'Active' : 'Inactive'}</span><h3>{branch.name}</h3><p>{branch.address || 'No address added'}</p><div className="actions"><Link to={'/b/'+slug+'/branch/'+branch.id}>Entry page</Link><Link to={'/b/'+slug+'/display?branch_id='+branch.id}>Display</Link><a href={'/owner/business/'+branch.business_id+'/qr.png?ui=react&branch_id='+branch.id+'&download=1'}>Download QR</a></div><Dialog title="Edit branch" trigger="Edit branch"><Form fields={[...branchFields,activeField]} initial={{name:branch.name,address:branch.address,is_active:branch.is_active}} submit="Save branch" onSubmit={action.mutateAsync} busy={action.isPending} error={action.error}/></Dialog></article>;
}
export function ServiceEditor({ service, businessId }: { service: Service; businessId: number }) {
  const action=useAction<Action>('/owner/businesses/'+businessId+'/services/'+service.id);
  return <article className="card"><span className="badge">{service.is_active ? 'Active' : 'Inactive'}</span><h3>{service.name}</h3><p>{service.prefix} · {service.average_minutes} min {service.counter_label && '· '+service.counter_label}</p><div className="actions"><a href={'/owner/business/'+businessId+'/qr.png?ui=react&service_id='+service.id+'&download=1'}>Download service QR</a><Dialog title="Edit service" trigger="Edit service"><Form fields={serviceFields} initial={{name:service.name,prefix:service.prefix,average_minutes:String(service.average_minutes),counter_label:service.counter_label,description:service.description,is_active:service.is_active}} submit="Save service" onSubmit={action.mutateAsync} busy={action.isPending} error={action.error}/></Dialog></div></article>;
}
export function CreateBranch({ businessId }: { businessId: number }) {
  const action=useAction<Action>('/owner/businesses/'+businessId+'/branches');
  return <section className="card"><h3>Add a branch</h3><Form fields={branchFields} submit="Add branch" onSubmit={action.mutateAsync} busy={action.isPending} error={action.error}/></section>;
}
export function CreateService({ data }: { data: OwnerBusiness }) {
  const action=useAction<Action>('/owner/businesses/'+data.business.id+'/services');
  const branch: Field={name:'branch_id',label:'Branch',type:'select',required:true,options:data.branches.map(b => ({value:String(b.id),label:b.name}))};
  return <section className="card"><h3>Create a service</h3>{data.branches.length ? <Form fields={[branch,...serviceFields]} initial={{branch_id:String(data.branches[0]!.id),average_minutes:'5',is_active:true}} submit="Create service" onSubmit={action.mutateAsync} busy={action.isPending} error={action.error}/> : <p>Add a branch first.</p>}</section>;
}
export function MemberCard({ member, data }: { member: Member; data: OwnerBusiness }) {
  const action=useAction<Action>('/owner/businesses/'+data.business.id+'/staff/'+member.id+'/permissions');
  const fields: Field[]=[{name:'is_active',label:'Membership active',type:'checkbox'},{name:'service_ids',label:'Assigned services',type:'multiselect',options:data.services.map(s => ({value:String(s.id),label:(data.branches.find(b=>b.id===s.branch_id)?.name ?? '')+' · '+s.name}))}];
  return <article className="card"><h3>{member.username}</h3><p>{member.role} · {member.is_active ? 'Active' : 'Revoked'}</p>{member.role==='staff' ? <Form fields={fields} initial={{is_active:member.is_active,service_ids:member.service_ids.map(String)}} submit="Save permissions" onSubmit={action.mutateAsync} busy={action.isPending} error={action.error}/> : <p className="hint">Owners can manage every service in this business.</p>}</article>;
}
export function TeamTools({ businessId, slug }: { businessId: number; slug: string }) {
  const create=useAction<Action>('/owner/businesses/'+businessId+'/staff');const [url,setUrl]=useState('');
  const invite=useAction<InviteCreated>('/owner/businesses/'+businessId+'/invitations', data=>setUrl(data.invite_url));
  return <div className="analytics-grid"><section className="card"><h3>Create staff securely</h3><p className="hint">Choose an initial password and share it privately. New staff start unassigned.</p><Form fields={accountFields.filter(f=>f.name!=='confirm_password')} submit="Create staff" onSubmit={create.mutateAsync} busy={create.isPending} error={create.error}/></section><section className="card"><h3>Invite a teammate</h3><p>One-use link, valid for 24 hours. Share it privately. Service permissions remain unassigned.</p><ErrorMessage error={invite.error}/><Button disabled={invite.isPending} onClick={()=>invite.mutate({})}>Create invitation</Button>{url && <><label htmlFor="invite-url">Private invitation link</label><input id="invite-url" value={url} readOnly/></>}<hr/><h3>Business entry QR</h3><img className="qr" src={'/owner/business/'+businessId+'/qr.png?ui=react'} alt={'Queue entry QR for '+slug}/><a className="text-link" href={'/owner/business/'+businessId+'/qr.png?ui=react&download=1'}>Download business QR</a></section></div>;
}
