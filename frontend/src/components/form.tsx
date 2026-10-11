import { useId } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import type { Values } from '../api/client';
import { ErrorMessage } from './feedback';
import { Button } from './ui/button';
export type Field = { name: string; label: string; type?: 'text' | 'password' | 'email' | 'textarea' | 'select' | 'checkbox' | 'multiselect' | 'number' | 'date'; required?: boolean; min?: number; max?: number; pattern?: string; options?: { value: string; label: string }[]; hint?: string };
export function formSchema(fields: Field[]) {
  return z.record(z.string(), z.union([z.string(), z.boolean(), z.array(z.string())])).superRefine((values, ctx) => {
    for (const f of fields) {
      const value = values[f.name] ?? ''; if (typeof value !== 'string') continue;
      let message = '';
      if (f.required && !value.trim()) message = `${f.label} is required.`;
      else if (f.type === 'number' && value && (!/^\d+$/.test(value) || Number(value) < (f.min ?? 1) || Number(value) > (f.max ?? 2147483647))) message = `${f.label} must be between ${f.min ?? 1} and ${f.max ?? 2147483647}.`;
      else if (f.type !== 'number' && f.min && value.length < f.min) message = `${f.label} needs at least ${f.min} characters.`;
      else if (f.type !== 'number' && f.max && value.length > f.max) message = `${f.label} must have at most ${f.max} characters.`;
      else if (f.type === 'email' && value && !z.email().safeParse(value).success) message = 'Enter a valid email address.';
      else if (f.pattern && value && !new RegExp(f.pattern).test(value)) message = `Check the format of ${f.label.toLowerCase()}.`;
      if (message) ctx.addIssue({ code: 'custom', path: [f.name], message });
    }
    if ('confirm_password' in values && values.confirm_password !== values.password) ctx.addIssue({ code: 'custom', path: ['confirm_password'], message: 'Passwords must match.' });
  });
}
export function Form({ fields, initial = {}, submit, onSubmit, busy = false, error = null }: { fields: Field[]; initial?: Values; submit: string; onSubmit: (values: Values) => Promise<unknown>; busy?: boolean; error?: Error | null }) {
  const id = useId();
  const defaults = Object.fromEntries(fields.map(f => [f.name, initial[f.name] ?? (f.type === 'checkbox' ? true : f.type === 'multiselect' ? [] : '')]));
  const { register, handleSubmit, formState: { errors } } = useForm<Values>({ defaultValues: defaults, resolver: zodResolver(formSchema(fields)) });
  return <form noValidate onSubmit={e => void handleSubmit(async values => { try { await onSubmit(values); } catch { /* Mutation error is rendered below. */ } })(e)} className="form-grid"><ErrorMessage error={error}/>{fields.map(f => {
    const fieldId = id + '-' + f.name; const message = errors[f.name]?.message;
    const common = { id: fieldId, 'aria-invalid': Boolean(message), 'aria-describedby': f.hint || message ? fieldId + '-help' : undefined, ...register(f.name) };
    return <div key={f.name} className={f.type === 'textarea' || f.type === 'multiselect' ? 'field wide' : 'field'}>{f.type !== 'checkbox' && <label htmlFor={fieldId}>{f.label}{f.required ? ' *' : ''}</label>}
      {f.type === 'textarea' ? <textarea {...common} rows={3}/> : f.type === 'select' ? <select {...common}>{f.options?.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select> : f.type === 'multiselect' ? <fieldset><legend>{f.label}</legend>{f.options?.map(o => <label className="check" key={o.value}><input type="checkbox" value={o.value} {...register(f.name)}/>{o.label}</label>)}</fieldset> : f.type === 'checkbox' ? <label className="check"><input type="checkbox" {...common}/>{f.label}</label> : <input {...common} type={f.type ?? 'text'} autoComplete={f.type === 'password' ? 'new-password' : f.name === 'username' ? 'username' : 'off'}/>}
      {(f.hint || message) && <p id={fieldId+'-help'} className={message ? 'field-error' : 'hint'}>{message ? String(message) : f.hint}</p>}
    </div>;
  })}<div className="wide"><Button type="submit" disabled={busy}>{busy ? 'Saving…' : submit}</Button></div></form>;
}
