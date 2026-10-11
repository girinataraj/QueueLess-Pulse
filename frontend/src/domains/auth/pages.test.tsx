import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { vi, test, expect } from 'vitest';
import { AuthPage } from './pages';

function show(register=false,staff=false) {
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({csrf_token:'unit-test-token',user:null,memberships:[],demo_mode:true,gateway_required:false,owner_registration_enabled:false}),{headers:{'Content-Type':'application/json'}})));
  return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MemoryRouter><AuthPage register={register} staff={staff}/></MemoryRouter></QueryClientProvider>);
}
test('closed staging registration offers existing login without an account form',async()=>{
  show(true);expect(await screen.findByRole('heading',{name:'Owner registration is closed'})).toBeInTheDocument();
  expect(screen.queryByRole('button',{name:'Create account'})).not.toBeInTheDocument();
  expect(screen.queryByLabelText(/Password/)).not.toBeInTheDocument();
});
test('existing staff can sign in without a new-owner registration invitation',async()=>{
  show(false,true);expect(await screen.findByRole('heading',{name:'Staff sign in'})).toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Sign in'})).toBeInTheDocument();
  expect(screen.queryByRole('link',{name:'Create an account'})).not.toBeInTheDocument();
});
