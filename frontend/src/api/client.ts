import type { ApiError, Session } from './contracts';
export type Values = Record<string, string | boolean | string[]>;
let csrfToken = '';
export class RequestError extends Error { constructor(public status: number, message: string) { super(message); } }
export async function api<T>(path: string, values?: Values): Promise<T> {
  const body = values ? new URLSearchParams() : undefined;
  if (values && body) {
    for (const [name, value] of Object.entries(values)) {
      if (Array.isArray(value)) value.forEach(v => body.append(name, v));
      else if (typeof value === 'boolean') { if (value) body.append(name, 'on'); }
      else body.append(name, value);
    }
    body.set('csrf_token', csrfToken);
  }
  const response = await fetch('/api/v1' + path, { method: body ? 'POST' : 'GET', body, credentials: 'same-origin', cache: 'no-store' });
  if (!response.ok) {
    const data = await response.json() as ApiError;
    throw new RequestError(response.status, data.error?.message || 'Request failed. Please retry.');
  }
  return response.json() as Promise<T>;
}
export async function session(): Promise<Session> { const data = await api<Session>('/session'); csrfToken = data.csrf_token; return data; }
