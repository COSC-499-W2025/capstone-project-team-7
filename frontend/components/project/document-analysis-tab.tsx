"use client";

import React, { useMemo, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { SearchInput } from "@/components/ui/search-input";
import {
  FileText,
  FileType,
  FileIcon,
  BookOpen,
} from "lucide-react";
import type { DocumentSummary, DocumentAnalysisStats } from "@/types/document";
import {
  projectPageSelectors,
  useProjectPageStore,
} from "@/lib/stores/project-page-store";

// Helper function to extract file type from path
function getFileType(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase() || 'unknown';
  return ext;
}

// Helper function to extract filename from path
function getFileName(path: string): string {
  return path.split(/[\\/]/).pop() || path;
}

type DocumentAnalysisPayload = unknown;

function getFileIcon(fileType: string) {
  switch (fileType) {
    case "pdf":
      return <FileText className="h-5 w-5 text-red-500" />;
    case "docx":
    case "doc":
      return <FileType className="h-5 w-5 text-blue-500" />;
    case "md":
    case "markdown":
      return <BookOpen className="h-5 w-5 text-purple-500" />;
    case "txt":
      return <FileIcon className="h-5 w-5 text-muted-foreground" />;
    default:
      return <FileIcon className="h-5 w-5 text-muted-foreground" />;
  }
}

// Calculate statistics from documents
function calculateStats(documents: DocumentSummary[]): DocumentAnalysisStats {
  const stats: DocumentAnalysisStats = {
    total_documents: documents.length,
    total_words: 0,
    documents_with_keywords: 0,
    documents_with_headings: 0,
    md_count: 0,
    txt_count: 0,
    docx_count: 0,
    other_count: 0,
  };

  documents.forEach(doc => {
    stats.total_words += doc.word_count || 0;
    if (doc.keywords.length > 0) stats.documents_with_keywords++;
    if (doc.headings.length > 0) stats.documents_with_headings++;

    const fileType = getFileType(doc.path);
    if (fileType === 'md' || fileType === 'markdown') {
      stats.md_count++;
    } else if (fileType === 'txt') {
      stats.txt_count++;
    } else if (fileType === 'docx' || fileType === 'doc') {
      stats.docx_count++;
    } else {
      stats.other_count++;
    }
  });

  return stats;
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((entry) => (typeof entry === "string" ? entry.trim() : null))
    .filter((entry): entry is string => Boolean(entry));
}

function toKeywordArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((entry) => {
      if (typeof entry === "string") return entry.trim();
      if (Array.isArray(entry) && typeof entry[0] === "string") {
        return entry[0].trim();
      }
      if (entry && typeof entry === "object") {
        const keyword =
          (entry as { word?: string; keyword?: string; text?: string }).word ||
          (entry as { word?: string; keyword?: string; text?: string }).keyword ||
          (entry as { word?: string; keyword?: string; text?: string }).text;
        return keyword ? keyword.trim() : null;
      }
      return null;
    })
    .filter((entry): entry is string => Boolean(entry));
}

function normalizeDocumentItem(item: unknown): DocumentSummary | null {
  if (!item || typeof item !== "object") return null;
  const record = item as Record<string, unknown>;
  if (record.success === false) return null;
  const metadata =
    record.metadata && typeof record.metadata === "object" && !Array.isArray(record.metadata)
      ? (record.metadata as Record<string, unknown>)
      : {};

  const path =
    record.path ||
    record.file_name ||
    record.fileName ||
    record.name ||
    "Unknown";

  const word_count =
    record.word_count ??
    metadata.word_count ??
    metadata.wordCount;

  const summary_text =
    record.summary_text ??
    record.summary ??
    record.summaryText ??
    record.text_summary ??
    null;

  const headings =
    toStringArray(record.headings).length > 0
      ? toStringArray(record.headings)
      : toStringArray(metadata.headings);

  const keywords =
    toKeywordArray(record.keywords).length > 0
      ? toKeywordArray(record.keywords)
      : toKeywordArray(record.key_topics).length > 0
        ? toKeywordArray(record.key_topics)
        : [];

  return {
    path: String(path),
    word_count: typeof word_count === "number" ? word_count : undefined,
    summary_text: typeof summary_text === "string" ? summary_text : undefined,
    keywords,
    headings,
  };
}

