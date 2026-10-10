import { useParams, useSearchParams } from 'react-router-dom';
import type { DisplayList } from '../../api/contracts';
import { useLive, QueryState, Connection } from '../../components/feedback';
import { Heading } from '../../components/layout';
import { Button } from '../../components/ui/button';
import { useState } from 'react';
export function DisplayPage() {
  const {slug=''}=useParams();const [params]=useSearchParams();const branch=params.get('branch_id');
  const query=useLive<DisplayList>('/display/'+encodeURIComponent(slug)+(branch ? '?branch_id='+encodeURIComponent(branch) : ''),3000);
  const [error,setError]=useState('');
  async function fullscreen() { try { if(document.fullscreenElement) await document.exitFullscreen(); else await document.documentElement.requestFullscreen(); } catch { setError('Full-screen mode is unavailable in this browser.'); } }
  return <div className="display-page"><Heading eyebrow="RECEPTION" title="Now serving" description="Please proceed to your service counter when your token appears."><Button variant="secondary" onClick={() => void fullscreen()}>Full screen</Button></Heading><Connection query={query}/>{error && <p role="alert">{error}</p>}<QueryState query={query}><div className="display-grid">{query.data?.map(s => <article key={s.service_id} className="display-card"><span className="eyebrow">{s.branch_name}</span><h2>{s.service_name}</h2><p>{s.counter_label}</p><div className="display-token">{s.currently_called}</div><p>{s.waiting_count} waiting</p></article>)}</div>{!query.data?.length && <div className="empty-state">No active services at this location.</div>}</QueryState></div>;
}
