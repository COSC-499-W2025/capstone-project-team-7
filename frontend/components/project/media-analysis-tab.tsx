"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { LoadingState } from "@/components/ui/loading-state";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import { formatBytes } from "@/lib/format-utils";
import { FileImage, Film } from "lucide-react";
import { resolveMediaAnalysis } from "@/lib/project-media-analysis";
import {
  projectPageSelectors,
  useProjectPageStore,
} from "@/lib/stores/project-page-store";

export type MediaAnalysisSummary = {
  total_media_files?: number;
  image_files?: number;
  audio_files?: number;
  video_files?: number;
  total_files?: number;
  total_size_bytes?: number;
  by_type?: {
    images?: { count?: number; size_bytes?: number };
    videos?: { count?: number; size_bytes?: number };
    audio?: { count?: number; size_bytes?: number };
  };
};

export type MediaAnalysisMetrics = {
  images?: {
    count?: number;
    average_width?: number;
    average_height?: number;
    max_resolution?: { path?: string; dimensions?: [number, number]; mode?: string };
    min_resolution?: { path?: string; dimensions?: [number, number]; mode?: string };
    common_aspect_ratios?: Record<string, number>;
    top_labels?: Array<{ label: string; share: number }>;
    content_summaries?: Array<{ path: string; summary: string }>;
  };
  audio?: {
    count?: number;
    total_duration_seconds?: number;
    average_duration_seconds?: number;
    longest_clip?: { path?: string; duration_seconds?: number };
    shortest_clip?: { path?: string; duration_seconds?: number };
    bitrate_stats?: { min: number; max: number; average: number };
    sample_rate_stats?: { min: number; max: number; average: number };
    channel_distribution?: Record<string, number>;
    top_labels?: Array<{ label: string; share: number }>;
    tempo_stats?: { min: number; max: number; average: number };
    top_genres?: Array<{ genre: string; share: number }>;
    content_summaries?: Array<{ path: string; summary: string }>;
    transcript_excerpts?: Array<{ path: string; excerpt: string }>;
  };
  video?: {
    count?: number;
    total_duration_seconds?: number;
    average_duration_seconds?: number;
    longest_clip?: { path?: string; duration_seconds?: number };
    shortest_clip?: { path?: string; duration_seconds?: number };
    bitrate_stats?: { min: number; max: number; average: number };
    top_labels?: Array<{ label: string; share: number }>;
    content_summaries?: Array<{ path: string; summary: string }>;
  };
};

export type MediaListItem = {
  label: string;
  type?: string;
  analysis?: string;
  metadata?: Record<string, unknown>;
  path?: string;
  file_name?: string;
};

export type MediaAnalysisPayload = {
  summary?: MediaAnalysisSummary;
  metrics?: MediaAnalysisMetrics;
  insights?: string[];
  issues?: string[];
  assetItems?: MediaListItem[];
  briefingItems?: MediaListItem[];
};

type MediaAnalysisTabProps = {
  loading?: boolean;
  error?: string | null;
  mediaAnalysis?: MediaAnalysisPayload | null;
  onRetry?: () => void;
  useStore?: boolean;
};

export function MediaAnalysisTab({
  loading,
  error,
  mediaAnalysis,
  onRetry,
  useStore = false,
}: MediaAnalysisTabProps) {
  const scanData = useProjectPageStore(projectPageSelectors.scanData);
  const storeLoading = useProjectPageStore(projectPageSelectors.projectLoading);
  const storeError = useProjectPageStore(projectPageSelectors.projectError);
  const storeRetryLoadProject = useProjectPageStore(
    projectPageSelectors.retryLoadProject
  );

  const useStoreFallback = useStore;

  const resolvedLoading = loading ?? (useStoreFallback ? storeLoading : false);
  const resolvedError = error ?? (useStoreFallback ? storeError : null);
  const resolvedMediaAnalysis =
    mediaAnalysis ??
    (useStoreFallback ? resolveMediaAnalysis(scanData as Record<string, unknown>) : null);
  const resolvedRetry =
    onRetry ??
    (useStoreFallback && storeRetryLoadProject
      ? () => {
          void storeRetryLoadProject();
        }
      : undefined);

  if (resolvedLoading) {
    return <LoadingState message="Analyzing media…" />;
  }

  if (resolvedError) {
    return <ErrorState message={resolvedError} onRetry={resolvedRetry} />;
  }

  if (!resolvedMediaAnalysis) {
    return <EmptyState title="No media analysis available yet." description="Run analysis or add media assets to generate results." onRetry={resolvedRetry} />;
  }

  const hasSummaryData =
    Boolean(resolvedMediaAnalysis.summary) ||
    Boolean(resolvedMediaAnalysis.metrics) ||
    Boolean(resolvedMediaAnalysis.insights && resolvedMediaAnalysis.insights.length > 0) ||
    Boolean(resolvedMediaAnalysis.issues && resolvedMediaAnalysis.issues.length > 0);

  const hasListItems =
    Boolean(resolvedMediaAnalysis.assetItems && resolvedMediaAnalysis.assetItems.length > 0) ||
    Boolean(resolvedMediaAnalysis.briefingItems && resolvedMediaAnalysis.briefingItems.length > 0);

  if (!hasSummaryData && hasListItems) {
    return (
      <div className="space-y-6">
        {resolvedMediaAnalysis.assetItems && resolvedMediaAnalysis.assetItems.length > 0 && (
          <MediaAnalysisListSection title="Media Assets" items={resolvedMediaAnalysis.assetItems} />
        )}
        {resolvedMediaAnalysis.briefingItems && resolvedMediaAnalysis.briefingItems.length > 0 && (
          <MediaAnalysisListSection title="Media Briefings" items={resolvedMediaAnalysis.briefingItems} />
        )}
      </div>
    );
  }

  if (!hasSummaryData && !hasListItems) {
    return <EmptyState title="No media analysis available yet." description="Run analysis or add media assets to generate results." onRetry={resolvedRetry} />;
  }

  return <MediaAnalysisSummaryView payload={resolvedMediaAnalysis} />;
}

