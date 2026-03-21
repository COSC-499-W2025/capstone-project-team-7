import * as React from "react";
import { cn } from "@/lib/utils";

export interface SectionProps extends React.HTMLAttributes<HTMLElement> {
  as?: React.ElementType;
}

export const Section = React.forwardRef<HTMLElement, SectionProps>(function Section(
  { as: Component = "section", className, ...props },
  ref,
) {
  return (
    <Component
      ref={ref}
      className={cn(
        "overflow-hidden rounded-[22px] border border-border/70 bg-[linear-gradient(180deg,hsl(var(--card)),hsl(var(--background))/0.9)] shadow-[0_16px_34px_rgba(15,23,42,0.06)]",
        className,
      )}
      {...props}
    />
  );
});

export const SectionHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  function SectionHeader({ className, ...props }, ref) {
    return (
      <div
        ref={ref}
        className={cn(
          "flex flex-col gap-4 px-6 py-5 sm:px-7 sm:py-6 md:flex-row md:items-start md:justify-between",
          className,
        )}
        {...props}
      />
    );
  },
);

export const SectionHeading = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  function SectionHeading({ className, ...props }, ref) {
    return <div ref={ref} className={cn("min-w-0 space-y-1.5", className)} {...props} />;
  },
);

export const SectionTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(
  function SectionTitle({ className, ...props }, ref) {
    return (
      <h2
        ref={ref}
        className={cn("text-lg font-semibold tracking-[-0.02em] text-foreground", className)}
        {...props}
      />
    );
  },
);

export const SectionDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(function SectionDescription({ className, ...props }, ref) {
  return (
    <p
      ref={ref}
      className={cn("text-sm leading-6 text-muted-foreground", className)}
      {...props}
    />
  );
});

export const SectionActions = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  function SectionActions({ className, ...props }, ref) {
    return (
      <div
        ref={ref}
        className={cn("flex flex-wrap items-center gap-3 md:justify-end", className)}
        {...props}
      />
    );
  },
);

export const SectionBody = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  function SectionBody({ className, ...props }, ref) {
    return <div ref={ref} className={cn("px-6 pb-6 sm:px-7 sm:pb-7", className)} {...props} />;
  },
);

export const SectionInset = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  function SectionInset({ className, ...props }, ref) {
    return (
      <div
        ref={ref}
        className={cn(
          "rounded-[18px] bg-[linear-gradient(180deg,hsl(var(--muted))/0.72,hsl(var(--card))/0.92)] p-4",
          className,
        )}
        {...props}
      />
    );
  },
);
