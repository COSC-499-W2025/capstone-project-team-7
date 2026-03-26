import React, { createContext, useContext, useMemo, useState } from "react";
import { cn } from "@/lib/utils";

type TabsValue = string;

interface TabsContextValue {
  value: TabsValue;
  setValue: (next: TabsValue) => void;
}

const TabsContext = createContext<TabsContextValue | null>(null);

interface TabsProps extends React.HTMLAttributes<HTMLDivElement> {
  defaultValue: TabsValue;
  onValueChange?: (value: TabsValue) => void;
}

export function Tabs({ defaultValue, onValueChange, className, children, ...props }: TabsProps) {
  const [value, setValue] = useState<TabsValue>(defaultValue);

  const ctx = useMemo<TabsContextValue>(
    () => ({
      value,
      setValue: (next) => {
        setValue(next);
        onValueChange?.(next);
      }
    }),
    [value, onValueChange]
  );

  return (
    <TabsContext.Provider value={ctx}>
      <div className={cn("w-full space-y-2", className)} {...props}>
        {children}
      </div>
    </TabsContext.Provider>
  );
}

export function TabsList({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "inline-flex h-auto w-fit max-w-full items-center gap-1 rounded-[18px] border border-border/70 bg-background/75 p-1.5 text-muted-foreground backdrop-blur-sm",
        className
      )}
      {...props}
    />
  );
}

interface TabsTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: TabsValue;
}

export function TabsTrigger({ className, value, ...props }: TabsTriggerProps) {
  const ctx = useTabsContext();
  const isActive = ctx.value === value;

  return (
    <button
      type="button"
      className={cn(
        "inline-flex h-10 shrink-0 items-center justify-center whitespace-nowrap rounded-[14px] border px-4 text-sm font-medium transition-[background-color,color,border-color,box-shadow] duration-200 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
        "ring-offset-background",
        isActive
          ? "border-border bg-card text-foreground shadow-[0_6px_14px_rgba(15,23,42,0.05)]"
          : "border-transparent bg-transparent text-muted-foreground hover:bg-card/70 hover:text-foreground",
        className
      )}
      onClick={() => ctx.setValue(value)}
      aria-pressed={isActive}
      {...props}
    />
  );
}

interface TabsContentProps extends React.HTMLAttributes<HTMLDivElement> {
  value: TabsValue;
}

export function TabsContent({ className, value, ...props }: TabsContentProps) {
  const ctx = useTabsContext();
  if (ctx.value !== value) return null;
  return (
    <div
      role="tabpanel"
      className={cn("mt-2 rounded-[18px] border border-border/80 bg-card/95 p-5 text-sm shadow-[0_16px_34px_rgba(15,23,42,0.05)]", className)}
      {...props}
    />
  );
}

function useTabsContext(): TabsContextValue {
  const ctx = useContext(TabsContext);
  if (!ctx) {
    throw new Error("Tabs components must be used within <Tabs>");
  }
  return ctx;
}
