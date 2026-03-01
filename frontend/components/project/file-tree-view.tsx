"use client";

import { useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  ChevronRight,
  ChevronDown,
  Folder,
  FolderOpen,
  File,
  Search,
  List,
  GitBranch,
} from "lucide-react";
import {
  buildFileTree,
  formatFileSize,
  type FileEntry,
  type FileTreeNode,
} from "@/lib/file-tree";

/* ------------------------------------------------------------------ */
/*  Public component                                                  */
/* ------------------------------------------------------------------ */

export function FileTreeView({ files }: { files: FileEntry[] }) {
  const [search, setSearch] = useState("");
  const [viewMode, setViewMode] = useState<"tree" | "list">("tree");

  const filteredFiles = useMemo(() => {
    if (!search.trim()) return files;
    const q = search.toLowerCase();
    return files.filter((f) => f.path.toLowerCase().includes(q));
  }, [files, search]);

  const tree = useMemo(() => buildFileTree(filteredFiles), [filteredFiles]);

  const totalSize = useMemo(
    () => files.reduce((sum, f) => sum + (f.size_bytes ?? 0), 0),
    [files]
  );

  if (files.length === 0) {
    return (
      <div className="text-sm text-gray-500 text-center py-8">
        No files available.
      </div>
    );
  }

  const isSearching = Boolean(search.trim());

  return (
    <div className="space-y-3">
      {/* Search */}
      <div className="relative">
        <Search
          className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          size={16}
        />
        <Input
          placeholder="Filter files…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9 h-9 text-sm border-gray-300"
        />
      </div>

      {/* Summary + View Toggle */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-500">
          {filteredFiles.length} file{filteredFiles.length !== 1 ? "s" : ""}
          {isSearching && filteredFiles.length !== files.length
            ? ` (of ${files.length})`
            : ""}
          , {formatFileSize(totalSize)} total
        </p>
        <div className="flex items-center gap-1 border border-gray-200 rounded-md p-0.5">
          <button
            type="button"
            onClick={() => setViewMode("tree")}
            aria-label="Tree view"
            className={`p-1 rounded ${viewMode === "tree" ? "bg-gray-200 text-gray-900" : "text-gray-400 hover:text-gray-600"}`}
          >
            <GitBranch size={14} />
          </button>
          <button
            type="button"
            onClick={() => setViewMode("list")}
            aria-label="List view"
            className={`p-1 rounded ${viewMode === "list" ? "bg-gray-200 text-gray-900" : "text-gray-400 hover:text-gray-600"}`}
          >
            <List size={14} />
          </button>
        </div>
      </div>

      {/* Tree / List */}
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <div key={`${viewMode}-${search.trim()}`} className="max-h-[480px] overflow-y-auto p-2">
          {filteredFiles.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-4">
              No matching files.
            </p>
          ) : viewMode === "list" ? (
            filteredFiles.map((f) => (
              <div
                key={f.path}
                className="flex items-center gap-1.5 px-2 py-1 text-sm"
              >
                <File size={14} className="text-gray-400 shrink-0" />
                <span className="text-gray-700 truncate">{f.path}</span>
                {f.mime_type && (
                  <span className="ml-1 px-1.5 py-0.5 rounded bg-gray-100 text-[10px] text-gray-500 shrink-0">
                    {f.mime_type}
                  </span>
                )}
                <span className="ml-auto text-xs text-gray-400 shrink-0">
                  {formatFileSize(f.size_bytes ?? 0)}
                </span>
              </div>
            ))
          ) : (
            tree.children.map((child) => (
              <TreeNode
                key={child.path}
                node={child}
                depth={0}
                defaultOpen
                expandAll={isSearching}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Recursive tree node                                               */
/* ------------------------------------------------------------------ */

function TreeNode({
  node,
  depth,
  defaultOpen = false,
  expandAll = false,
}: {
  node: FileTreeNode;
  depth: number;
  defaultOpen?: boolean;
  expandAll?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen || expandAll);

  if (node.isDirectory) {
    return (
      <div>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex items-center gap-1.5 w-full text-left px-2 py-1 rounded hover:bg-gray-50 text-sm"
          style={{ paddingLeft: `${depth * 16 + 8}px` }}
        >
          {open ? (
            <ChevronDown size={14} className="text-gray-400 shrink-0" />
          ) : (
            <ChevronRight size={14} className="text-gray-400 shrink-0" />
          )}
          {open ? (
            <FolderOpen size={14} className="text-amber-500 shrink-0" />
          ) : (
            <Folder size={14} className="text-amber-500 shrink-0" />
          )}
          <span className="font-medium text-gray-900 truncate">
            {node.name}
          </span>
          <span className="ml-auto flex items-center gap-2 shrink-0">
            <span className="text-xs text-gray-400">
              {node.fileCount} file{node.fileCount !== 1 ? "s" : ""}
            </span>
            <span className="text-xs text-gray-400">
              {formatFileSize(node.size_bytes)}
            </span>
          </span>
        </button>
        {open && (
          <div>
            {node.children.map((child) => (
              <TreeNode
                key={child.path}
                node={child}
                depth={depth + 1}
                expandAll={expandAll}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  // File leaf
  return (
    <div
      className="flex items-center gap-1.5 px-2 py-1 text-sm"
      style={{ paddingLeft: `${depth * 16 + 8 + 18}px` }}
    >
      <File size={14} className="text-gray-400 shrink-0" />
      <span className="text-gray-700 truncate">{node.name}</span>
      {node.file?.mime_type && (
        <span className="ml-1 px-1.5 py-0.5 rounded bg-gray-100 text-[10px] text-gray-500 shrink-0">
          {node.file.mime_type}
        </span>
      )}
      <span className="ml-auto text-xs text-gray-400 shrink-0">
        {formatFileSize(node.size_bytes)}
      </span>
    </div>
  );
}
