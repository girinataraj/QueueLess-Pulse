import { it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { ErrorBoundary, ErrorMessage, QueryState } from './feedback';
import { RequestError } from '../api/client';
it('contains render failures with a useful recovery action', () => {
  vi.spyOn(console,'error').mockImplementation(()=>{});
  function Broken(): never { throw new Error('render failure'); }
  render(<ErrorBoundary><Broken/></ErrorBoundary>);
  expect(screen.getByRole('alert')).toHaveTextContent('Something went wrong');
  expect(screen.getByRole('button',{name:'Reload page'})).toBeVisible();
});
it.each([401,403,404,410])('hides previously cached private data after access is denied (%s)', async status => {
  const fetchPrivate=vi.fn().mockResolvedValueOnce({name:'Private tenant data'}).mockRejectedValue(new RequestError(status,'Access no longer available'));
  function PrivatePage() {
    const query=useQuery({queryKey:['private'],queryFn:fetchPrivate,retry:false});
    return <><button onClick={()=>void query.refetch()}>Refresh</button><QueryState query={query}><p>{query.data?.name}</p></QueryState></>;
  }
  const client=new QueryClient();
  render(<QueryClientProvider client={client}><PrivatePage/></QueryClientProvider>);
  expect(await screen.findByText('Private tenant data')).toBeVisible();
  await userEvent.click(screen.getByRole('button',{name:'Refresh'}));
  await waitFor(()=>expect(screen.queryByText('Private tenant data')).not.toBeInTheDocument());
  expect(screen.getByRole('alert')).toHaveTextContent('Access no longer available');
  client.clear();
});
it('handles unauthorized and expired links explicitly', () => {
  const view=render(<ErrorMessage error={new RequestError(401,'Sign in')}/>);
  expect(screen.getByRole('link',{name:'Sign in'})).toHaveAttribute('href','/app/staff/login');
  view.rerender(<ErrorMessage error={new RequestError(410,'Invitation expired')}/>);
  expect(screen.getByRole('alert')).toHaveTextContent('Link unavailable');
});
