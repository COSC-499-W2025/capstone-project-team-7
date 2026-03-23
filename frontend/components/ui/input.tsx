import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(function Input({ className, type = "text", ...props }, ref) {
  return (
    <input
      ref={ref}
      type={type}
      className={cn(
        "flex h-11 w-full rounded-[14px] border border-input bg-background px-3.5 py-2.5 text-sm text-foreground shadow-sm transition-[border-color,box-shadow,background-color]",
        "file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-2 focus-visible:border-primary/40",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "ring-offset-background",
        className
      )}
      {...props}
    />
  );
});
