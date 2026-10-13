import { printService } from '../lib/print';
import * as Dialog from '@radix-ui/react-dialog';
import { X, Search as SearchIcon } from 'lucide-react';
import { useId, type ReactNode, type ComponentProps } from 'react';
import { Button } from './ui/button';

export function PageHeader({ eyebrow, title, description, children }: { eyebrow: string; title: string; description?: string; children?: ReactNode }) {
  return <header className="page-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1>{description && <p>{description}</p>}</div><div className="page-tools">{children}</div></header>;
}
export function KPIStatCard({ label, value, detail, tone = 'neutral', icon }: { label: string; value: ReactNode; detail?: string; tone?: 'neutral' | 'success' | 'warning'; icon?: ReactNode }) {
  return <div className={'kpi-card tone-'+tone}><span className="kpi-label">{label}{icon}</span><strong>{value}</strong>{detail && <small>{detail}</small>}</div>;
}
export function StatusBadge({ status, children }: { status: string; children?: ReactNode }) {
  return <span className={'status-badge status-'+status.toLowerCase().replaceAll('_','-')}>{children ?? status.replaceAll('_',' ')}</span>;
}
export function TokenDisplay({ number, label = 'Currently serving', large = false }: { number: string; label?: string; large?: boolean }) {
  return <div className={'token-focus'+(large?' large':'')}><span className="eyebrow">{label}</span><div className="token-display" aria-label={label+' '+number}>{number}</div></div>;
}
export function ActionToolbar({ children }: { children: ReactNode }) { return <div className="actions action-toolbar">{children}</div>; }
export function EmptyState({ title, children }: { title: string; children?: ReactNode }) { return <div className="empty-state"><h2>{title}</h2>{children}</div>; }
export function IconButton({ label, children, ...props }: ComponentProps<'button'> & { label: string }) { return <Button variant="secondary" className="icon-button" aria-label={label} title={label} {...props}>{children}</Button>; }
export function AccessibleTooltip({ label, children }: { label: string; children: ReactNode }) {
  const id=useId(); return <span className="tooltip-anchor" tabIndex={0} aria-describedby={id}>{children}<span className="tooltip" role="tooltip" id={id}>{label}</span></span>;
}
export function Drawer({ open, onOpenChange, title, description = "Choose a workspace.", children }: { open: boolean; onOpenChange: (open: boolean) => void; title: string; description?: string; children: ReactNode }) {
  return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal><Dialog.Overlay className="dialog-overlay"/><Dialog.Content className="drawer"><Dialog.Title>{title}</Dialog.Title><Dialog.Description>{description}</Dialog.Description><Dialog.Close asChild><IconButton label="Close panel"><X size={20}/></IconButton></Dialog.Close>{children}</Dialog.Content></Dialog.Portal></Dialog.Root>;
}
export function ConfirmationDialog({ open, onOpenChange, title, description, confirm, onConfirm, busy = false, danger = false, error }: { open: boolean; onOpenChange: (open: boolean) => void; title: string; description: string; confirm: string; onConfirm: () => void; busy?: boolean; danger?: boolean; error?: Error|null }) {
  return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal><Dialog.Overlay className="dialog-overlay"/><Dialog.Content className="dialog-content"><Dialog.Title>{title}</Dialog.Title><Dialog.Description>{description}</Dialog.Description>{error&&<p role="alert" className="notice error">{error.message}</p>}<div className="actions"><Button variant={danger?'destructive':'default'} disabled={busy} onClick={onConfirm}>{busy?'Saving…':confirm}</Button><Dialog.Close asChild><Button variant="secondary" disabled={busy}>Keep current state</Button></Dialog.Close></div></Dialog.Content></Dialog.Portal></Dialog.Root>;
}
export function FilterBar({ children }: { children: ReactNode }) { return <div className="filter-bar">{children}</div>; }
export function Tabs({ label, items, value, onValueChange }: { label: string; items: { id: string; label: string; content: ReactNode }[]; value: string; onValueChange: (value: string) => void }) {
  const prefix=useId();
  return <div className="tabs"><div role="tablist" aria-label={label} className="tabs-list">{items.map((item,index)=><button key={item.id} type="button" role="tab" id={prefix+'-tab-'+item.id} aria-selected={value===item.id} aria-controls={prefix+'-panel-'+item.id} tabIndex={value===item.id?0:-1} onClick={()=>onValueChange(item.id)} onKeyDown={event=>{
    let next:number;
    if(event.key==='ArrowRight')next=(index+1)%items.length;
    else if(event.key==='ArrowLeft')next=(index+items.length-1)%items.length;
    else if(event.key==='Home')next=0;
    else if(event.key==='End')next=items.length-1;
    else return;
    event.preventDefault();const target=items[next];if(target){onValueChange(target.id);document.getElementById(prefix+'-tab-'+target.id)?.focus();}
  }}>{item.label}</button>)}</div>{items.map(item=><div key={item.id} role="tabpanel" tabIndex={0} id={prefix+'-panel-'+item.id} aria-labelledby={prefix+'-tab-'+item.id} hidden={value!==item.id}>{item.content}</div>)}</div>;
}
export function Search({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string }) {
  const id=useId();return <div className="search-field"><label htmlFor={id}>{label}</label><div><SearchIcon aria-hidden size={18}/><input id={id} type="search" value={value} onChange={e=>onChange(e.target.value)} placeholder={placeholder}/></div></div>;
}
export function DateFilter({ label = 'Business-local date', value, onChange }: { label?: string; value: string; onChange: (value: string) => void }) { const id=useId();return <div><label htmlFor={id}>{label}</label><input id={id} type="date" value={value} onChange={e=>onChange(e.target.value)}/></div>; }
export function Pagination({ page, pages, onChange }: { page: number; pages: number; onChange: (page: number) => void }) { return <nav aria-label="Pagination" className="pagination"><Button variant="secondary" disabled={page<=1} onClick={()=>onChange(page-1)}>Previous</Button><span>Page {page} of {pages || 1}</span><Button variant="secondary" disabled={page>=pages} onClick={()=>onChange(page+1)}>Next</Button></nav>; }
export function DataTable({ caption, headings, children }: { caption: string; headings: string[]; children: ReactNode }) { return <div className="table-wrap" tabIndex={0} role="region" aria-label={caption}><table><caption>{caption}</caption><thead><tr>{headings.map(h=><th key={h} scope="col">{h}</th>)}</tr></thead><tbody>{children}</tbody></table></div>; }
export function QRDisplayCard({ serviceId, service, patientUrl }: { serviceId: number; service: string; patientUrl: string }) {
  return <div className="reception-qr"><img src={`/api/v1/staff/services/${serviceId}/qr.png`} alt={`${service} service QR`} className="qr" width="280" height="280"/><h3>Patient check-in</h3><p className="hint">Scan for {service} · No account required.</p><a className="text-link patient-link" href={patientUrl}>Open patient queue</a><ActionToolbar><a href={`/api/v1/staff/services/${serviceId}/qr.png?download=1`} className="button button-secondary" download>Download QR</a><Button variant="secondary" onClick={()=>printService(serviceId,'qr')}>Print QR</Button></ActionToolbar></div>;
}
