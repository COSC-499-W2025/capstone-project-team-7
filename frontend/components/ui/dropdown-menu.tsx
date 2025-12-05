import React, { createContext, useContext, useMemo, useState } from "react";
import { cn } from "@/lib/utils";

interface DropdownContextValue {
  open: boolean;
  setOpen: (next: boolean) => void;
}

const DropdownContext = createContext<DropdownContextValue | null>(null);

interface DropdownMenuProps {
  children: React.ReactNode;
}

export function DropdownMenu({ children }: DropdownMenuProps) {
  const [open, setOpen] = useState(false);

  const ctx = useMemo<DropdownContextValue>(() => ({ open, setOpen }), [open]);

  return <DropdownContext.Provider value={ctx}>{children}</DropdownContext.Provider>;
}

export function DropdownMenuTrigger({ className, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const ctx = useDropdownContext();
  return (
    <button
      type="button"
      className={cn(
        "inline-flex items-center justify-center gap-1 rounded-md border border-border bg-card px-3 py-2 text-sm shadow-sm",
        "transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        "ring-offset-background",
        className
      )}
      aria-haspopup="menu"
      aria-expanded={ctx.open}
      onClick={() => ctx.setOpen(!ctx.open)}
      {...props}
    />
  );
}

interface DropdownMenuContentProps extends React.HTMLAttributes<HTMLDivElement> {}

export function DropdownMenuContent({ className, children, ...props }: DropdownMenuContentProps) {
  const ctx = useDropdownContext();
  if (!ctx.open) return null;

  return (
    <div
      role="menu"
      className={cn(
        "mt-2 min-w-[12rem] rounded-md border border-border bg-popover p-2 text-sm shadow-md shadow-black/20",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

interface DropdownMenuItemProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {}

export function DropdownMenuItem({ className, onClick, children, ...props }: DropdownMenuItemProps) {
  const ctx = useDropdownContext();
  return (
    <button
      type="button"
      role="menuitem"
      className={cn(
        "flex w-full items-center justify-start rounded-sm px-3 py-2 text-left transition-colors",
        "hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        "ring-offset-background",
        className
      )}
      onClick={(e) => {
        onClick?.(e);
        ctx.setOpen(false);
      }}
      {...props}
    >
      {children}
    </button>
  );
}

function useDropdownContext(): DropdownContextValue {
  const ctx = useContext(DropdownContext);
  if (!ctx) {
    throw new Error("DropdownMenu components must be used within <DropdownMenu>");
  }
  return ctx;
}
