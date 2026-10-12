import * as Dialog from '@radix-ui/react-dialog';
import { X, ChevronRight, Search as SearchIcon } from 'lucide-react';
import { useId, type ReactNode, type ComponentProps } from 'react';
import { Link } from 'react-router-dom';
import { Button } from './ui/button';

export function PageHeader({ eyebrow, title, description, children }: { eyebrow: string; title: string; description?: string; children?: ReactNode }) {
  return <header className="page-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1>{description && <p>{description}</p>}</div><div className="page-tools">{children}</div></header>;
}
export function Breadcrumbs({ items }: { items: { label: string; to?: string }[] }) {
  return <nav aria-label="Breadcrumb" className="breadcrumbs"><ol>{items.map((item, index) => <li key={item.label}>{index > 0 && <ChevronRight aria-hidden size={14}/>} {item.to ? <Link to={item.to}>{item.label}</Link> : <span aria-current="page">{item.label}</span>}</li>)}</ol></nav>;
}
export function KPIStatCard({ label, value, detail, tone = 'neutral' }: { label: string; value: ReactNode; detail?: string; tone?: 'neutral' | 'success' | 'warning' }) {
  return <div className={'kpi-card tone-'+tone}><span>{label}</span><strong>{value}</strong>{detail && <small>{detail}</small>}</div>;
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
export function Drawer({ open, onOpenChange, title, children }: { open: boolean; onOpenChange: (open: boolean) => void; title: string; children: ReactNode }) {
  return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal><Dialog.Overlay className="dialog-overlay"/><Dialog.Content className="drawer"><Dialog.Title>{title}</Dialog.Title><Dialog.Description>Choose your QueueLess Pulse workspace.</Dialog.Description><Dialog.Close asChild><IconButton label="Close navigation"><X size={20}/></IconButton></Dialog.Close>{children}</Dialog.Content></Dialog.Portal></Dialog.Root>;
}
export function ConfirmationDialog({ open, onOpenChange, title, description, confirm, onConfirm, busy = false, danger = false }: { open: boolean; onOpenChange: (open: boolean) => void; title: string; description: string; confirm: string; onConfirm: () => void; busy?: boolean; danger?: boolean }) {
  return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal><Dialog.Overlay className="dialog-overlay"/><Dialog.Content className="dialog-content"><Dialog.Title>{title}</Dialog.Title><Dialog.Description>{description}</Dialog.Description><div className="actions"><Button variant={danger?'destructive':'default'} disabled={busy} onClick={onConfirm}>{busy?'Saving…':confirm}</Button><Dialog.Close asChild><Button variant="secondary" disabled={busy}>Keep current state</Button></Dialog.Close></div></Dialog.Content></Dialog.Portal></Dialog.Root>;
}
export function FilterBar({ children }: { children: ReactNode }) { return <div className="filter-bar">{children}</div>; }
export function Search({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string }) {
  const id=useId();return <div className="search-field"><label htmlFor={id}>{label}</label><div><SearchIcon aria-hidden size={18}/><input id={id} type="search" value={value} onChange={e=>onChange(e.target.value)} placeholder={placeholder}/></div></div>;
}
export function DateFilter({ label = 'Business-local date', value, onChange }: { label?: string; value: string; onChange: (value: string) => void }) { const id=useId();return <div><label htmlFor={id}>{label}</label><input id={id} type="date" value={value} onChange={e=>onChange(e.target.value)}/></div>; }
export function Pagination({ page, pages, onChange }: { page: number; pages: number; onChange: (page: number) => void }) { return <nav aria-label="Pagination" className="pagination"><Button variant="secondary" disabled={page<=1} onClick={()=>onChange(page-1)}>Previous</Button><span>Page {page} of {pages || 1}</span><Button variant="secondary" disabled={page>=pages} onClick={()=>onChange(page+1)}>Next</Button></nav>; }
export function DataTable({ caption, headings, children }: { caption: string; headings: string[]; children: ReactNode }) { return <div className="table-wrap" tabIndex={0} role="region" aria-label={caption}><table><caption>{caption}</caption><thead><tr>{headings.map(h=><th key={h} scope="col">{h}</th>)}</tr></thead><tbody>{children}</tbody></table></div>; }
export function QRDisplayCard({ serviceId, service, patientUrl }: { serviceId: number; service: string; patientUrl: string }) {
  return <div className="reception-qr"><img src={`/api/v1/staff/services/${serviceId}/qr.png`} alt={`${service} service QR`} className="qr" width="280" height="280"/><h3>Scan. Join. Follow your token.</h3><p className="hint">No patient account required.</p><a className="text-link patient-link" href={patientUrl}>Open patient queue</a><ActionToolbar><a href={`/api/v1/staff/services/${serviceId}/qr.png?download=1`} className="button button-secondary" download>Download QR</a><Button variant="secondary" onClick={()=>window.print()}>Print QR</Button></ActionToolbar></div>;
}
