import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Code2, FileCode, Braces, Box, TrendingUp, AlertCircle, AlertTriangle, Copy, GitBranch, Hash, XCircle, Type, Layers, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import {
  projectPageSelectors,
  useProjectPageStore,
} from "@/lib/stores/project-page-store";

// Example types
interface MagicValueExample {
  file: string;
  type: string;
  value: string;
  line: number;
  code_snippet: string;
  suggested_name?: string;
}

interface DeadCodeExample {
  file: string;
  type: string;
  name: string;
  line: number;
  code_snippet: string;
  reason?: string;
  confidence?: string;
}

interface DuplicateExample {
  file1?: string;
  file2?: string;
  file?: string;
  line1?: number;
  line2?: number;
  lines?: number;
  similarity?: number;
  code_snippet?: string;
}

interface NamingIssueExample {
  file: string;
  name: string;
  line: number;
  issue_type: string;
  suggestion?: string;
}

interface ErrorHandlingExample {
  file: string;
  line: number;
  issue_type: string;
  severity: string;
  code_snippet?: string;
}

export interface CodeAnalysisData {
  total_files?: number;
  total_lines?: number;
  code_lines?: number;
  comment_lines?: number;
  functions?: number;
  classes?: number;
  avg_complexity?: number;
  avg_maintainability?: number;
  
  // Code quality metrics
  magic_values?: number;
  dead_code?: {
    total: number;
    unused_functions: number;
    unused_imports: number;
    unused_variables: number;
  };
  duplicates?: {
    within_file: number;
    cross_file: number;
    total_duplicate_lines: number;
  };
  error_handling_issues?: {
    total: number;
    critical: number;
    warning: number;
  };
  naming_issues?: number;
  nesting_issues?: number;
  call_graph_edges?: number;
  data_structures?: Record<string, number>;
  languages?: Record<string, number>;
  
  // Detailed examples
  examples?: {
    magic_values?: MagicValueExample[];
    dead_code?: DeadCodeExample[];
    duplicates?: DuplicateExample[];
    naming_issues?: NamingIssueExample[];
    error_handling?: ErrorHandlingExample[];
  };
}

interface CodeAnalysisTabProps {
  codeAnalysis?: CodeAnalysisData | null;
  isLoading?: boolean;
  errorMessage?: string | null;
  useStore?: boolean;
}

const overviewCardStyles = {
  blue: {
    card: "border-blue-200 bg-gradient-to-br from-blue-50 to-white dark:border-blue-500/20 dark:from-blue-500/10 dark:to-card",
    icon: "text-blue-600 dark:text-blue-300",
  },
  purple: {
    card: "border-purple-200 bg-gradient-to-br from-purple-50 to-white dark:border-purple-500/20 dark:from-purple-500/10 dark:to-card",
    icon: "text-purple-600 dark:text-purple-300",
  },
  emerald: {
    card: "border-emerald-200 bg-gradient-to-br from-emerald-50 to-white dark:border-emerald-500/20 dark:from-emerald-500/10 dark:to-card",
    icon: "text-emerald-600 dark:text-emerald-300",
  },
  amber: {
    card: "border-amber-200 bg-gradient-to-br from-amber-50 to-white dark:border-amber-500/20 dark:from-amber-500/10 dark:to-card",
    icon: "text-amber-600 dark:text-amber-300",
  },
} as const;

