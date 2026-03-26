import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
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
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const ctx = useMemo<DropdownContextValue>(() => ({ open, setOpen }), [open]);

  return (
    <DropdownContext.Provider value={ctx}>
      <div ref={ref} className="relative">{children}</div>
    </DropdownContext.Provider>
  );
}

export function DropdownMenuTrigger({ className, onClick, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const ctx = useDropdownContext();
  return (
    <button
      type="button"
      className={cn(
        "inline-flex items-center justify-center gap-1 rounded-md border-2 border-border bg-card px-3 py-2 text-sm",
        "transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        "ring-offset-background",
        className
      )}
      aria-haspopup="menu"
      aria-expanded={ctx.open}
      onClick={(e) => {
        // Toggle first, then forward to consumer — ordering prevents
        // double-toggle if the consumer's handler also calls setOpen.
        e.stopPropagation();
        ctx.setOpen(!ctx.open);
        onClick?.(e);
      }}
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
        "absolute right-0 z-50 mt-2 min-w-[12rem] rounded-md border-2 border-border bg-popover p-2 text-sm shadow-md shadow-black/20",
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
