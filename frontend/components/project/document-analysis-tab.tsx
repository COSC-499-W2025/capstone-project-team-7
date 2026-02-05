"use client";

import React, { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  FileText,
  FileType,
  Search,
  FileIcon,
  BookOpen,
  HardDrive,
} from "lucide-react";
import type { DocumentSummary, DocumentAnalysisStats } from "@/types/document";

// Helper function to extract file type from path
function getFileType(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase() || 'unknown';
  return ext;
}

// Helper function to extract filename from path
function getFileName(path: string): string {
  return path.split('/').pop() || path;
}

// Mock data aligned with backend schema
const mockDocuments: DocumentSummary[] = [
  {
    path: "/docs/Project_Proposal.md",
    word_count: 3200,
    summary_text: "Comprehensive project proposal outlining the portfolio analysis system architecture, requirements, and implementation plan.",
    keywords: ["portfolio", "analysis", "capstone", "architecture", "requirements"],
    headings: ["Introduction", "System Architecture", "Requirements", "User Stories", "Timeline"],
  },
  {
    path: "/docs/Requirements_Document.md",
    word_count: 5400,
    summary_text: "Detailed requirements specification including functional requirements, use cases, and system constraints.",
    keywords: ["requirements", "functional", "non-functional", "use-cases", "constraints"],
    headings: ["Functional Requirements", "Non-Functional Requirements", "Use Cases", "System Constraints"],
  },
  {
    path: "/docs/api/API_Documentation.md",
    word_count: 6800,
    summary_text: "Complete API reference for the portfolio system including authentication, endpoints, and request/response formats.",
    keywords: ["API", "endpoints", "authentication", "REST", "FastAPI", "JWT"],
    headings: ["Authentication", "Endpoints", "Request/Response", "Error Handling", "Rate Limiting"],
  },
  {
    path: "/README.md",
    word_count: 1200,
    summary_text: "Getting started guide and project overview including setup instructions and usage examples.",
    keywords: ["setup", "installation", "usage", "Node.js", "npm", "Docker"],
    headings: ["Setup", "Installation", "Usage", "Development", "Testing"],
  },
  {
    path: "/docs/design/Design_Spec.txt",
    word_count: 2500,
    summary_text: "UI/UX design specifications and component guidelines for the portfolio interface.",
    keywords: ["design", "UI", "UX", "components", "Tailwind", "Figma"],
    headings: [],
  },
];

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

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
      return <FileIcon className="h-5 w-5 text-gray-500" />;
    default:
      return <FileIcon className="h-5 w-5 text-gray-500" />;
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

export function DocumentAnalysisTab() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string>("all");

  const stats = calculateStats(mockDocuments);

  const filteredDocuments = mockDocuments.filter((doc) => {
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

  return (
    <div className="space-y-6">
      {/* Statistics Overview */}
      <Card className="bg-white border border-gray-200">
        <CardHeader className="border-b border-gray-200">
          <CardTitle className="text-xl font-bold text-gray-900">Document Statistics</CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-gray-900">{stats.total_documents}</p>
              <p className="text-xs text-gray-500 mt-1">Total Documents</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-gray-900">
                {stats.total_words.toLocaleString()}
              </p>
              <p className="text-xs text-gray-500 mt-1">Total Words</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-gray-900">{stats.documents_with_keywords}</p>
              <p className="text-xs text-gray-500 mt-1">With Keywords</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-gray-900">{stats.documents_with_headings}</p>
              <p className="text-xs text-gray-500 mt-1">With Headings</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Document Type Breakdown */}
      <Card className="bg-white border border-gray-200">
        <CardHeader className="border-b border-gray-200">
          <CardTitle className="text-xl font-bold text-gray-900">Document Types</CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="flex items-center gap-3 p-3 bg-purple-50 border border-purple-200 rounded-lg">
              <BookOpen className="h-6 w-6 text-purple-500" />
              <div>
                <p className="text-lg font-bold text-gray-900">{stats.md_count}</p>
                <p className="text-xs text-gray-600">Markdown</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-gray-50 border border-gray-200 rounded-lg">
              <FileIcon className="h-6 w-6 text-gray-500" />
              <div>
                <p className="text-lg font-bold text-gray-900">{stats.txt_count}</p>
                <p className="text-xs text-gray-600">Text Files</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <FileType className="h-6 w-6 text-blue-500" />
              <div>
                <p className="text-lg font-bold text-gray-900">{stats.docx_count}</p>
                <p className="text-xs text-gray-600">Word Docs</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-gray-50 border border-gray-200 rounded-lg">
              <FileIcon className="h-6 w-6 text-gray-500" />
              <div>
                <p className="text-lg font-bold text-gray-900">{stats.other_count}</p>
                <p className="text-xs text-gray-600">Other</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Search and Filter */}
      <Card className="bg-white border border-gray-200">
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                type="text"
                placeholder="Search documents by name, title, or topic..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="flex gap-2">
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
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
      <Card className="bg-white border border-gray-200">
        <CardHeader className="border-b border-gray-200">
          <CardTitle className="text-xl font-bold text-gray-900">
            Documents ({filteredDocuments.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="space-y-4">
            {filteredDocuments.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No documents found matching your criteria
              </div>
            ) : (
              filteredDocuments.map((doc, index) => (
                <div
                  key={index}
                  className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors"
                >
                  <div className="flex items-start gap-4">
                    <div className="mt-1">{getFileIcon(getFileType(doc.path))}</div>
                    <div className="flex-1 min-w-0">
                      {/* File Header */}
                      <div className="flex items-start justify-between gap-4 mb-3">
                        <div className="flex-1 min-w-0">
                          <h3 className="font-semibold text-gray-900 mb-1 truncate">
                            {getFileName(doc.path)}
                          </h3>
                          <p className="text-xs text-gray-500 font-mono truncate">{doc.path}</p>
                        </div>
                        <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded uppercase">
                          {getFileType(doc.path)}
                        </span>
                      </div>

                      {/* Summary */}
                      {doc.summary_text && (
                        <p className="text-sm text-gray-600 mb-3">{doc.summary_text}</p>
                      )}

                      {/* Metadata */}
                      {doc.word_count && (
                        <div className="flex items-center gap-2 text-xs text-gray-600 mb-3">
                          <FileType className="h-3 w-3" />
                          <span>{doc.word_count.toLocaleString()} words</span>
                        </div>
                      )}

                      {/* Headings */}
                      {doc.headings.length > 0 && (
                        <div className="mb-3">
                          <p className="text-xs font-semibold text-gray-700 mb-1.5">
                            Headings ({doc.headings.length}):
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {doc.headings.slice(0, 5).map((heading, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded"
                              >
                                {heading}
                              </span>
                            ))}
                            {doc.headings.length > 5 && (
                              <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
                                +{doc.headings.length - 5} more
                              </span>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Keywords */}
                      {doc.keywords.length > 0 && (
                        <div>
                          <p className="text-xs font-semibold text-gray-700 mb-1.5">
                            Keywords ({doc.keywords.length}):
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {doc.keywords.slice(0, 8).map((keyword, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-1 bg-green-50 text-green-700 text-xs rounded"
                              >
                                {keyword}
                              </span>
                            ))}
                            {doc.keywords.length > 8 && (
                              <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
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
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