function MediaAnalysisListSection({ title, items }: { title: string; items: MediaListItem[] }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        <span className="text-xs text-muted-foreground">{items.length.toLocaleString()} items</span>
      </div>
      <MediaAnalysisList items={items} />
    </div>
  );
}

function MediaAnalysisList({ items }: { items: MediaListItem[] }) {
  if (items.length === 0) {
    return (
      <Card>
        <CardContent className="p-8 text-center text-sm text-muted-foreground">
          No media files analyzed.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {items.map((item, idx) => (
          <Card key={idx}>
            <CardContent className="p-5">
              <div className="flex items-start gap-3">
                <div className="mt-1 text-muted-foreground">
                  {item.type === "image" ? <FileImage size={18} /> : <Film size={18} />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="truncate text-sm font-medium text-foreground">
                    {item.label || item.file_name || item.path || "Untitled"}
                  </p>
                  {item.analysis && (
                    <p className="mt-1 text-xs text-muted-foreground">{item.analysis}</p>
                  )}
                  {item.metadata && (
                    <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                      {typeof item.metadata.duration === "number" && (
                        <span>Duration: {item.metadata.duration}s</span>
                      )}
                      {typeof item.metadata.duration === "string" && item.metadata.duration.trim() && (
                        <span>Duration: {item.metadata.duration}s</span>
                      )}
                      {typeof item.metadata.resolution === "string" && item.metadata.resolution.trim() && (
                        <span>{item.metadata.resolution}</span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
      ))}
    </div>
  );
}

function MediaAnalysisSummaryView({
  payload,
}: {
  payload: {
    summary?: MediaAnalysisSummary;
    metrics?: MediaAnalysisMetrics;
    insights?: string[];
    issues?: string[];
    assetItems?: MediaListItem[];
    briefingItems?: MediaListItem[];
  };
}) {
  const summary = payload.summary || {};
  const metrics = payload.metrics || {};

  const totalFiles =
    summary.total_media_files ??
    summary.total_files ??
    (summary.by_type?.images?.count || 0) +
      (summary.by_type?.videos?.count || 0) +
      (summary.by_type?.audio?.count || 0);

  const imageCount =
    summary.image_files ?? summary.by_type?.images?.count ?? metrics.images?.count ?? 0;
  const audioCount =
    summary.audio_files ?? summary.by_type?.audio?.count ?? metrics.audio?.count ?? 0;
  const videoCount =
    summary.video_files ?? summary.by_type?.videos?.count ?? metrics.video?.count ?? 0;

  const totalSize = summary.total_size_bytes ?? 0;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 items-start gap-3 md:grid-cols-4">
        <StatCard label="Total Media Files" value={totalFiles.toLocaleString()} />
        <StatCard label="Images" value={imageCount.toLocaleString()} />
        <StatCard label="Audio" value={audioCount.toLocaleString()} />
        <StatCard label="Video" value={videoCount.toLocaleString()} />
      </div>

      {totalSize > 0 && (
        <Card>
          <CardContent className="p-4 text-sm text-muted-foreground sm:p-4">
            Total media size: <span className="font-semibold text-foreground">{formatBytes(totalSize)}</span>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <MediaTypeCard
          title="Images"
          count={imageCount}
          details={[
            metrics.images?.average_width && metrics.images?.average_height
              ? `Avg resolution: ${Math.round(metrics.images.average_width)}x${Math.round(metrics.images.average_height)}`
              : null,
            metrics.images?.max_resolution?.dimensions
              ? `Largest: ${metrics.images.max_resolution.dimensions[0]}x${metrics.images.max_resolution.dimensions[1]}`
              : null,
            metrics.images?.common_aspect_ratios
              ? `Common ratios: ${Object.keys(metrics.images.common_aspect_ratios).slice(0, 3).join(", ")}`
              : null,
          ]}
          tags={(metrics.images?.top_labels || []).map(
            (label) => `${label.label} (${Math.round(label.share * 100)}%)`
          )}
          summaries={metrics.images?.content_summaries}
        />
        <MediaTypeCard
          title="Audio"
          count={audioCount}
          details={[
            metrics.audio?.total_duration_seconds
              ? `Total duration: ${formatDuration(metrics.audio.total_duration_seconds)}`
              : null,
            metrics.audio?.average_duration_seconds
              ? `Avg duration: ${formatDuration(metrics.audio.average_duration_seconds)}`
              : null,
            metrics.audio?.tempo_stats?.average
              ? `Avg tempo: ${Math.round(metrics.audio.tempo_stats.average)} BPM`
              : null,
          ]}
          tags={(metrics.audio?.top_genres || []).map(
            (genre) => `${genre.genre} (${Math.round(genre.share * 100)}%)`
          )}
          summaries={metrics.audio?.content_summaries}
        />
        <MediaTypeCard
          title="Video"
          count={videoCount}
          details={[
            metrics.video?.total_duration_seconds
              ? `Total duration: ${formatDuration(metrics.video.total_duration_seconds)}`
              : null,
            metrics.video?.average_duration_seconds
              ? `Avg duration: ${formatDuration(metrics.video.average_duration_seconds)}`
              : null,
            metrics.video?.longest_clip?.duration_seconds
              ? `Longest clip: ${formatDuration(metrics.video.longest_clip.duration_seconds)}`
              : null,
          ]}
          tags={(metrics.video?.top_labels || []).map(
            (label) => `${label.label} (${Math.round(label.share * 100)}%)`
          )}
          summaries={metrics.video?.content_summaries}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <InsightCard title="Insights" items={payload.insights} emptyLabel="No insights available yet." />
        <InsightCard title="Issues" items={payload.issues} emptyLabel="No issues detected." />
      </div>

      {payload.assetItems && payload.assetItems.length > 0 && (
        <MediaAnalysisListSection title="Media Assets" items={payload.assetItems} />
      )}
      {payload.briefingItems && payload.briefingItems.length > 0 && (
        <MediaAnalysisListSection title="Media Briefings" items={payload.briefingItems} />
      )}
    </div>
  );
}

function MediaTypeCard({
  title,
  count,
  details,
  tags,
  summaries,
}: {
  title: string;
  count: number;
  details: Array<string | null | undefined>;
  tags?: string[];
  summaries?: Array<{ path: string; summary: string }>;
}) {
  return (
    <Card>
      <CardHeader className="border-b border-border/70 p-5 pb-4 sm:p-5 sm:pb-4">
        <CardTitle className="text-sm font-semibold text-foreground">
          {title} ({count.toLocaleString()})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 p-5 pt-4 text-sm text-muted-foreground sm:p-5 sm:pt-4">
        <div className="space-y-1">
          {details.filter(Boolean).length === 0 ? (
            <p className="text-xs text-muted-foreground">No metrics available.</p>
          ) : (
            details.filter(Boolean).map((line, idx) => (
              <p key={idx}>{line}</p>
            ))
          )}
        </div>
        {tags && tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {tags.slice(0, 5).map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-border bg-muted px-2.5 py-1 text-xs text-foreground"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
        {summaries && summaries.length > 0 && (
          <div className="space-y-2">
            {summaries.slice(0, 3).map((entry) => (
              <div key={`${entry.path}-${entry.summary}`} className="text-xs text-muted-foreground">
                <span className="font-medium text-foreground">{entry.path}:</span>{" "}
                {entry.summary}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function InsightCard({
  title,
  items,
  emptyLabel,
}: {
  title: string;
  items?: string[];
  emptyLabel: string;
}) {
  return (
    <Card>
      <CardHeader className="border-b border-border/70 p-5 pb-4 sm:p-5 sm:pb-4">
        <CardTitle className="text-sm font-semibold text-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 p-5 pt-4 text-sm text-muted-foreground sm:p-5 sm:pt-4">
        {items && items.length > 0 ? (
          items.map((item, idx) => <p key={`${title}-${idx}`}>• {item}</p>)
        ) : (
          <p className="text-xs text-muted-foreground">{emptyLabel}</p>
        )}
      </CardContent>
    </Card>
  );
}

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds)) return "0s";
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${minutes}m ${remainder.toFixed(0)}s`;
}
