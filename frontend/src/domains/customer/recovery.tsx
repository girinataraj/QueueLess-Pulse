import { Link, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import type { TicketList } from '../../api/contracts';
import { useLive, QueryState } from '../../components/feedback';
import { Drawer, StatusBadge } from '../../components/system';
import { Button } from '../../components/ui/button';
import { recoverPath } from '../../lib/navigation';
export function TicketRecovery({open,onOpenChange}: {open:boolean;onOpenChange:(open:boolean)=>void}){
  const query=useLive<TicketList>('/my-tickets',undefined,open);const [link,setLink]=useState('');const [error,setError]=useState('');const navigate=useNavigate();
  function recover(){const path=recoverPath(link,window.location.origin);if(!path){setError('Paste a saved QueueLess Pulse ticket link from this application.');return;}setError('');setLink('');onOpenChange(false);navigate(path);}
  return <Drawer open={open} onOpenChange={onOpenChange} title="Your tickets" description="Recover a ticket from this browser or a private saved link.">
    <p className="hint">Only tickets issued in this browser appear here. Private recovery links also work on another device.</p>
    <QueryState query={query}><ul className="ticket-history">{query.data?.map(t=><li key={t.token}><Link onClick={()=>onOpenChange(false)} to={'/ticket/'+t.token}><strong>{t.display_number}</strong><span>{t.service_name}<small>{t.business_name} · {t.business_date}</small></span><StatusBadge status={t.status}/></Link></li>)}</ul>{!query.data?.length&&<p className="recovery-empty">No tickets saved in this browser. Use your private saved link below, or join through the service QR.</p>}</QueryState>
    <form className="recovery-form" onSubmit={e=>{e.preventDefault();recover();}}><label htmlFor="saved-ticket-link">Saved ticket link</label><input id="saved-ticket-link" type="password" autoComplete="off" value={link} onChange={e=>setLink(e.target.value)} aria-describedby={error?'recovery-error':undefined}/>{error&&<p id="recovery-error" className="field-error" role="alert">{error}</p>}<Button type="submit" disabled={!link.trim()}>Recover ticket</Button></form>
    <p className="hint">Keep recovery links private. This drawer never searches other patients' tickets.</p>
  </Drawer>;
}
