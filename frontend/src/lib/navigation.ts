export function ownerSectionPath(businessId: string|number, section: string, params = new URLSearchParams(), review?: string) {
  const next=new URLSearchParams(params);next.set('section',section);
  if(review)next.set('review',review);
  return `/owner/business/${businessId}?${next}`;
}
export function recoverPath(value: string, origin: string) {
  try {
    const url=new URL(value.trim(),origin);
    if(url.origin!==origin||url.username||url.password||url.search||url.hash)return null;
    const match=/^\/app\/ticket\/([A-Za-z0-9_-]{16,128})$/.exec(url.pathname);
    return match?'/ticket/'+match[1]:null;
  } catch { return null; }
}
export function experience(path: string, search: string) {
  if(path.endsWith('/display')||path==='/'&&new URLSearchParams(search).get('view')==='display')return 'display';
  if(path.includes('/login')||path==='/owner/register'||path.startsWith('/invite/'))return 'access';
  if(path.startsWith('/owner'))return 'owner';
  if(path==='/staff/reception')return 'reception';
  if(path.startsWith('/staff'))return 'doctor';
  return 'patient';
}
