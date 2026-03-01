/** Types and utilities for converting a flat file list into a hierarchical tree. */

export interface FileEntry {
  path: string;
  size_bytes: number;
  mime_type: string;
  created_at?: string | null;
  modified_at?: string | null;
  file_hash?: string | null;
}

export interface FileTreeNode {
  name: string;
  path: string;
  isDirectory: boolean;
  children: FileTreeNode[];
  file?: FileEntry;
  size_bytes: number;
  fileCount: number;
}

/**
 * Build a hierarchical file tree from a flat array of file entries.
 * Directories are sorted before files; both groups are sorted alphabetically.
 */
export function buildFileTree(files: FileEntry[]): FileTreeNode {
  const root: FileTreeNode = {
    name: "",
    path: "",
    isDirectory: true,
    children: [],
    size_bytes: 0,
    fileCount: 0,
  };

  for (const file of files) {
    const parts = file.path.split("/").filter(Boolean);
    let current = root;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isLast = i === parts.length - 1;
      const partPath = parts.slice(0, i + 1).join("/");

      if (isLast) {
        // Leaf file node
        current.children.push({
          name: part,
          path: partPath,
          isDirectory: false,
          children: [],
          file,
          size_bytes: file.size_bytes,
          fileCount: 1,
        });
      } else {
        // Intermediate directory — find or create
        let dir = current.children.find(
          (c) => c.isDirectory && c.name === part
        );
        if (!dir) {
          dir = {
            name: part,
            path: partPath,
            isDirectory: true,
            children: [],
            size_bytes: 0,
            fileCount: 0,
          };
          current.children.push(dir);
        }
        current = dir;
      }
    }
  }

  // Aggregate sizes & counts bottom-up, then sort
  aggregate(root);
  sortTree(root);

  return root;
}

function aggregate(node: FileTreeNode): void {
  if (!node.isDirectory) return;

  let totalSize = 0;
  let totalFiles = 0;

  for (const child of node.children) {
    aggregate(child);
    totalSize += child.size_bytes;
    totalFiles += child.fileCount;
  }

  node.size_bytes = totalSize;
  node.fileCount = totalFiles;
}

function sortTree(node: FileTreeNode): void {
  if (!node.isDirectory) return;

  node.children.sort((a, b) => {
    // Directories first
    if (a.isDirectory !== b.isDirectory) return a.isDirectory ? -1 : 1;
    // Then alphabetical (case-insensitive)
    return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
  });

  for (const child of node.children) {
    sortTree(child);
  }
}

/** Format byte count into a human-readable string. */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1
  );
  const value = bytes / Math.pow(1024, i);
  return `${i === 0 ? value : value.toFixed(1)} ${units[i]}`;
}
