import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FileImage, FileText, Clock, Tag, TrendingUp } from "lucide-react";
import {
  projectPageSelectors,
  useProjectPageStore,
} from "@/lib/stores/project-page-store";

interface PdfKeyword {
  word: string;
  count: number;
}

interface PdfDocument {
  file_name: string;
  file_path: string;
  page_count: number;
  summary?: string;
  key_topics?: string[];
  keywords?: PdfKeyword[];
  reading_time?: number;
  file_size_mb?: number;
}

type PdfAnalysisPayload = unknown;

type PdfAnalysisTabProps = {
  pdfAnalysis?: PdfAnalysisPayload;
  isLoading?: boolean;
  errorMessage?: string | null;
  useStore?: boolean;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((entry): entry is string => typeof entry === "string");
}

function toKeywordArray(value: unknown): PdfKeyword[] {
  if (!Array.isArray(value)) return [];

  return value.reduce<PdfKeyword[]>((acc, entry) => {
    if (!isRecord(entry)) return acc;

    const word = typeof entry.word === "string" ? entry.word : "";
    const count = typeof entry.count === "number" ? entry.count : Number(entry.count);

    if (!word || !Number.isFinite(count)) return acc;

    acc.push({ word, count });
    return acc;
  }, []);
}

function normalizePdfAnalysis(payload: PdfAnalysisPayload): PdfDocument[] {
  if (!Array.isArray(payload)) return [];

  return payload.reduce<PdfDocument[]>((acc, entry) => {
    if (!isRecord(entry)) return acc;

    const fileName = typeof entry.file_name === "string" ? entry.file_name : "";
    const filePath = typeof entry.file_path === "string" ? entry.file_path : "";
    if (!fileName && !filePath) return acc;

    const normalized: PdfDocument = {
      file_name: fileName || filePath || "Unknown",
      file_path: filePath || fileName || "",
      page_count: typeof entry.page_count === "number" ? entry.page_count : 0,
      key_topics: toStringArray(entry.key_topics),
      keywords: toKeywordArray(entry.keywords),
      reading_time: typeof entry.reading_time === "number" ? entry.reading_time : 0,
      file_size_mb: typeof entry.file_size_mb === "number" ? entry.file_size_mb : 0,
    };

    if (typeof entry.summary === "string" && entry.summary.length > 0) {
      normalized.summary = entry.summary;
    }

    acc.push(normalized);
    return acc;
  }, []);
}

export function PdfAnalysisTab({
  pdfAnalysis,
  isLoading,
  errorMessage,
  useStore = false,
}: PdfAnalysisTabProps) {
  const scanData = useProjectPageStore(projectPageSelectors.scanData);
  const storeLoading = useProjectPageStore(projectPageSelectors.projectLoading);
  const storeError = useProjectPageStore(projectPageSelectors.projectError);
  const useStoreFallback = useStore;
  const resolvedPdfAnalysis =
    pdfAnalysis ?? (useStoreFallback ? scanData.pdf_analysis : undefined);
  const resolvedIsLoading = isLoading ?? (useStoreFallback ? storeLoading : false);
  const resolvedErrorMessage = errorMessage ?? (useStoreFallback ? storeError : null);
  const documents = normalizePdfAnalysis(resolvedPdfAnalysis);

  // Calculate statistics
  const stats = {
    total_pdfs: documents.length,
    total_pages: documents.reduce((sum, doc) => sum + doc.page_count, 0),
    total_reading_time: documents.reduce((sum, doc) => sum + (doc.reading_time || 0), 0),
    avg_pages: documents.length > 0 
      ? Math.round(documents.reduce((sum, doc) => sum + doc.page_count, 0) / documents.length) 
      : 0,
  };

  const emptyMessage = !documents || documents.length === 0
    ? "No PDF documents found in this project"
    : "No PDFs match your criteria";

  return (
    <div className="space-y-6">
      {/* Statistics Overview */}
      <Card className="bg-white border border-gray-200">
        <CardHeader className="border-b border-gray-200">
          <CardTitle className="text-xl font-bold text-gray-900">PDF Statistics</CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-gray-900">{stats.total_pdfs}</p>
              <p className="text-xs text-gray-500 mt-1">Total PDFs</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-gray-900">{stats.total_pages}</p>
              <p className="text-xs text-gray-500 mt-1">Total Pages</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-gray-900">{stats.avg_pages}</p>
              <p className="text-xs text-gray-500 mt-1">Avg Pages/PDF</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-gray-900">{Math.round(stats.total_reading_time)}</p>
              <p className="text-xs text-gray-500 mt-1">Total Minutes</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* PDF Documents List */}
      <Card className="bg-white border border-gray-200">
        <CardHeader className="border-b border-gray-200">
          <CardTitle className="text-xl font-bold text-gray-900">
            PDF Documents ({documents.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          {resolvedIsLoading && (
            <div className="text-center py-8 text-gray-500">
              Loading PDF analysis…
            </div>
          )}
          {resolvedErrorMessage && !resolvedIsLoading && (
            <div className="text-center py-8 text-red-600">
              {resolvedErrorMessage}
            </div>
          )}
          <div className="space-y-4">
            {!resolvedIsLoading && !resolvedErrorMessage && documents.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                {emptyMessage}
              </div>
            ) : (!resolvedIsLoading && !resolvedErrorMessage ? (
              documents.map((doc, index) => (
                <div
                  key={index}
                  className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors"
                >
                  <div className="flex items-start gap-4">
                    <div className="mt-1">
                      <FileImage className="h-6 w-6 text-red-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      {/* Header */}
                      <div className="flex items-start justify-between gap-4 mb-3">
                        <div className="flex-1 min-w-0">
                          <h3 className="text-sm font-semibold text-gray-900 truncate">
                            {doc.file_name}
                          </h3>
                          {doc.file_path && doc.file_path !== doc.file_name && (
                            <p className="text-xs text-gray-500 mt-1 truncate">{doc.file_path}</p>
                          )}
                        </div>
                        <div className="flex gap-4 text-xs text-gray-600 shrink-0">
                          <div className="flex items-center gap-1">
                            <FileText className="h-3 w-3" />
                            <span>{doc.page_count} pages</span>
                          </div>
                          {doc.reading_time && doc.reading_time > 0 && (
                            <div className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              <span>{Math.round(doc.reading_time)} min</span>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Summary */}
                      {doc.summary && (
                        <div className="mb-3">
                          <p className="text-sm text-gray-700 leading-relaxed">
                            {doc.summary}
                          </p>
                        </div>
                      )}

                      {/* Key Topics */}
                      {doc.key_topics && doc.key_topics.length > 0 && (
                        <div className="mb-3">
                          <div className="flex items-center gap-2 mb-2">
                            <TrendingUp className="h-4 w-4 text-blue-600" />
                            <span className="text-xs font-medium text-gray-700">Key Topics:</span>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {doc.key_topics.map((topic, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded-md border border-blue-200"
                              >
                                {topic}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Keywords */}
                      {doc.keywords && doc.keywords.length > 0 && (
                        <div>
                          <div className="flex items-center gap-2 mb-2">
                            <Tag className="h-4 w-4 text-green-600" />
                            <span className="text-xs font-medium text-gray-700">Keywords:</span>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {doc.keywords.slice(0, 10).map((kw, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-1 bg-green-50 text-green-700 text-xs rounded-md border border-green-200 flex items-center gap-1"
                              >
                                {kw.word}
                                <span className="text-green-500">({kw.count})</span>
                              </span>
                            ))}
                            {doc.keywords.length > 10 && (
                              <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
                                +{doc.keywords.length - 10} more
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
