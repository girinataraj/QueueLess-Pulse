import { it, expect } from 'vitest';
import { render,screen } from '@testing-library/react';
import { Analytics } from './analytics';
const stats={waiting:2,called:1,completed:30,skipped:8,cancelled:0,completed_today:3,skipped_today:0,business_date:'2026-10-11',average_wait:null,average_duration:4.2,wait_samples:0,duration_samples:3,throughput:[{date:'2026-10-10',completed:3}]};
it('renders actual samples and an accessible throughput chart',()=>{
  render(<Analytics stats={stats}/>);
  expect(screen.getByRole('img',{name:'Completed tickets by business date'})).toBeVisible();
  expect(screen.getByText('2026-10-10: 3 completed')).toBeVisible();
  expect(screen.getByText('—')).toBeVisible();
  expect(screen.queryByText('30')).not.toBeInTheDocument();
  expect(screen.queryByText('8')).not.toBeInTheDocument();
});
