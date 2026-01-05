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
      className={cn("inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground", className)}
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
        "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
        "ring-offset-background",
        isActive ? "bg-background text-foreground shadow-sm" : "opacity-70 hover:text-foreground"
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
      className={cn("mt-2 rounded-md border border-border bg-card p-4 text-sm shadow-sm", className)}
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
