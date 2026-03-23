import * as React from "react";
import { cn } from "@/lib/utils";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { className, ...props },
  ref
) {
  return (
    <textarea
      ref={ref}
      className={cn(
        "flex min-h-[120px] w-full rounded-[16px] border border-input bg-background px-3.5 py-3 text-sm text-foreground shadow-sm transition-[border-color,box-shadow,background-color]",
        "placeholder:text-muted-foreground",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-2 focus-visible:border-primary/40",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "ring-offset-background",
        className
      )}
      {...props}
    />
  );
});
