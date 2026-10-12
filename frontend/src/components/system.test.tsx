import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { ConfirmationDialog, Drawer, Pagination, StatusBadge, TokenDisplay, Tabs } from './system';

describe('operational design system',()=>{
  it('retains a textual status rather than relying on color',()=>{
    render(<><StatusBadge status="ON_BREAK"/><TokenDisplay number="E017"/></>);
    expect(screen.getByText('ON BREAK')).toHaveClass('status-on-break');
    expect(screen.getByLabelText('Currently serving E017')).toHaveTextContent('E017');
  });
  it('requires an explicit confirmation and prevents duplicate submissions while busy',async()=>{
    const confirm=vi.fn();const user=userEvent.setup();
    const view=render(<ConfirmationDialog open onOpenChange={()=>{}} title="Skip E017?" description="This records a no-show; no clinical details are stored." confirm="Confirm skip" onConfirm={confirm}/>);
    expect(screen.getByRole('dialog')).toHaveAccessibleName('Skip E017?');
    await user.click(screen.getByRole('button',{name:'Confirm skip'}));expect(confirm).toHaveBeenCalledOnce();
    view.rerender(<ConfirmationDialog open onOpenChange={()=>{}} title="Skip E017?" description="Saving" confirm="Confirm skip" onConfirm={confirm} busy/>);
    expect(screen.getByRole('button',{name:'Saving…'})).toBeDisabled();
  });
  it('allows keyboard closing of mobile navigation',async()=>{
    function Example(){const [open,setOpen]=useState(false);return <><button onClick={()=>setOpen(true)}>Menu</button><Drawer title="Workspaces" open={open} onOpenChange={setOpen}><a href="/app/">Patient portal</a></Drawer></>;}
    const user=userEvent.setup();render(<Example/>);await user.click(screen.getByRole('button',{name:'Menu'}));
    expect(screen.getByRole('dialog',{name:'Workspaces'})).toBeInTheDocument();await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
  it('disables pagination at actual boundaries',async()=>{
    const onChange=vi.fn();render(<Pagination page={1} pages={2} onChange={onChange}/>);
    expect(screen.getByRole('button',{name:'Previous'})).toBeDisabled();
    await userEvent.click(screen.getByRole('button',{name:'Next'}));expect(onChange).toHaveBeenCalledWith(2);
  });
  it('supports tab keyboard navigation and preserves unsaved fields in inactive panels',async()=>{
    function Example(){const [value,setValue]=useState('overview');return <Tabs label="Business sections" value={value} onValueChange={setValue} items={[{id:'overview',label:'Overview',content:<p>Actual queue metrics</p>},{id:'team',label:'Team',content:<label>Desk name<input/></label>}]}/>;}
    const user=userEvent.setup();render(<Example/>);const overview=screen.getByRole('tab',{name:'Overview'});
    overview.focus();await user.keyboard('{ArrowRight}');expect(screen.getByRole('tab',{name:'Team'})).toHaveFocus();
    await user.type(screen.getByLabelText('Desk name'),'Reception A');screen.getByRole('tab',{name:'Team'}).focus();await user.keyboard('{Home}');
    expect(overview).toHaveAttribute('aria-selected','true');expect(screen.getByLabelText('Desk name')).not.toBeVisible();
    await user.keyboard('{End}');expect(screen.getByLabelText('Desk name')).toHaveValue('Reception A');
  });
});
