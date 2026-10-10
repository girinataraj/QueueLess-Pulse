import { it, expect, vi } from 'vitest';
import { api, session } from './client';
it('sends signed-session credentials, no-store and CSRF for mutations', async () => {
  const fetcher=vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({csrf_token:'test-csrf',user:null,memberships:[],demo_mode:false}))).mockResolvedValueOnce(new Response(JSON.stringify({resource_path:'/owner'})));
  vi.stubGlobal('fetch',fetcher);
  await session();await api('/auth/logout',{});
  const options=fetcher.mock.calls[1]?.[1] as RequestInit;
  expect(options.credentials).toBe('same-origin');expect(options.cache).toBe('no-store');
  expect(String(options.body)).toContain('csrf_token=test-csrf');expect(options.method).toBe('POST');
});
it('preserves repeated permissions and does not send false checkbox values', async () => {
  const fetcher=vi.fn().mockResolvedValue(new Response('{}'));vi.stubGlobal('fetch',fetcher);
  await api('/owner/businesses/1/staff/2/permissions',{service_ids:['1','2'],is_active:false});
  const body=fetcher.mock.calls[0]?.[1].body as URLSearchParams;
  expect(body.getAll('service_ids')).toEqual(['1','2']);expect(body.has('is_active')).toBe(false);
});
it('surfaces server errors rather than returning a success result', async () => {
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({error:{code:'conflict',message:'Complete active ticket first'}}),{status:409})));
  await expect(api('/staff/services/1/call',{})).rejects.toThrow('Complete active ticket first');
});
