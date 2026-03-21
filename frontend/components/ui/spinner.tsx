import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

type SpinnerSize = "sm" | "md" | "lg" | "xl" | number;

interface SpinnerProps {
  className?: string;
  size?: SpinnerSize;
}

const sizeClasses: Record<Exclude<SpinnerSize, number>, string> = {
  sm: "h-3.5 w-3.5",
  md: "h-4 w-4",
  lg: "h-5 w-5",
  xl: "h-8 w-8",
};

export function Spinner({ className, size = "md" }: SpinnerProps) {
  if (typeof size === "number") {
    return (
      <Loader2
        aria-hidden="true"
        className={cn("animate-spin text-current", className)}
        style={{ height: size, width: size }}
      />
    );
  }

  return (
    <Loader2
      aria-hidden="true"
      className={cn("animate-spin text-current", sizeClasses[size], className)}
    />
  );
}
