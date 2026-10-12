import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Queue } from '../../api/contracts';
import { DoctorQueueCard } from './doctor';
const queue:Queue={id:1,name:'Eye Consultation',branch:'Main Reception',business:'Fictional clinic',counter:'Room 1',active:true,waiting:[{id:11,number:'E011',business_date:'2026-10-12'}],called:{id:10,number:'E010',business_date:'2026-10-12'},completed_today:7,skipped_today:2,business_date:'2026-10-12',duty:{state:'AVAILABLE',started_at:null,updated_at:null},called_at:'2026-10-12T06:00:00Z',average_duration_today:5,duration_samples_today:7,activity:[]};
function setup(data:Queue){const client=new QueryClient();const wrap=(q:Queue)=><QueryClientProvider client={client}><DoctorQueueCard queue={q}/></QueryClientProvider>;return {view:render(wrap(data)),wrap};}
afterEach(()=>vi.unstubAllGlobals());
describe('Doctor operational safety',()=>{
  it('blocks next, break and end when a called token is unresolved',()=>{
    setup(queue);for(const name of ['Call Next','Start break','End duty'])expect(screen.getByRole('button',{name})).toBeDisabled();
    expect(screen.getByRole('button',{name:'Recall token'})).toBeEnabled();expect(screen.getByRole('button',{name:'Mark Reviewed'})).toBeEnabled();
  });
  it('keeps the original skip target if polling changes the active consultation',async()=>{
    const fetch=vi.fn().mockResolvedValue({ok:true,json:async()=>({resource_path:'/staff/dashboard'})});vi.stubGlobal('fetch',fetch);
    const {view,wrap}=setup(queue);await userEvent.click(screen.getByRole('button',{name:'Skip'}));
    view.rerender(wrap({...queue,called:{id:11,number:'E011',business_date:'2026-10-12'}}));
    expect(screen.getByRole('dialog')).toHaveAccessibleName('Skip E010?');await userEvent.click(screen.getByRole('button',{name:'Confirm skip'}));
    await waitFor(()=>expect(fetch).toHaveBeenCalled());expect(fetch.mock.calls[0]?.[0]).toBe('/api/v1/staff/tickets/10/skip');
  });
  it('shows a break reason and permits resume without consuming a waiting token',()=>{
    setup({...queue,called:null,duty:{...queue.duty,state:'ON_BREAK'}});
    expect(screen.getByRole('button',{name:'Call Next'})).toBeDisabled();expect(screen.getByRole('button',{name:'Resume duty'})).toBeEnabled();expect(screen.getByText('E011')).toBeInTheDocument();
  });
});
