import { useParams, useSearchParams } from 'react-router-dom';
import type { DisplayList } from '../../api/contracts';
import { useLive, QueryState, Connection } from '../../components/feedback';
import { Heading } from '../../components/layout';
import { Button } from '../../components/ui/button';
import { StatusBadge } from '../../components/system';
import { useEffect, useRef, useState } from 'react';
import { announce, enableSound } from '../../lib/announcements';
export function DisplayPage(){
  const {slug=''}=useParams();const [params,setParams]=useSearchParams();const branch=params.get('branch_id');const selected=params.get('service_id')??'';
  const query=useLive<DisplayList>('/display/'+encodeURIComponent(slug)+(branch?'?branch_id='+encodeURIComponent(branch):''),3000);
  const [error,setError]=useState('');const [audio,setAudio]=useState<AudioContext|null>(null);const previous=useRef<string|null>(null);
  const announcement=query.data?.filter(s=>!selected||String(s.service_id)===selected).map(s=>s.announcement_id).join(',')??'';
  useEffect(()=>{if(previous.current!==null&&announcement&&announcement!==previous.current)announce(audio);previous.current=announcement;},[announcement,audio]);
  useEffect(()=>()=>{if(audio && audio.state!=='closed')void audio.close().catch(()=>{});},[audio]);
  async function sound(){try{if(audio){await audio.close();setAudio(null);}else setAudio(await enableSound());setError('');}catch{setError('Sound is unavailable; the display continues updating visually.');}}
  async function fullscreen(){try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch{setError('Full-screen mode is unavailable in this browser.');}}
  return <div className="display-page"><Heading eyebrow={query.data?.[0]?.business_name??'RECEPTION DISPLAY'} title="Now serving" description="Please proceed to your service counter when your token appears."><Button variant="secondary" onClick={()=>void fullscreen()}>Full screen</Button><Button variant="secondary" onClick={()=>void sound()}>{audio?'Disable sound':'Enable announcement tone'}</Button></Heading><div className="display-toolbar"><Connection query={query}/><label htmlFor="display-service">Show service<select id="display-service" value={selected} onChange={e=>setParams(prev=>{if(e.target.value)prev.set('service_id',e.target.value);else prev.delete('service_id');return prev;})}><option value="">All configured services</option>{query.data?.map(s=><option key={s.service_id} value={String(s.service_id)}>{s.service_name}</option>)}</select></label></div>{error&&<p className="notice error" role="alert">{error}</p>}<QueryState query={query}><div className="display-grid">{query.data?.filter(s=>!selected||String(s.service_id)===selected).map(s=><article key={s.service_id} className="display-card"><span className="eyebrow">{s.branch_name}</span><h2>{s.service_name}</h2><p className="display-counter">{s.counter_label||'Service counter'}</p><span className="display-serving-label">NOW SERVING</span><div className="display-token" key={s.announcement_id} aria-live="polite" aria-atomic="true">{s.currently_called}</div><div className="display-bottom"><span><strong>{s.waiting_count}</strong> waiting</span><StatusBadge status={s.availability}/></div><p className="hint">Business date {s.business_date}</p></article>)}</div>{(!query.data?.length||selected&&!query.data.some(s=>String(s.service_id)===selected))&&<div className="empty-state">No active services for this selection.</div>}</QueryState><p className="hint">Public queue information only · Foreground updates every 3 seconds</p></div>;
}
