import { describe, it, expect } from 'vitest';
import { experience, ownerSectionPath, recoverPath } from './navigation';
describe('focused route navigation',()=>{
  it('keeps patient and kiosk shells independent of protected role routes',()=>{
    expect(experience('/b/clinic/service/1','')).toBe('patient');
    expect(experience('/ticket/private-capability','')).toBe('patient');
    expect(experience('/b/clinic/display','')).toBe('display');
    expect(experience('/','?view=display')).toBe('display');
    expect(experience('/staff/reception','')).toBe('reception');
    expect(experience('/staff/dashboard','')).toBe('doctor');
    expect(experience('/owner/business/1','')).toBe('owner');
    expect(experience('/owner/login','')).toBe('access');
  });
  it('preserves history scope and paging while consolidating the review route',()=>{
    const path=ownerSectionPath(7,'reviews',new URLSearchParams('date=2026-10-12&service_id=9&status=SKIPPED&page=2'),'history');
    const url=new URL(path,'https://queue.example');
    expect(url.pathname).toBe('/owner/business/7');
    expect(Object.fromEntries(url.searchParams)).toEqual({date:'2026-10-12',service_id:'9',status:'SKIPPED',page:'2',section:'reviews',review:'history'});
  });
  it('accepts an actual saved same-origin capability path without exposing its value elsewhere',()=>{
    expect(recoverPath('https://queue.example/app/ticket/synthetic_saved_123456','https://queue.example')).toBe('/ticket/synthetic_saved_123456');
    expect(recoverPath('/app/ticket/synthetic_saved_123456','https://queue.example')).toBe('/ticket/synthetic_saved_123456');
  });
  it('rejects foreign, credentialed, privileged and malformed recovery destinations',()=>{
    for(const value of ['https://other.example/app/ticket/synthetic_saved_123456','https://name:secret@queue.example/app/ticket/synthetic_saved_123456','/app/owner/business/1','javascript:alert(1)','/app/ticket/short','/app/ticket/synthetic_saved_123456?next=/owner'])expect(recoverPath(value,'https://queue.example')).toBeNull();
  });
});
