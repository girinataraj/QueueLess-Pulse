import * as DialogPrimitive from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import type { ReactNode } from 'react';
import { Button } from './button';
export function Dialog({ title, children, trigger }: { title: string; children: ReactNode; trigger: string }) {
  return <DialogPrimitive.Root><DialogPrimitive.Trigger asChild><Button variant="secondary">{trigger}</Button></DialogPrimitive.Trigger><DialogPrimitive.Portal><DialogPrimitive.Overlay className="dialog-overlay"/><DialogPrimitive.Content className="dialog-content"><DialogPrimitive.Title>{title}</DialogPrimitive.Title><DialogPrimitive.Description>Update configuration for this business. Changes take effect on the next request.</DialogPrimitive.Description><DialogPrimitive.Close asChild><button className="dialog-close" aria-label="Close dialog"><X size={20}/></button></DialogPrimitive.Close>{children}</DialogPrimitive.Content></DialogPrimitive.Portal></DialogPrimitive.Root>;
}
