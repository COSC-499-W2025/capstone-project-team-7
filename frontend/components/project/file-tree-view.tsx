"use client";

import { useMemo, useState } from "react";
import { SearchInput } from "@/components/ui/search-input";
import {
  ChevronRight,
  ChevronDown,
  Folder,
  FolderOpen,
  File,
  List,
  GitBranch,
} from "lucide-react";
import {
  buildFileTree,
  formatFileSize,
  type FileEntry,
  type FileTreeNode,
} from "@/lib/file-tree";
import {
  projectPageSelectors,
  useProjectPageStore,
} from "@/lib/stores/project-page-store";

/* ------------------------------------------------------------------ */
/*  Public component                                                  */
/* ------------------------------------------------------------------ */

export function FileTreeView({
  files,
  useStore = false,
}: {
  files?: FileEntry[];
  useStore?: boolean;
}) {
  const scanData = useProjectPageStore(projectPageSelectors.scanData);
  const storeFiles = useMemo<FileEntry[]>(() => {
    if (!Array.isArray(scanData.files)) return [];

    return scanData.files
      .map((entry) => {
        if (typeof entry !== "object" || entry === null) {
          return null;
        }

        const file = entry as Record<string, unknown>;
        const path =
          typeof file.path === "string"
            ? file.path
            : typeof file.file_path === "string"
              ? file.file_path
              : "";

        if (path.length === 0) return null;

        return {
          path,
          size_bytes:
            typeof file.size_bytes === "number" && Number.isFinite(file.size_bytes)
              ? file.size_bytes
              : 0,
          mime_type:
            typeof file.mime_type === "string" && file.mime_type.length > 0
              ? file.mime_type
              : "application/octet-stream",
          created_at:
            typeof file.created_at === "string" || file.created_at === null
              ? file.created_at
              : undefined,
          modified_at:
            typeof file.modified_at === "string" || file.modified_at === null
              ? file.modified_at
              : undefined,
          file_hash:
            typeof file.file_hash === "string" || file.file_hash === null
              ? file.file_hash
              : undefined,
        } as FileEntry;
      })
      .filter((entry): entry is FileEntry => entry !== null);
  }, [scanData.files]);

  const sourceFiles = files ?? (useStore ? storeFiles : []);
  const [search, setSearch] = useState("");
  const [viewMode, setViewMode] = useState<"tree" | "list">("tree");

  const filteredFiles = useMemo(() => {
    if (!search.trim()) return sourceFiles;
    const q = search.toLowerCase();
    return sourceFiles.filter((f) => f.path.toLowerCase().includes(q));
  }, [sourceFiles, search]);

  const tree = useMemo(() => buildFileTree(filteredFiles), [filteredFiles]);

  const totalSize = useMemo(
    () => sourceFiles.reduce((sum, f) => sum + (f.size_bytes ?? 0), 0),
    [sourceFiles]
  );

  if (sourceFiles.length === 0) {
    return (
      <div className="text-sm text-muted-foreground text-center py-8">
        No files available.
      </div>
    );
  }

  const isSearching = Boolean(search.trim());

  return (
    <div className="space-y-3">
      {/* Search */}
      <SearchInput
        value={search}
        onChange={setSearch}
        placeholder="Filter files…"
      />

      {/* Summary + View Toggle */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          {filteredFiles.length} file{filteredFiles.length !== 1 ? "s" : ""}
          {isSearching && filteredFiles.length !== sourceFiles.length
            ? ` (of ${sourceFiles.length})`
            : ""}
          , {formatFileSize(totalSize)} total
        </p>
        <div className="flex items-center gap-1 border border-border rounded-md p-0.5">
          <button
            type="button"
            onClick={() => setViewMode("tree")}
            aria-label="Tree view"
            className={`p-1 rounded ${viewMode === "tree" ? "bg-muted/60 text-foreground" : "text-muted-foreground hover:text-foreground"}`}
          >
            <GitBranch size={14} />
          </button>
          <button
            type="button"
            onClick={() => setViewMode("list")}
            aria-label="List view"
            className={`p-1 rounded ${viewMode === "list" ? "bg-muted/60 text-foreground" : "text-muted-foreground hover:text-foreground"}`}
          >
            <List size={14} />
          </button>
        </div>
      </div>

      {/* Tree / List */}
      <div className="border border-border rounded-lg overflow-hidden">
        <div key={`${viewMode}-${search.trim()}`} className="max-h-[480px] overflow-y-auto p-2">
          {filteredFiles.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No matching files.
            </p>
          ) : viewMode === "list" ? (
            filteredFiles.map((f) => (
              <div
                key={f.path}
                className="flex items-center gap-1.5 px-2 py-1 text-sm"
              >
                <File size={14} className="text-muted-foreground shrink-0" />
                <span className="text-foreground truncate">{f.path}</span>
                {f.mime_type && (
                  <span className="ml-1 px-1.5 py-0.5 rounded bg-muted/30 text-[10px] text-muted-foreground shrink-0">
                    {f.mime_type}
                  </span>
                )}
                <span className="ml-auto text-xs text-muted-foreground shrink-0">
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
          className="flex items-center gap-1.5 w-full text-left px-2 py-1 rounded hover:bg-muted/50 text-sm"
          style={{ paddingLeft: `${depth * 16 + 8}px` }}
        >
          {open ? (
            <ChevronDown size={14} className="text-muted-foreground shrink-0" />
          ) : (
            <ChevronRight size={14} className="text-muted-foreground shrink-0" />
          )}
          {open ? (
            <FolderOpen size={14} className="text-amber-500 shrink-0" />
          ) : (
            <Folder size={14} className="text-amber-500 shrink-0" />
          )}
          <span className="font-medium text-foreground truncate">
            {node.name}
          </span>
          <span className="ml-auto flex items-center gap-2 shrink-0">
            <span className="text-xs text-muted-foreground">
              {node.fileCount} file{node.fileCount !== 1 ? "s" : ""}
            </span>
            <span className="text-xs text-muted-foreground">
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
      <File size={14} className="text-muted-foreground shrink-0" />
      <span className="text-foreground truncate">{node.name}</span>
      {node.file?.mime_type && (
        <span className="ml-1 px-1.5 py-0.5 rounded bg-muted/30 text-[10px] text-muted-foreground shrink-0">
          {node.file.mime_type}
        </span>
      )}
      <span className="ml-auto text-xs text-muted-foreground shrink-0">
        {formatFileSize(node.size_bytes)}
      </span>
    </div>
  );
}
