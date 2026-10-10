import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Form, formSchema } from './form';
import { accountFields } from '../domains/auth/pages';
describe('form validation', () => {
  it('rejects weak password and mismatched confirmation', () => {
    expect(formSchema(accountFields).safeParse({ username:'owner', password:'short', confirm_password:'other' }).success).toBe(false);
    expect(formSchema(accountFields).safeParse({ username:'owner', password:'secure-password-123', confirm_password:'secure-password-123',email:'invalid' }).success).toBe(false);
  });
  it('enforces the service duration boundary', () => {
    const schema=formSchema([{name:'duration',label:'Duration',type:'number',min:1,max:120,required:true}]);
    for (const value of ['0','121','NaN','2.5']) expect(schema.safeParse({duration:value}).success).toBe(false);
    expect(schema.safeParse({duration:'120'}).success).toBe(true);
  });
  it('shows accessible field errors without submitting invalid values', async () => {
    const submit=vi.fn().mockResolvedValue(undefined);const user=userEvent.setup();
    render(<Form fields={[{name:'name',label:'Business name',required:true}]} submit="Save" onSubmit={submit}/>);
    await user.click(screen.getByRole('button',{name:'Save'}));
    expect(await screen.findByText('Business name is required.')).toBeVisible();
    expect(screen.getByRole('textbox',{name:'Business name *'})).toHaveAttribute('aria-invalid','true');
    expect(submit).not.toHaveBeenCalled();
    await user.type(screen.getByRole('textbox'), 'Clinic');await user.click(screen.getByRole('button',{name:'Save'}));
    await waitFor(()=>expect(submit).toHaveBeenCalledWith({name:'Clinic'}));
  });
  it('disables submission while a mutation is pending', () => {
    render(<Form fields={[]} submit="Save" busy onSubmit={vi.fn()}/>);
    expect(screen.getByRole('button',{name:'Saving…'})).toBeDisabled();
  });
});
