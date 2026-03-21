import * as React from "react";
import { cn } from "@/lib/utils";

type ButtonVariant = "default" | "secondary" | "outline" | "ghost" | "destructive";
type ButtonSize = "default" | "sm" | "lg";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantClasses: Record<ButtonVariant, string> = {
  default:
    "border border-primary/80 bg-[linear-gradient(180deg,hsl(var(--primary)),hsl(215_84%_52%))] text-primary-foreground shadow-[0_16px_28px_hsl(var(--primary)/0.22)] hover:border-primary hover:shadow-[0_18px_32px_hsl(var(--primary)/0.3)]",
  secondary:
    "border border-border/80 bg-[linear-gradient(180deg,hsl(var(--secondary)),hsl(var(--card)))] text-secondary-foreground shadow-[0_10px_20px_rgba(15,23,42,0.08)] hover:border-border hover:bg-secondary/85",
  outline:
    "border border-border bg-card/88 text-foreground shadow-[0_10px_22px_rgba(15,23,42,0.05)] hover:border-primary/35 hover:bg-accent/70 hover:text-accent-foreground",
  ghost:
    "border border-transparent bg-transparent text-muted-foreground hover:bg-accent/75 hover:text-foreground",
  destructive:
    "border border-destructive/80 bg-[linear-gradient(180deg,hsl(var(--destructive)),hsl(0_74%_52%))] text-destructive-foreground shadow-[0_16px_26px_hsl(var(--destructive)/0.18)] hover:border-destructive hover:shadow-[0_18px_30px_hsl(var(--destructive)/0.24)]"
};

const sizeClasses: Record<ButtonSize, string> = {
  default: "h-10 px-4 py-2",
  sm: "h-9 px-3.5 text-sm",
  lg: "h-11 px-5 text-[15px]"
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant = "default", size = "default", type = "button", ...props },
  ref
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(
        "inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-[14px] text-sm font-semibold leading-none tracking-[-0.01em] transition-[transform,box-shadow,border-color,background-color,color] duration-200 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:translate-y-0.5 disabled:translate-y-0 [&_svg]:shrink-0",
        "hover:-translate-y-px",
        "ring-offset-background",
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      {...props}
    />
  );
});
