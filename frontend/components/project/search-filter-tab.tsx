"use client";

import { useEffect, useRef, useMemo, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Search,
  X,
  File,
  AlertCircle,
  RotateCcw,
} from "lucide-react";
import type { FileEntry } from "@/lib/file-tree";
import { formatFileSize } from "@/lib/file-tree";

const PAGE_SIZE = 50;

function getExtension(path: string): string {
  const name = path.split("/").pop() ?? path;
  const dot = name.lastIndexOf(".");
  return dot >= 0 ? name.slice(dot + 1).toLowerCase() : "";
}

function getMimeCategory(mime: string): string {
  if (
    mime.includes("javascript") ||
    mime.includes("typescript") ||
    mime.includes("x-python") ||
    mime.includes("x-sh") ||
    mime.includes("x-c") ||
    mime.includes("x-java")
  )
    return "code";
  if (mime.includes("json")) return "json";
  if (mime.startsWith("text/")) return "text";
  if (mime.startsWith("image/")) return "image";
  if (mime === "application/pdf") return "pdf";
  return "other";
}

export function SearchFilterTab({
  files,
  loading,
  error,
  onRetry,
}: {
  files: FileEntry[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}) {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [langFilter, setLangFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [pathFilter, setPathFilter] = useState("all");
  const [sortBy, setSortBy] = useState<"name" | "size" | "type">("name");
  const [page, setPage] = useState(1);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  function handleQueryChange(value: string) {
    setQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedQuery(value);
      setPage(1);
    }, 250);
  }

  // Derive available extensions from files
  const languages = useMemo(() => {
    const exts = new Set<string>();
    for (const f of files) {
      const ext = getExtension(f.path);
      if (ext) exts.add(ext);
    }
    return Array.from(exts).sort();
  }, [files]);

  // Derive available MIME categories
  const mimeCategories = useMemo(() => {
    const cats = new Set<string>();
    for (const f of files) cats.add(getMimeCategory(f.mime_type));
    return Array.from(cats).sort();
  }, [files]);

  // Derive top-level directories for path filter
  const topDirs = useMemo(() => {
    const dirs = new Set<string>();
    for (const f of files) {
      const parts = f.path.split("/");
      if (parts.length > 1) dirs.add(parts[0]);
    }
    return Array.from(dirs).sort();
  }, [files]);

  // Filtered + sorted files
  const filtered = useMemo(() => {
    let result = files;

    if (debouncedQuery.trim()) {
      const q = debouncedQuery.toLowerCase();
      result = result.filter((f) => f.path.toLowerCase().includes(q));
    }

    if (langFilter !== "all") {
      result = result.filter((f) => getExtension(f.path) === langFilter);
    }

    if (typeFilter !== "all") {
      result = result.filter(
        (f) => getMimeCategory(f.mime_type) === typeFilter
      );
    }

    if (pathFilter !== "all") {
      result = result.filter((f) => f.path.startsWith(pathFilter + "/"));
    }

    const sorted = [...result].sort((a, b) => {
      if (sortBy === "size") return b.size_bytes - a.size_bytes;
      if (sortBy === "type") return a.mime_type.localeCompare(b.mime_type);
      return a.path.localeCompare(b.path);
    });

    return sorted;
  }, [files, debouncedQuery, langFilter, typeFilter, pathFilter, sortBy]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const hasActiveFilters =
    debouncedQuery.trim() ||
    langFilter !== "all" ||
    typeFilter !== "all" ||
    pathFilter !== "all";

  function reset() {
    handleQueryChange("");
    setLangFilter("all");
    setTypeFilter("all");
    setPathFilter("all");
    setSortBy("name");
    setPage(1);
  }

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4">
        <AlertCircle className="text-red-500" size={32} />
        <p className="text-sm text-gray-700">{error}</p>
        <Button variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Search input */}
      <div className="relative">
        <Search
          className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          size={16}
        />
        <Input
          placeholder="Search by filename or path…"
          value={query}
          onChange={(e) => handleQueryChange(e.target.value)}
          className="pl-9 pr-9 h-9 text-sm border-gray-300"
        />
        {query && (
          <button
            type="button"
            onClick={() => handleQueryChange("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            aria-label="Clear search"
          >
            <X size={14} />
          </button>
        )}
      </div>

      {/* Filter controls */}
      <div className="flex flex-wrap gap-2 items-center">
        {languages.length > 0 && (
          <Select
            value={langFilter}
            onValueChange={(v) => {
              setLangFilter(v);
              setPage(1);
            }}
          >
            <SelectTrigger className="h-8 text-xs w-36">
              <SelectValue placeholder="Language" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All languages</SelectItem>
              {languages.map((l) => (
                <SelectItem key={l} value={l}>
                  .{l}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        {mimeCategories.length > 1 && (
          <Select
            value={typeFilter}
            onValueChange={(v) => {
              setTypeFilter(v);
              setPage(1);
            }}
          >
            <SelectTrigger className="h-8 text-xs w-36">
              <SelectValue placeholder="File type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              {mimeCategories.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        {topDirs.length > 0 && (
          <Select
            value={pathFilter}
            onValueChange={(v) => {
              setPathFilter(v);
              setPage(1);
            }}
          >
            <SelectTrigger className="h-8 text-xs w-44">
              <SelectValue placeholder="Directory" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All directories</SelectItem>
              {topDirs.map((d) => (
                <SelectItem key={d} value={d}>
                  {d}/
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        <Select
          value={sortBy}
          onValueChange={(v) => {
            setSortBy(v as "name" | "size" | "type");
            setPage(1);
          }}
        >
          <SelectTrigger className="h-8 text-xs w-32">
            <SelectValue placeholder="Sort by" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="name">Sort: Name</SelectItem>
            <SelectItem value="size">Sort: Size</SelectItem>
            <SelectItem value="type">Sort: Type</SelectItem>
          </SelectContent>
        </Select>

        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={reset}
            className="h-8 text-xs gap-1 text-gray-500 hover:text-gray-900"
          >
            <RotateCcw size={12} />
            Reset
          </Button>
        )}
      </div>

      {/* Result count */}
      <p className="text-xs text-gray-500">
        {loading
          ? "Loading…"
          : `${filtered.length} file${filtered.length !== 1 ? "s" : ""}${
              hasActiveFilters && filtered.length !== files.length
                ? ` (of ${files.length} total)`
                : ""
            }`}
      </p>

      {/* Results */}
      {loading ? (
        <div className="border border-gray-200 rounded-lg">
          <div className="flex items-center justify-center py-16 text-sm text-gray-400">
            Loading files…
          </div>
        </div>
      ) : filtered.length === 0 ? (
        <div className="border border-gray-200 rounded-lg flex flex-col items-center justify-center py-16 gap-3">
          <Search className="text-gray-300" size={32} />
          <p className="text-sm text-gray-500">No files match your search.</p>
          {hasActiveFilters && (
            <Button variant="outline" size="sm" onClick={reset}>
              Clear filters
            </Button>
          )}
        </div>
      ) : (
        <>
          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <div className="max-h-[480px] overflow-y-auto divide-y divide-gray-100">
              {paginated.map((f) => {
                const ext = getExtension(f.path);
                const name = f.path.split("/").pop() ?? f.path;
                const dir = f.path.includes("/")
                  ? f.path.slice(0, f.path.lastIndexOf("/"))
                  : "";
                return (
                  <div
                    key={f.path}
                    className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50"
                  >
                    <File size={14} className="text-gray-400 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {name}
                      </p>
                      {dir && (
                        <p className="text-xs text-gray-400 truncate">{dir}</p>
                      )}
                    </div>
                    {ext && (
                      <Badge
                        variant="outline"
                        className="text-[10px] shrink-0 px-1.5 py-0"
                      >
                        .{ext}
                      </Badge>
                    )}
                    <span className="text-xs text-gray-400 shrink-0">
                      {formatFileSize(f.size_bytes)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-1">
              <p className="text-xs text-gray-500">
                Page {page} of {totalPages} ({filtered.length} files)
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page === 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page === totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
