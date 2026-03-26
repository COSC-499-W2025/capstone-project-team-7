import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  onClear?: () => void;
  onKeyDown?: React.KeyboardEventHandler<HTMLInputElement>;
  className?: string;
}

export function SearchInput({
  value,
  onChange,
  placeholder = "Search…",
  onClear,
  onKeyDown,
  className,
}: SearchInputProps) {
  const showClear = onClear && value.length > 0;

  return (
    <div className={cn("relative", className)}>
      <Search
        className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground"
        size={16}
      />
      <Input
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        className={`h-11 rounded-[16px] pl-11 text-sm ${showClear ? "pr-10" : ""}`}
      />
      {showClear && (
        <button
          type="button"
          onClick={onClear}
          className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
          aria-label="Clear search"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}