const issueCardStyles = {
  orange: {
    card: "border-orange-200 bg-orange-50 dark:border-orange-500/20 dark:bg-orange-500/10",
    icon: "text-orange-600 dark:text-orange-300",
    metric: "text-orange-700 dark:text-orange-200",
    divider: "border-orange-200 dark:border-orange-500/20",
    button: "text-orange-700 hover:text-orange-900 dark:text-orange-300 dark:hover:text-orange-200",
    example: "border-orange-100 bg-white dark:border-orange-500/20 dark:bg-card",
    exampleText: "text-orange-800 dark:text-orange-200",
  },
  purple: {
    card: "border-purple-200 bg-purple-50 dark:border-purple-500/20 dark:bg-purple-500/10",
    icon: "text-purple-600 dark:text-purple-300",
    metric: "text-purple-700 dark:text-purple-200",
    divider: "border-purple-200 dark:border-purple-500/20",
    button: "text-purple-700 hover:text-purple-900 dark:text-purple-300 dark:hover:text-purple-200",
    example: "border-purple-100 bg-white dark:border-purple-500/20 dark:bg-card",
  },
  yellow: {
    card: "border-yellow-200 bg-yellow-50 dark:border-yellow-500/20 dark:bg-yellow-500/10",
    icon: "text-yellow-600 dark:text-yellow-300",
    metric: "text-yellow-700 dark:text-yellow-200",
    divider: "border-yellow-200 dark:border-yellow-500/20",
    button: "text-yellow-700 hover:text-yellow-900 dark:text-yellow-300 dark:hover:text-yellow-200",
    example: "border-yellow-100 bg-white dark:border-yellow-500/20 dark:bg-card",
    exampleText: "text-yellow-800 dark:text-yellow-200",
    suggestion: "text-yellow-600 dark:text-yellow-300",
  },
  red: {
    card: "border-red-200 bg-red-50 dark:border-red-500/20 dark:bg-red-500/10",
    icon: "text-red-600 dark:text-red-300",
    metric: "text-red-700 dark:text-red-200",
    divider: "border-red-200 dark:border-red-500/20",
    button: "text-red-700 hover:text-red-900 dark:text-red-300 dark:hover:text-red-200",
    example: "border-red-100 bg-white dark:border-red-500/20 dark:bg-card",
    exampleText: "text-red-800 dark:text-red-200",
  },
  blue: {
    card: "border-blue-200 bg-blue-50 dark:border-blue-500/20 dark:bg-blue-500/10",
    icon: "text-blue-600 dark:text-blue-300",
    metric: "text-blue-700 dark:text-blue-200",
    divider: "border-blue-200 dark:border-blue-500/20",
    button: "text-blue-700 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-200",
    example: "border-blue-100 bg-white dark:border-blue-500/20 dark:bg-card",
    exampleText: "text-blue-800 dark:text-blue-200",
  },
  indigo: {
    card: "border-indigo-200 bg-indigo-50 dark:border-indigo-500/20 dark:bg-indigo-500/10",
    icon: "text-indigo-600 dark:text-indigo-300",
    metric: "text-indigo-700 dark:text-indigo-200",
  },
} as const;

// Helper to get short filename from path
function getShortPath(fullPath: string): string {
  const parts = fullPath.replace(/\\/g, '/').split('/');
  return parts.slice(-2).join('/');
}

