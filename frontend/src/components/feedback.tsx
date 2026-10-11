import { Component, createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { useQuery, useMutation, useQueryClient, type UseQueryResult } from '@tanstack/react-query';
import { api, RequestError, type Values } from '../api/client';
import { Button } from './ui/button';
const ToastContext = createContext<(message: string) => void>(() => {});
export function ToastProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState('');
  useEffect(() => { if (!message) return; const id = setTimeout(() => setMessage(''), 6000); return () => clearTimeout(id); }, [message]);
  return <ToastContext.Provider value={setMessage}>{children}<div className="toast" role="status" aria-live="polite">{message}</div></ToastContext.Provider>;
}
export function useAction<T>(path: string, done?: (data: T) => void) {
  const queryClient = useQueryClient(); const toast = useContext(ToastContext);
  return useMutation({ mutationFn: (values: Values) => api<T>(path, values), onSuccess: async data => { await queryClient.invalidateQueries(); toast('Changes saved.'); done?.(data); } });
}
export function useLive<T>(path: string, interval?: number) { return useQuery({ queryKey: [path], queryFn: () => api<T>(path), refetchInterval: interval, retry: 1 }); }
export function ErrorMessage({ error }: { error: Error | null }) {
  if (!error) return null;
  const status = error instanceof RequestError ? error.status : 0;
  const signInPath = window.location.pathname.startsWith('/app/owner') ? '/app/owner/login' : window.location.pathname === '/app/staff/reception' ? '/app/staff/login?experience=reception' : '/app/staff/login';
  return <div className="notice error" role="alert"><strong>{status === 401 ? 'Sign in to continue' : status === 404 || status === 410 ? 'Link unavailable' : 'Unable to complete the request'}</strong><p>{error.message}</p>{status === 401 && <a href={signInPath}>Sign in</a>}</div>;
}
export function Loading() { return <div role="status" aria-label="Loading" className="skeleton"><div/><div/><div/></div>; }
export function QueryState({ query, children }: { query: UseQueryResult<unknown, Error>; children: ReactNode }) {
  if (query.isPending) return <Loading/>;
  const denied=query.error instanceof RequestError && [401,403,404,410].includes(query.error.status);
  if (query.isError && (!query.data || denied)) return <><ErrorMessage error={query.error}/><Button variant="secondary" onClick={() => void query.refetch()}>Retry</Button></>;
  return <>{children}</>;
}
export function Connection({ query }: { query: UseQueryResult<unknown, Error> }) { return <span className={'connection ' + (query.isError ? 'offline' : '')} role="status">{query.isError ? 'Connection lost · Showing last update · Retrying' : query.isPending ? 'Connecting…' : 'Connected · Live updates'}</span>; }
export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <main className="content"><div role="alert" className="notice error"><h1>Something went wrong</h1><p>Reload the page to reconnect. Your saved queue data is unchanged.</p><Button onClick={() => window.location.reload()}>Reload page</Button></div></main> : this.props.children; }
}