function normalizeDocumentAnalysis(payload: DocumentAnalysisPayload): DocumentSummary[] {
  if (!payload) return [];
  if (Array.isArray(payload)) {
    return payload
      .map((item) => normalizeDocumentItem(item))
      .filter((item): item is DocumentSummary => Boolean(item));
  }

  if (typeof payload === "object") {
    const record = payload as Record<string, unknown>;
    const documents = record.documents;
    const listItems = record.items;
    const items =
      Array.isArray(documents)
        ? documents
        : Array.isArray(listItems)
          ? listItems
          : [];
    return items
      .map((item: unknown) => normalizeDocumentItem(item))
      .filter((item: DocumentSummary | null): item is DocumentSummary => Boolean(item));
  }

  return [];
}

type DocumentAnalysisTabProps = {
  documentAnalysis?: unknown;
  isLoading?: boolean;
  errorMessage?: string | null;
  useStore?: boolean;
};

export function DocumentAnalysisTab({
  documentAnalysis,
  isLoading,
  errorMessage,
  useStore = false,
}: DocumentAnalysisTabProps) {
  const scanData = useProjectPageStore(projectPageSelectors.scanData);
  const storeLoading = useProjectPageStore(projectPageSelectors.projectLoading);
  const storeError = useProjectPageStore(projectPageSelectors.projectError);
  const useStoreFallback = useStore;
  const resolvedDocumentAnalysis =
    documentAnalysis ?? (useStoreFallback ? scanData.document_analysis : undefined);
  const resolvedIsLoading = isLoading ?? (useStoreFallback ? storeLoading : false);
  const resolvedErrorMessage = errorMessage ?? (useStoreFallback ? storeError : null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string>("all");
  const documents = useMemo(
    () => normalizeDocumentAnalysis(resolvedDocumentAnalysis),
    [resolvedDocumentAnalysis]
  );
  const stats = calculateStats(documents);

  const filteredDocuments = documents.filter((doc) => {
    const matchesSearch =
      searchQuery === "" ||
      doc.path.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.summary_text?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.keywords.some((kw) => kw.toLowerCase().includes(searchQuery.toLowerCase())) ||
      doc.headings.some((h) => h.toLowerCase().includes(searchQuery.toLowerCase()));

    const docType = getFileType(doc.path);
    const matchesType = selectedType === "all" || docType === selectedType;

    return matchesSearch && matchesType;
  });
  const emptyMessage =
    documents.length === 0 && searchQuery === "" && selectedType === "all"
      ? "No document analysis available for this project yet"
      : "No documents found matching your criteria";

  return (
    <div className="space-y-5">
      {/* Statistics Overview */}
      <Card>
        <CardHeader className="border-b border-border/70 p-5 pb-4">
          <CardTitle className="text-lg font-semibold text-foreground">Document Statistics</CardTitle>
        </CardHeader>
        <CardContent className="p-5 pt-4">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <div className="stat-block p-4 text-center">
              <p className="text-2xl font-bold text-foreground">{stats.total_documents}</p>
              <p className="mt-1 text-xs text-muted-foreground">Total Documents</p>
            </div>
            <div className="stat-block p-4 text-center">
              <p className="text-2xl font-bold text-foreground">
                {stats.total_words.toLocaleString()}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">Total Words</p>
            </div>
            <div className="stat-block p-4 text-center">
              <p className="text-2xl font-bold text-foreground">{stats.documents_with_keywords}</p>
              <p className="mt-1 text-xs text-muted-foreground">Docs with key terms</p>
              <p className="mt-0.5 text-[11px] text-muted-foreground">
                At least one extracted keyword or topic
              </p>
            </div>
            <div className="stat-block p-4 text-center">
              <p className="text-2xl font-bold text-foreground">{stats.documents_with_headings}</p>
              <p className="mt-1 text-xs text-muted-foreground">With Headings</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Document Type Breakdown */}
      <Card>
        <CardHeader className="border-b border-border/70 p-5 pb-4">
          <CardTitle className="text-lg font-semibold text-foreground">Document Types</CardTitle>
        </CardHeader>
        <CardContent className="p-5 pt-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="flex items-center gap-3 rounded-[16px] border border-purple-200 bg-purple-50/80 p-3.5">
              <BookOpen className="h-6 w-6 text-purple-500" />
              <div>
                <p className="text-lg font-bold text-foreground">{stats.md_count}</p>
                <p className="text-xs text-muted-foreground">Markdown</p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-[16px] border border-border bg-muted/60 p-3.5">
              <FileIcon className="h-6 w-6 text-muted-foreground" />
              <div>
                <p className="text-lg font-bold text-foreground">{stats.txt_count}</p>
                <p className="text-xs text-muted-foreground">Text Files</p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-[16px] border border-blue-200 bg-blue-50/80 p-3.5">
              <FileType className="h-6 w-6 text-blue-500" />
              <div>
                <p className="text-lg font-bold text-foreground">{stats.docx_count}</p>
                <p className="text-xs text-muted-foreground">Word Docs</p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-[16px] border border-border bg-muted/60 p-3.5">
              <FileIcon className="h-6 w-6 text-muted-foreground" />
              <div>
                <p className="text-lg font-bold text-foreground">{stats.other_count}</p>
                <p className="text-xs text-muted-foreground">Other</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Search and Filter */}
      <Card>
        <CardContent className="p-5">
          <div className="flex flex-col sm:flex-row gap-3">
            <SearchInput
              value={searchQuery}
              onChange={setSearchQuery}
              placeholder="Search documents by name, title, or topic..."
              className="flex-1"
            />
            <div className="flex gap-2">
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="h-10 rounded-[14px] border border-border bg-background px-3.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/40"
              >
                <option value="all">All Types</option>
                <option value="md">Markdown</option>
                <option value="txt">Text</option>
                <option value="docx">Word</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Documents List */}
      <Card>
        <CardHeader className="border-b border-border/70 p-5 pb-4">
          <CardTitle className="text-lg font-semibold text-foreground">
            Documents ({filteredDocuments.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-5 pt-4">
          {resolvedIsLoading && (
            <div className="text-center py-8 text-muted-foreground">
              Loading document analysis…
            </div>
          )}
          {resolvedErrorMessage && !resolvedIsLoading && (
            <div className="text-center py-8 text-red-600">
              {resolvedErrorMessage}
            </div>
          )}
          <div className="space-y-4">
            {!resolvedIsLoading && !resolvedErrorMessage && filteredDocuments.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                {emptyMessage}
              </div>
            ) : (!resolvedIsLoading && !resolvedErrorMessage ? (
              filteredDocuments.map((doc, index) => (
                <div
                  key={index}
                  className="rounded-[16px] border border-border bg-background/70 p-4 transition-colors hover:border-border/90"
                >
                  <div className="flex items-start gap-4">
                    <div className="mt-1">{getFileIcon(getFileType(doc.path))}</div>
                    <div className="flex-1 min-w-0">
                      {/* File Header */}
                      <div className="flex items-start justify-between gap-4 mb-3">
                        <div className="flex-1 min-w-0">
                          <h3 className="mb-1 truncate font-semibold text-foreground">
                            {getFileName(doc.path)}
                          </h3>
                          <p className="truncate font-mono text-xs text-muted-foreground">{doc.path}</p>
                        </div>
                        <span className="rounded-full border border-border bg-muted px-2.5 py-1 text-xs uppercase text-muted-foreground">
                          {getFileType(doc.path)}
                        </span>
                      </div>

                      {/* Summary */}
                      {doc.summary_text && (
                        <p className="mb-3 text-sm text-muted-foreground">{doc.summary_text}</p>
                      )}

                      {/* Metadata */}
                      {doc.word_count && (
                        <div className="mb-3 flex items-center gap-2 text-xs text-muted-foreground">
                          <FileType className="h-3 w-3" />
                          <span>{doc.word_count.toLocaleString()} words</span>
                        </div>
                      )}

                      {/* Headings */}
                      {doc.headings.length > 0 && (
                        <div className="mb-3">
                          <p className="mb-1.5 text-xs font-semibold text-foreground">
                            Headings ({doc.headings.length}):
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {doc.headings.slice(0, 5).map((heading, idx) => (
                              <span
                                key={idx}
                                className="rounded-md border border-blue-200 bg-blue-50 px-2 py-1 text-xs text-blue-700"
                              >
                                {heading}
                              </span>
                            ))}
                            {doc.headings.length > 5 && (
                              <span className="rounded-md border border-border bg-muted px-2 py-1 text-xs text-muted-foreground">
                                +{doc.headings.length - 5} more
                              </span>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Keywords */}
                      {doc.keywords.length > 0 && (
                        <div>
                          <p className="mb-1.5 text-xs font-semibold text-foreground">
                            Keywords ({doc.keywords.length}):
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {doc.keywords.slice(0, 8).map((keyword, idx) => (
                              <span
                                key={idx}
                                className="rounded-md border border-green-200 bg-green-50 px-2 py-1 text-xs text-green-700"
                              >
                                {keyword}
                              </span>
                            ))}
                            {doc.keywords.length > 8 && (
                              <span className="rounded-md border border-border bg-muted px-2 py-1 text-xs text-muted-foreground">
                                +{doc.keywords.length - 8} more
                              </span>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))
            ) : null)}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
