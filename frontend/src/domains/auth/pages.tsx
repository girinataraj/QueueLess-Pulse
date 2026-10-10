import { Link, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, session, type Values } from '../../api/client';
import type { Session, Invitation } from '../../api/contracts';
import { Form, type Field } from '../../components/form';
import { useLive, QueryState } from '../../components/feedback';
import { Heading } from '../../components/layout';
export const accountFields: Field[] = [{ name: 'username', label: 'Username', required: true, min: 3, max: 64, pattern: '^[a-zA-Z0-9_.-]+$' }, { name: 'email', label: 'Email (optional)', type: 'email', max: 254 }, { name: 'password', label: 'Password', type: 'password', required: true, min: 12, max: 128 }, { name: 'confirm_password', label: 'Confirm password', type: 'password', required: true }];
function useAuthenticate(path: string, target: string) {
  const cache=useQueryClient(); const navigate=useNavigate();
  return useMutation({ mutationFn: async (values: Values) => { await api<Session>(path, values); return session(); }, onSuccess: data => { cache.clear(); cache.setQueryData(['session'],data); navigate(target); } });
}
export function AuthPage({ register = false, staff = false }: { register?: boolean; staff?: boolean }) {
  const mutation=useAuthenticate(register ? '/auth/register' : '/auth/login', staff ? '/staff/dashboard' : '/owner');
  const fields=register ? accountFields : [accountFields[0]!, { name: 'password', label: 'Password', type: 'password' as const, required: true, max: 128 }];
  return <div className="auth-container"><Heading eyebrow={staff ? 'STAFF CONSOLE' : 'BUILT FOR YOUR BUSINESS'} title={register ? 'Create your owner account' : staff ? 'Staff sign in' : 'Owner sign in'} description="One platform for clinics, salons, banks and service teams."/><div className="card"><Form fields={fields} submit={register ? 'Create account' : 'Sign in'} onSubmit={mutation.mutateAsync} busy={mutation.isPending} error={mutation.error}/><p>{register ? 'Already registered?' : 'New to Pulse?'} <Link to={register ? '/owner/login' : '/owner/register'}>{register ? 'Sign in' : 'Create an account'}</Link></p></div></div>;
}
export function InvitePage() {
  const { token = '' }=useParams();const info=useLive<Invitation>('/invitations/'+encodeURIComponent(token));
  const auth=useQuery({queryKey:['session'],queryFn:session});const mutation=useAuthenticate('/invitations/'+encodeURIComponent(token),'/staff/dashboard');
  return <QueryState query={info}>{info.data && <div className="auth-container"><Heading eyebrow="PRIVATE TEAM INVITATION" title={'Join '+info.data.business_name} description="Your owner will assign service permissions after you accept."/><div className="card">{auth.data?.user ? <p>Accept as <strong>{auth.data.user.username}</strong>.</p> : <p>Already registered? <Link to="/staff/login">Sign in</Link>, then reopen this invitation.</p>}<Form fields={auth.data?.user ? [] : accountFields} submit="Accept invitation" busy={mutation.isPending} error={mutation.error} onSubmit={mutation.mutateAsync}/></div></div>}</QueryState>;
}