export function CodeAnalysisTab({
  codeAnalysis,
  isLoading,
  errorMessage,
  useStore = false,
}: CodeAnalysisTabProps) {
  const scanData = useProjectPageStore(projectPageSelectors.scanData);
  const storeLoading = useProjectPageStore(projectPageSelectors.projectLoading);
  const storeError = useProjectPageStore(projectPageSelectors.projectError);
  const useStoreFallback = useStore;
  const resolvedCodeAnalysis =
    codeAnalysis ??
    (useStoreFallback ? (scanData.code_analysis as CodeAnalysisData | undefined) ?? null : null);
  const resolvedIsLoading = isLoading ?? (useStoreFallback ? storeLoading : false);
  const resolvedErrorMessage = errorMessage ?? (useStoreFallback ? storeError : null);

  // State for expanded sections
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});
  
  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // Loading state
  if (resolvedIsLoading) {
    return (
      <Card className="bg-white border border-gray-200">
        <CardHeader className="border-b border-gray-200">
          <CardTitle className="text-xl font-bold text-gray-900">
            Code Analysis
          </CardTitle>
          <p className="text-xs text-gray-500 mt-1">
            Analyzing code metrics and quality...
          </p>
        </CardHeader>
        <CardContent className="p-6">
          <div className="space-y-4 animate-pulse">
            <div className="h-24 rounded-lg bg-gray-100" />
            <div className="h-24 rounded-lg bg-gray-100" />
            <div className="h-24 rounded-lg bg-gray-100" />
          </div>
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (resolvedErrorMessage) {
    return (
      <Card className="bg-white border border-gray-200">
        <CardHeader className="border-b border-gray-200">
          <CardTitle className="text-xl font-bold text-gray-900">
            Code Analysis
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-red-700">
                Failed to load code analysis
              </p>
              <p className="text-xs text-red-600 mt-1">{resolvedErrorMessage}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // No data state - check for meaningful data
  if (!resolvedCodeAnalysis || 
      (typeof resolvedCodeAnalysis === 'object' && Object.keys(resolvedCodeAnalysis).length === 0)) {
    return (
      <Card className="bg-white border border-gray-200">
        <CardHeader className="border-b border-gray-200">
          <CardTitle className="text-xl font-bold text-gray-900">
            Code Analysis
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center">
            <Code2 className="h-12 w-12 text-gray-400 mx-auto mb-3" />
            <p className="text-sm font-semibold text-gray-900">
              No code analysis data available
            </p>
            <p className="text-xs text-gray-500 mt-2">
              Run a scan with code analysis enabled to see detailed metrics about
              your codebase structure and quality.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const {
    total_files = 0,
    total_lines = 0,
    code_lines = 0,
    comment_lines = 0,
    functions = 0,
    classes = 0,
    avg_complexity,
    avg_maintainability,
    magic_values = 0,
    dead_code,
    duplicates,
    error_handling_issues,
    naming_issues = 0,
    nesting_issues = 0,
    call_graph_edges = 0,
    data_structures,
    examples,
  } = resolvedCodeAnalysis;

  // Calculate percentages
  const commentPercentage = total_lines > 0 
    ? ((comment_lines / total_lines) * 100).toFixed(1)
    : "0.0";
  const codePercentage = total_lines > 0 
    ? ((code_lines / total_lines) * 100).toFixed(1)
    : "0.0";

  // Quality indicators
  const getComplexityColor = (complexity?: number) => {
    if (!complexity) return "text-gray-500";
    if (complexity < 10) return "text-green-600";
    if (complexity < 20) return "text-yellow-600";
    return "text-red-600";
  };

  const getComplexityLabel = (complexity?: number) => {
    if (!complexity) return "N/A";
    if (complexity < 10) return "Low";
    if (complexity < 20) return "Moderate";
    return "High";
  };

  const getMaintainabilityColor = (maintainability?: number) => {
    if (!maintainability) return "text-gray-500";
    if (maintainability >= 80) return "text-green-600";
    if (maintainability >= 60) return "text-yellow-600";
    return "text-red-600";
  };

  const getMaintainabilityLabel = (maintainability?: number) => {
    if (!maintainability) return "N/A";
    if (maintainability >= 80) return "Excellent";
    if (maintainability >= 60) return "Good";
    return "Needs Improvement";
  };

  return (
    <div className="space-y-6">
      <Card className="bg-white border border-gray-200">
        <CardHeader className="border-b border-gray-200 p-5 pb-4 sm:p-5 sm:pb-4">
          <CardTitle className="text-xl font-bold text-gray-900">
            Code Analysis Overview
          </CardTitle>
          <p className="text-xs text-gray-500 mt-1">
            Comprehensive metrics about your codebase structure and quality
          </p>
        </CardHeader>
        <CardContent className="p-5 sm:p-5">
          {/* Overview Cards */}
          <div className="mb-5 grid items-start gap-4 md:grid-cols-2 lg:grid-cols-4">
            {/* Total Files */}
            <div className={cn("self-start rounded-lg border p-4", overviewCardStyles.blue.card)}>
              <div className="flex items-center justify-between mb-2">
                <FileCode className={cn("h-5 w-5", overviewCardStyles.blue.icon)} />
              </div>
              <p className="text-3xl font-bold text-gray-900 dark:text-foreground">
                {total_files.toLocaleString()}
              </p>
              <p className="mt-1 text-xs text-gray-600 dark:text-muted-foreground">Total Files Analyzed</p>
            </div>

            {/* Total Lines */}
            <div className={cn("self-start rounded-lg border p-4", overviewCardStyles.purple.card)}>
              <div className="flex items-center justify-between mb-2">
                <Code2 className={cn("h-5 w-5", overviewCardStyles.purple.icon)} />
              </div>
              <p className="text-3xl font-bold text-gray-900 dark:text-foreground">
                {total_lines.toLocaleString()}
              </p>
              <p className="mt-1 text-xs text-gray-600 dark:text-muted-foreground">Total Lines of Code</p>
            </div>

            {/* Functions */}
            <div className={cn("self-start rounded-lg border p-4", overviewCardStyles.emerald.card)}>
              <div className="flex items-center justify-between mb-2">
                <Braces className={cn("h-5 w-5", overviewCardStyles.emerald.icon)} />
              </div>
              <p className="text-3xl font-bold text-gray-900 dark:text-foreground">
                {functions.toLocaleString()}
              </p>
              <p className="mt-1 text-xs text-gray-600 dark:text-muted-foreground">Functions</p>
            </div>

            {/* Classes */}
            <div className={cn("self-start rounded-lg border p-4", overviewCardStyles.amber.card)}>
              <div className="flex items-center justify-between mb-2">
                <Box className={cn("h-5 w-5", overviewCardStyles.amber.icon)} />
              </div>
              <p className="text-3xl font-bold text-gray-900 dark:text-foreground">
                {classes.toLocaleString()}
              </p>
              <p className="mt-1 text-xs text-gray-600 dark:text-muted-foreground">Classes</p>
            </div>
          </div>

          {/* Code Composition */}
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">
              Code Composition
            </h3>
            <div className="grid gap-4 md:grid-cols-2">
              {/* Code Lines */}
              <div className="rounded-lg border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="h-3 w-3 rounded-full bg-blue-500" />
                    <span className="text-sm font-medium text-gray-700">
                      Code Lines
                    </span>
                  </div>
                  <span className="text-sm font-bold text-gray-900">
                    {codePercentage}%
                  </span>
                </div>
                <p className="text-2xl font-bold text-gray-900">
                  {code_lines.toLocaleString()}
                </p>
                <div className="mt-2 h-2 w-full rounded-full bg-gray-100 overflow-hidden">
                  <div
                    className="h-full bg-blue-500 transition-all duration-300"
                    style={{ width: `${codePercentage}%` }}
                  />
                </div>
              </div>

              {/* Comment Lines */}
              <div className="rounded-lg border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="h-3 w-3 rounded-full bg-green-500" />
                    <span className="text-sm font-medium text-gray-700">
                      Comment Lines
                    </span>
                  </div>
                  <span className="text-sm font-bold text-gray-900">
                    {commentPercentage}%
                  </span>
                </div>
                <p className="text-2xl font-bold text-gray-900">
                  {comment_lines.toLocaleString()}
                </p>
                <div className="mt-2 h-2 w-full rounded-full bg-gray-100 overflow-hidden">
                  <div
                    className="h-full bg-green-500 transition-all duration-300"
                    style={{ width: `${commentPercentage}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Quality Metrics */}
          {(avg_complexity !== undefined || avg_maintainability !== undefined) && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3">
                Code Quality Metrics
              </h3>
              <div className="grid gap-4 md:grid-cols-2">
                {/* Average Complexity */}
                {avg_complexity !== undefined && avg_complexity !== null && (
                  <div className="rounded-lg border border-gray-200 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp className="h-4 w-4 text-gray-600" />
                      <span className="text-sm font-medium text-gray-700">
                        Average Complexity
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <p className={`text-3xl font-bold ${getComplexityColor(avg_complexity)}`}>
                        {avg_complexity.toFixed(2)}
                      </p>
                      <span className={`text-sm font-semibold ${getComplexityColor(avg_complexity)}`}>
                        {getComplexityLabel(avg_complexity)}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mt-2">
                      Lower values indicate simpler, more maintainable code
                    </p>
                  </div>
                )}

                {/* Average Maintainability */}
                {avg_maintainability !== undefined && avg_maintainability !== null && (
                  <div className="rounded-lg border border-gray-200 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp className="h-4 w-4 text-gray-600" />
                      <span className="text-sm font-medium text-gray-700">
                        Average Maintainability
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <p className={`text-3xl font-bold ${getMaintainabilityColor(avg_maintainability)}`}>
                        {avg_maintainability.toFixed(1)}
                      </p>
                      <span className={`text-sm font-semibold ${getMaintainabilityColor(avg_maintainability)}`}>
                        {getMaintainabilityLabel(avg_maintainability)}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mt-2">
                      Score from 0-100, higher is better
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Code Quality Issues Card */}
      {(dead_code || duplicates || magic_values > 0 || error_handling_issues || naming_issues > 0 || nesting_issues > 0) && (
        <Card className="bg-white border border-gray-200">
          <CardHeader className="border-b border-gray-200 p-5 pb-4 sm:p-5 sm:pb-4">
            <CardTitle className="text-base font-bold text-gray-900">
              Code Quality Issues
            </CardTitle>
          </CardHeader>
          <CardContent className="p-5 sm:p-5">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {/* Dead Code */}
              {dead_code && dead_code.total > 0 && (
                <div className={cn("rounded-lg border p-4", issueCardStyles.orange.card)}>
                  <div className="flex items-center gap-2 mb-3">
                    <XCircle className={cn("h-5 w-5", issueCardStyles.orange.icon)} />
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-foreground">
                      Dead Code Detection
                    </h3>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-muted-foreground">Total items:</span>
                      <span className={cn("font-semibold", issueCardStyles.orange.metric)}>
                        {dead_code.total}
                      </span>
                    </div>
                    <div className="pl-3 space-y-1 text-xs text-gray-600 dark:text-muted-foreground">
                      <div>• Unused functions: {dead_code.unused_functions}</div>
                      <div>• Unused imports: {dead_code.unused_imports}</div>
                      <div>• Unused variables: {dead_code.unused_variables}</div>
                    </div>
                  </div>
                  <p className="mt-3 text-xs text-gray-500 dark:text-muted-foreground">
                    Remove unused code to improve maintainability
                  </p>
                  {/* Examples */}
                  {examples?.dead_code && examples.dead_code.length > 0 && (
                    <div className={cn("mt-3 border-t pt-3", issueCardStyles.orange.divider)}>
                      <button
                        onClick={() => toggleSection('deadCode')}
                        className={cn("flex items-center gap-1 text-xs", issueCardStyles.orange.button)}
                      >
                        {expandedSections.deadCode ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                        {expandedSections.deadCode ? 'Hide' : 'Show'} examples
                      </button>
                      {expandedSections.deadCode && (
                        <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
                          {examples.dead_code.map((ex, i) => (
                            <div key={i} className={cn("rounded border p-2 text-xs", issueCardStyles.orange.example)}>
                              <div className={cn("font-mono", issueCardStyles.orange.exampleText)}>{ex.name}</div>
                              <div className="text-gray-500 dark:text-muted-foreground">{getShortPath(ex.file)}:{ex.line}</div>
                              <code className="mt-1 block truncate rounded bg-gray-50 p-1 text-gray-700 dark:bg-muted dark:text-foreground">{ex.code_snippet}</code>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Duplicate Code */}
              {duplicates && (duplicates.within_file > 0 || duplicates.cross_file > 0) && (
                <div className={cn("rounded-lg border p-4", issueCardStyles.purple.card)}>
                  <div className="flex items-center gap-2 mb-3">
                    <Copy className={cn("h-5 w-5", issueCardStyles.purple.icon)} />
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-foreground">
                      Duplicate Code Detection
                    </h3>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-muted-foreground">Total blocks:</span>
                      <span className={cn("font-semibold", issueCardStyles.purple.metric)}>
                        {duplicates.within_file + duplicates.cross_file}
                      </span>
                    </div>
                    <div className="pl-3 space-y-1 text-xs text-gray-600 dark:text-muted-foreground">
                      <div>• Within-file: {duplicates.within_file}</div>
                      <div>• Cross-file: {duplicates.cross_file}</div>
                      <div>• Duplicate lines: ~{duplicates.total_duplicate_lines}</div>
                    </div>
                  </div>
                  <p className="mt-3 text-xs text-gray-500 dark:text-muted-foreground">
                    Extract duplicates into reusable functions
                  </p>
                  {/* Examples */}
                  {examples?.duplicates && examples.duplicates.length > 0 && (
                    <div className={cn("mt-3 border-t pt-3", issueCardStyles.purple.divider)}>
                      <button
                        onClick={() => toggleSection('duplicates')}
                        className={cn("flex items-center gap-1 text-xs", issueCardStyles.purple.button)}
                      >
                        {expandedSections.duplicates ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                        {expandedSections.duplicates ? 'Hide' : 'Show'} examples
                      </button>
                      {expandedSections.duplicates && (
                        <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
                          {examples.duplicates.map((ex, i) => (
                            <div key={i} className={cn("rounded border p-2 text-xs", issueCardStyles.purple.example)}>
                              {ex.file1 && ex.file2 ? (
                                <>
                                  <div className="text-gray-500 dark:text-muted-foreground">{getShortPath(ex.file1)}:{ex.line1}</div>
                                  <div className="text-gray-500 dark:text-muted-foreground">{getShortPath(ex.file2)}:{ex.line2}</div>
                                </>
                              ) : ex.file ? (
                                <div className="text-gray-500 dark:text-muted-foreground">{getShortPath(ex.file)}:{ex.lines || ex.line1}</div>
                              ) : null}
                              {ex.similarity && <div className={cn(issueCardStyles.purple.metric)}>Similarity: {(ex.similarity * 100).toFixed(0)}%</div>}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Magic Values */}
              {magic_values > 0 && (
                <div className={cn("rounded-lg border p-4", issueCardStyles.yellow.card)}>
                  <div className="flex items-center gap-2 mb-3">
                    <Hash className={cn("h-5 w-5", issueCardStyles.yellow.icon)} />
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-foreground">
                      Magic Value Detection
                    </h3>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-muted-foreground">Hardcoded values:</span>
                      <span className={cn("font-semibold", issueCardStyles.yellow.metric)}>
                        {magic_values}
                      </span>
                    </div>
                  </div>
                  <p className="mt-3 text-xs text-gray-500 dark:text-muted-foreground">
                    Replace magic numbers/strings with named constants
                  </p>
                  {/* Examples */}
                  {examples?.magic_values && examples.magic_values.length > 0 && (
                    <div className={cn("mt-3 border-t pt-3", issueCardStyles.yellow.divider)}>
                      <button
                        onClick={() => toggleSection('magicValues')}
                        className={cn("flex items-center gap-1 text-xs", issueCardStyles.yellow.button)}
                      >
                        {expandedSections.magicValues ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                        {expandedSections.magicValues ? 'Hide' : 'Show'} examples
                      </button>
                      {expandedSections.magicValues && (
                        <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
                          {examples.magic_values.map((ex, i) => (
                            <div key={i} className={cn("rounded border p-2 text-xs", issueCardStyles.yellow.example)}>
                              <div className="flex justify-between">
                                <span className={cn("font-mono", issueCardStyles.yellow.exampleText)}>{ex.value}</span>
                                <span className="text-gray-400 dark:text-muted-foreground">{ex.type}</span>
                              </div>
                              <div className="text-gray-500 dark:text-muted-foreground">{getShortPath(ex.file)}:{ex.line}</div>
                              <code className="mt-1 block truncate rounded bg-gray-50 p-1 text-gray-700 dark:bg-muted dark:text-foreground">{ex.code_snippet}</code>
                              {ex.suggested_name && <div className={cn("mt-1", issueCardStyles.yellow.suggestion)}>Suggest: {ex.suggested_name}</div>}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Error Handling */}
              {error_handling_issues && error_handling_issues.total > 0 && (
                <div className={cn("rounded-lg border p-4", issueCardStyles.red.card)}>
                  <div className="flex items-center gap-2 mb-3">
                    <AlertTriangle className={cn("h-5 w-5", issueCardStyles.red.icon)} />
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-foreground">
                      Error Handling Quality
                    </h3>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-muted-foreground">Total issues:</span>
                      <span className={cn("font-semibold", issueCardStyles.red.metric)}>
                        {error_handling_issues.total}
                      </span>
                    </div>
                    <div className="pl-3 space-y-1 text-xs text-gray-600 dark:text-muted-foreground">
                      <div>• Critical: {error_handling_issues.critical}</div>
                      <div>• Warnings: {error_handling_issues.warning}</div>
                    </div>
                  </div>
                  <p className="mt-3 text-xs text-gray-500 dark:text-muted-foreground">
                    Fix empty catch blocks and broad exceptions
                  </p>
                  {/* Examples */}
                  {examples?.error_handling && examples.error_handling.length > 0 && (
                    <div className={cn("mt-3 border-t pt-3", issueCardStyles.red.divider)}>
                      <button
                        onClick={() => toggleSection('errorHandling')}
                        className={cn("flex items-center gap-1 text-xs", issueCardStyles.red.button)}
                      >
                        {expandedSections.errorHandling ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                        {expandedSections.errorHandling ? 'Hide' : 'Show'} examples
                      </button>
                      {expandedSections.errorHandling && (
                        <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
                          {examples.error_handling.map((ex, i) => (
                            <div key={i} className={cn("rounded border p-2 text-xs", issueCardStyles.red.example)}>
                              <div className="flex justify-between">
                                <span className={cn("font-medium", issueCardStyles.red.exampleText)}>{ex.issue_type}</span>
                                <span className={ex.severity === 'critical' ? 'text-red-600 dark:text-red-300' : 'text-yellow-600 dark:text-yellow-300'}>{ex.severity}</span>
                              </div>
                              <div className="text-gray-500 dark:text-muted-foreground">{getShortPath(ex.file)}:{ex.line}</div>
                              {ex.code_snippet && <code className="mt-1 block truncate rounded bg-gray-50 p-1 text-gray-700 dark:bg-muted dark:text-foreground">{ex.code_snippet}</code>}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Naming Issues */}
              {naming_issues > 0 && (
                <div className={cn("rounded-lg border p-4", issueCardStyles.blue.card)}>
                  <div className="flex items-center gap-2 mb-3">
                    <Type className={cn("h-5 w-5", issueCardStyles.blue.icon)} />
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-foreground">
                      Naming Convention Checking
                    </h3>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-muted-foreground">Violations:</span>
                      <span className={cn("font-semibold", issueCardStyles.blue.metric)}>
                        {naming_issues}
                      </span>
                    </div>
                  </div>
                  <p className="mt-3 text-xs text-gray-500 dark:text-muted-foreground">
                    Follow language naming conventions
                  </p>
                  {/* Examples */}
                  {examples?.naming_issues && examples.naming_issues.length > 0 && (
                    <div className={cn("mt-3 border-t pt-3", issueCardStyles.blue.divider)}>
                      <button
                        onClick={() => toggleSection('namingIssues')}
                        className={cn("flex items-center gap-1 text-xs", issueCardStyles.blue.button)}
                      >
                        {expandedSections.namingIssues ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                        {expandedSections.namingIssues ? 'Hide' : 'Show'} examples
                      </button>
                      {expandedSections.namingIssues && (
                        <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
                          {examples.naming_issues.map((ex, i) => (
                            <div key={i} className={cn("rounded border p-2 text-xs", issueCardStyles.blue.example)}>
                              <div className={cn("font-mono", issueCardStyles.blue.exampleText)}>{ex.name}</div>
                              <div className="text-gray-500 dark:text-muted-foreground">{getShortPath(ex.file)}:{ex.line}</div>
                              <div className="text-blue-600 dark:text-blue-300">{ex.issue_type}</div>
                              {ex.suggestion && <div className="mt-1 text-green-600 dark:text-green-300">→ {ex.suggestion}</div>}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
              {/* Nesting Depth */}
              {nesting_issues > 0 && (
                <div className={cn("rounded-lg border p-4", issueCardStyles.indigo.card)}>
                  <div className="flex items-center gap-2 mb-3">
                    <Layers className={cn("h-5 w-5", issueCardStyles.indigo.icon)} />
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-foreground">
                      Nesting Depth Analysis
                    </h3>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-muted-foreground">Deep functions:</span>
                      <span className={cn("font-semibold", issueCardStyles.indigo.metric)}>
                        {nesting_issues}
                      </span>
                    </div>
                  </div>
                  <p className="mt-3 text-xs text-gray-500 dark:text-muted-foreground">
                    Reduce nesting to improve readability
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Call Graph Analysis Card */}
      {call_graph_edges > 0 && (
        <Card className="bg-white border border-gray-200">
          <CardHeader className="border-b border-gray-200 p-5 pb-4 sm:p-5 sm:pb-4">
            <CardTitle className="text-base font-bold text-gray-900 flex items-center gap-2">
              <GitBranch className="h-5 w-5" />
              Call Graph Analysis
            </CardTitle>
          </CardHeader>
          <CardContent className="p-5 sm:p-5">
            <div className="flex items-center gap-4">
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 flex-1">
                <p className="text-sm text-gray-600 mb-1">Function Relationships</p>
                <p className="text-3xl font-bold text-gray-900">{call_graph_edges}</p>
                <p className="text-xs text-gray-500 mt-2">
                  Tracks function call relationships to understand code flow
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Data Structure Usage Card */}
      {data_structures && Object.keys(data_structures).length > 0 && (
        <Card className="bg-white border border-gray-200">
          <CardHeader className="border-b border-gray-200 p-5 pb-4 sm:p-5 sm:pb-4">
            <CardTitle className="text-base font-bold text-gray-900">
              Data Structure Usage Tracking
            </CardTitle>
          </CardHeader>
          <CardContent className="p-5 sm:p-5">
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {Object.entries(data_structures)
                .sort(([, a], [, b]) => b - a)
                .map(([structure, count]) => (
                  <div
                    key={structure}
                    className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 p-3"
                  >
                    <span className="text-sm font-medium text-gray-700 capitalize">
                      {structure}
                    </span>
                    <span className="text-lg font-bold text-gray-900">{count}</span>
                  </div>
                ))}
            </div>
            <p className="text-xs text-gray-500 mt-4">
              Tracks usage of lists, dicts, sets, and other data structures
            </p>
          </CardContent>
        </Card>
      )}

      {/* Additional Insights Card */}
      <Card className="bg-white border border-gray-200">
        <CardHeader className="border-b border-gray-200 p-5 pb-4 sm:p-5 sm:pb-4">
          <CardTitle className="text-base font-bold text-gray-900">
            Code Statistics
          </CardTitle>
        </CardHeader>
        <CardContent className="p-5 sm:p-5">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Average lines per file:</span>
                <span className="font-semibold text-gray-900">
                  {total_files > 0 ? (total_lines / total_files).toFixed(1) : "0"}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Functions per file:</span>
                <span className="font-semibold text-gray-900">
                  {total_files > 0 ? (functions / total_files).toFixed(1) : "0"}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Classes per file:</span>
                <span className="font-semibold text-gray-900">
                  {total_files > 0 ? (classes / total_files).toFixed(1) : "0"}
                </span>
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Code to comment ratio:</span>
                <span className="font-semibold text-gray-900">
                  {comment_lines > 0 ? (code_lines / comment_lines).toFixed(2) : "N/A"}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Documentation coverage:</span>
                <span className="font-semibold text-gray-900">
                  {commentPercentage}%
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Lines per function:</span>
                <span className="font-semibold text-gray-900">
                  {functions > 0 ? (code_lines / functions).toFixed(1) : "N/A"}
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
