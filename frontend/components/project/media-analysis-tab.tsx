"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FileImage, Film } from "lucide-react";

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

export type MediaAnalysisPayload =
  | {
      summary?: MediaAnalysisSummary;
      metrics?: MediaAnalysisMetrics;
      insights?: string[];
      issues?: string[];
    }
  | Array<Record<string, any>>;

export function MediaAnalysisTab({
  loading,
  error,
  mediaAnalysis,
}: {
  loading: boolean;
  error: string | null;
  mediaAnalysis: MediaAnalysisPayload | null;
}) {
  if (loading) {
    return (
      <Card className="bg-white border border-gray-200">
        <CardContent className="p-10 text-center text-sm text-gray-500">
          Loading media analysis…
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="bg-white border border-gray-200">
        <CardContent className="p-10 text-center text-sm text-red-600">
          {error}
        </CardContent>
      </Card>
    );
  }

  if (!mediaAnalysis) {
    return <PlaceholderContent label="Media Analysis" />;
  }

  if (Array.isArray(mediaAnalysis)) {
    return <MediaAnalysisList items={mediaAnalysis} />;
  }

  return <MediaAnalysisSummaryView payload={mediaAnalysis} />;
}

function PlaceholderContent({ label }: { label: string }) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardContent className="p-12 text-center">
        <p className="text-gray-500 text-sm">{label} — This section will be available soon.</p>
      </CardContent>
    </Card>
  );
}

function MediaAnalysisList({ items }: { items: Array<Record<string, any>> }) {
  if (items.length === 0) {
    return (
      <Card className="bg-white border border-gray-200">
        <CardContent className="p-10 text-center text-sm text-gray-500">
          No media files analyzed.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {items.map((item, idx) => (
        <Card key={idx} className="bg-white border border-gray-200">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className="mt-1 text-gray-500">
                {item.type === "image" ? <FileImage size={18} /> : <Film size={18} />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {item.file_name || item.path || "Untitled"}
                </p>
                {item.analysis && (
                  <p className="text-xs text-gray-600 mt-1">{item.analysis}</p>
                )}
                {item.metadata && (
                  <div className="mt-2 text-xs text-gray-500 flex flex-wrap gap-2">
                    {item.metadata.duration && (
                      <span>Duration: {item.metadata.duration}s</span>
                    )}
                    {item.metadata.resolution && <span>{item.metadata.resolution}</span>}
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
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Total Media Files" value={totalFiles.toLocaleString()} />
        <StatCard label="Images" value={imageCount.toLocaleString()} />
        <StatCard label="Audio" value={audioCount.toLocaleString()} />
        <StatCard label="Video" value={videoCount.toLocaleString()} />
      </div>

      {totalSize > 0 && (
        <Card className="bg-white border border-gray-200">
          <CardContent className="p-4 text-sm text-gray-600">
            Total media size: <span className="font-semibold text-gray-900">{formatBytes(totalSize)}</span>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <InsightCard title="Insights" items={payload.insights} emptyLabel="No insights available yet." />
        <InsightCard title="Issues" items={payload.issues} emptyLabel="No issues detected." />
      </div>
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
    <Card className="bg-white border border-gray-200">
      <CardHeader className="border-b border-gray-200">
        <CardTitle className="text-sm font-semibold text-gray-900">
          {title} ({count.toLocaleString()})
        </CardTitle>
      </CardHeader>
      <CardContent className="p-4 space-y-3 text-sm text-gray-600">
        <div className="space-y-1">
          {details.filter(Boolean).length === 0 ? (
            <p className="text-xs text-gray-400">No metrics available.</p>
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
                className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
        {summaries && summaries.length > 0 && (
          <div className="space-y-2">
            {summaries.slice(0, 3).map((entry) => (
              <div key={`${entry.path}-${entry.summary}`} className="text-xs text-gray-500">
                <span className="font-medium text-gray-700">{entry.path}:</span>{" "}
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
    <Card className="bg-white border border-gray-200">
      <CardHeader className="border-b border-gray-200">
        <CardTitle className="text-sm font-semibold text-gray-900">{title}</CardTitle>
      </CardHeader>
      <CardContent className="p-4 text-sm text-gray-600 space-y-2">
        {items && items.length > 0 ? (
          items.map((item, idx) => <p key={`${title}-${idx}`}>• {item}</p>)
        ) : (
          <p className="text-xs text-gray-400">{emptyLabel}</p>
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

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardContent className="p-4">
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-lg font-semibold text-gray-900 mt-1">{value}</p>
      </CardContent>
    </Card>
  );
}
