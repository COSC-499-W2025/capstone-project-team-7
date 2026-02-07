// TypeScript types for Document Analysis
// Aligned with backend/src/api/spec_routes.py DocumentSummary and DocumentAnalysisSummary

/**
 * Represents a single analyzed document
 * Backend: DocumentSummary in spec_routes.py
 */
export interface DocumentSummary {
  path: string;
  word_count?: number;
  summary_text?: string;
  keywords: string[];
  headings: string[];
}

/**
 * Container for document analysis results
 * Backend: DocumentAnalysisSummary in spec_routes.py
 */
export interface DocumentAnalysisSummary {
  items: DocumentSummary[];
}

/**
 * Statistics derived from document analysis (computed client-side)
 */
export interface DocumentAnalysisStats {
  total_documents: number;
  total_words: number;
  documents_with_keywords: number;
  documents_with_headings: number;
  // File type breakdown (derived from file extensions)
  md_count: number;
  txt_count: number;
  docx_count: number;
  other_count: number;
}
