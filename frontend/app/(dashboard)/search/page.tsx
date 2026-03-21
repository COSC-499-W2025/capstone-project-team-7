"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Loader2, Search, FileText, Sparkles } from "lucide-react";
import { getStoredToken } from "@/lib/auth";
import { searchProjects, getSkills } from "@/lib/api/projects";
import { SearchResultItem } from "@/types/project";
import { SearchInput } from "@/components/ui/search-input";

export default function SearchPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [scope, setScope] = useState<"all" | "files" | "skills">("all");
  const [selectedSkill, setSelectedSkill] = useState<string>("all");
  const [skills, setSkills] = useState<string[]>([]);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [skillsLoading, setSkillsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  // Fetch skills for filter dropdown on mount
  useEffect(() => {
    const fetchSkills = async () => {
      const token = getStoredToken();
      if (!token) {
        setSkillsLoading(false);
        return;
      }

      try {
        const response = await getSkills(token);
        setSkills(response.skills);
      } catch (err) {
        console.error("Failed to fetch skills:", err);
      } finally {
        setSkillsLoading(false);
      }
    };

    fetchSkills();
  }, []);

  // Perform search
  const handleSearch = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      setError("Not authenticated. Please log in through Settings.");
      return;
    }

    if (!query.trim()) {
      setResults([]);
      setTotal(0);
      setHasSearched(false);
      return;
    }

    setLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      const response = await searchProjects(token, query, { scope });
      setResults(response.items);
      setTotal(response.page.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setResults([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [query, scope]);

  // Handle Enter key in search input
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  // Filter results by skill (client-side)
  const filteredResults =
    selectedSkill === "all"
      ? results
      : results.filter(
          (item) => item.type === "skill" && item.skill === selectedSkill
        );

  // Navigate to project detail
  const handleResultClick = (projectId: string) => {
    router.push(`/project?projectId=${projectId}`);
  };

  // Format file size
  const formatSize = (bytes?: number) => {
    if (!bytes) return "";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="page-container">
      <section className="page-card page-hero">
        <div className="page-header">
          <p className="page-kicker">Cross-Project Discovery</p>
          <h1 className="text-foreground">Search</h1>
          <p className="page-summary mt-3">
            Search across projects, file paths, and extracted skills from one streamlined discovery surface.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="dashboard-chip">{skills.length} indexed skill{skills.length === 1 ? "" : "s"}</span>
            <span className="dashboard-chip">Scope-aware search</span>
            <span className="dashboard-chip">Project jump links</span>
          </div>
        </div>
      </section>

        <section className="page-card page-body">
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1.2fr)_minmax(300px,0.8fr)]">
            <div className="space-y-4">
              <div className="rounded-[22px] border border-border bg-muted/35 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                  Query Builder
                </p>
                <div className="mt-3 flex flex-col gap-4 sm:flex-row">
                  <div className="flex-1">
                    <SearchInput
                      value={query}
                      onChange={setQuery}
                      onKeyDown={handleKeyDown}
                      onClear={() => {
                        setQuery("");
                        setHasSearched(false);
                        setResults([]);
                        setTotal(0);
                      }}
                      placeholder="Search projects, files, skills..."
                    />
                  </div>

                  <Select
                    value={scope}
                    onValueChange={(value) =>
                      setScope(value as "all" | "files" | "skills")
                    }
                  >
                    <SelectTrigger className="w-full sm:w-[160px]">
                      <SelectValue placeholder="Scope" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="files">Files</SelectItem>
                      <SelectItem value="skills">Skills</SelectItem>
                    </SelectContent>
                  </Select>

                  <Select value={selectedSkill} onValueChange={setSelectedSkill}>
                    <SelectTrigger className="w-full sm:w-[220px]">
                      <SelectValue placeholder="Filter by skill" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Skills</SelectItem>
                      {skillsLoading ? (
                        <SelectItem value="loading" disabled>
                          Loading...
                        </SelectItem>
                      ) : (
                        skills.map((skill) => (
                          <SelectItem key={skill} value={skill}>
                            {skill}
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>

                  <Button
                    onClick={handleSearch}
                    onKeyDown={handleKeyDown}
                    disabled={loading || !query.trim()}
                    className="sm:min-w-[132px]"
                  >
                    {loading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Search className="h-4 w-4" />
                    )}
                    <span>Search</span>
                  </Button>
                </div>
              </div>

              {error && (
                <div className="alert alert-error">
                  <p className="text-sm">{error}</p>
                </div>
              )}

              {hasSearched && !loading && (
                <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                  <span className="dashboard-chip">
                    {filteredResults.length === 0
                      ? "No results found"
                      : `${filteredResults.length} result${filteredResults.length === 1 ? "" : "s"}`}
                  </span>
                  {selectedSkill !== "all" && (
                    <span className="dashboard-chip">Filtered from {total}</span>
                  )}
                </div>
              )}

              {loading && (
                <div className="flex items-center justify-center rounded-[22px] border border-border bg-muted/30 py-20">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                  <span className="ml-3 text-muted-foreground">Searching...</span>
                </div>
              )}

              {!loading && filteredResults.length > 0 && (
                <div className="space-y-3">
                  {filteredResults.map((item, idx) => (
                    <div
                      key={`${item.project_id}-${item.type}-${idx}`}
                      className="rounded-[22px] border border-border bg-card/90 p-5 shadow-[0_16px_36px_rgba(15,23,42,0.06)] transition-[transform,border-color,background-color] hover:-translate-y-0.5 hover:border-primary/20 hover:bg-background"
                      onClick={() => handleResultClick(item.project_id)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          handleResultClick(item.project_id);
                        }
                      }}
                      role="button"
                      tabIndex={0}
                    >
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5 flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-2xl border border-border bg-muted/60">
                          {item.type === "file" ? (
                            <FileText className="h-5 w-5 text-foreground" />
                          ) : (
                            <Sparkles className="h-5 w-5 text-muted-foreground" />
                          )}
                        </div>

                        <div className="flex-1 min-w-0">
                          {item.type === "file" ? (
                            <>
                              <div className="flex flex-wrap items-center gap-2">
                                <p className="truncate font-semibold text-foreground">
                                  {item.name || item.path?.split("/").pop() || "Unknown file"}
                                </p>
                                <span className="rounded-full border border-border bg-muted px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                  File
                                </span>
                              </div>
                              <p className="mt-1 truncate text-sm text-muted-foreground">
                                {item.path}
                              </p>
                              <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                                <span className="dashboard-chip">{item.project_name}</span>
                                {item.size_bytes && <span className="dashboard-chip">{formatSize(item.size_bytes)}</span>}
                                {item.mime_type && <span className="dashboard-chip">{item.mime_type}</span>}
                              </div>
                            </>
                          ) : (
                            <>
                              <div className="flex flex-wrap items-center gap-2">
                                <p className="font-semibold text-foreground">{item.skill}</p>
                                <span className="rounded-full border border-primary/15 bg-primary/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-[hsl(var(--accent-foreground))]">
                                  Skill
                                </span>
                              </div>
                              <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                                <span className="dashboard-chip">{item.project_name}</span>
                                {item.category && <span className="dashboard-chip capitalize">{item.category}</span>}
                                {item.proficiency && <span className="dashboard-chip">{item.proficiency}</span>}
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {!loading && hasSearched && filteredResults.length === 0 && (
                <div className="rounded-[24px] border border-dashed border-border bg-background/75 py-16 text-center shadow-[inset_0_1px_0_rgba(255,255,255,0.65)]">
                  <Search className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
                  <p className="text-base font-medium text-foreground">No results found</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Try a different search term or adjust your filters.
                  </p>
                </div>
              )}

              {!loading && !hasSearched && (
                <div className="rounded-[24px] border border-dashed border-border bg-background/75 py-16 text-center shadow-[inset_0_1px_0_rgba(255,255,255,0.65)]">
                  <Search className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
                  <p className="text-base font-medium text-foreground">Enter a search term to get started</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Search by file name, path, project name, or skill.
                  </p>
                </div>
              )}
            </div>

            <div className="grid gap-3">
              <div className="info-tile">
                <p className="info-tile-kicker">Search Tips</p>
                <p className="mt-3 text-base font-semibold text-foreground">Use short, precise terms</p>
                <p className="mt-2 text-sm text-muted-foreground">Search by filename fragments, technology names, or notable capabilities.</p>
              </div>
              <div className="info-tile">
                <p className="info-tile-kicker">Filters</p>
                <p className="mt-3 text-base font-semibold text-foreground">Scope narrows noise</p>
                <p className="mt-2 text-sm text-muted-foreground">Switch between files and skills when you want either raw evidence or extracted expertise.</p>
              </div>
              <div className="info-tile">
                <p className="info-tile-kicker">Navigation</p>
                <p className="mt-3 text-base font-semibold text-foreground">Jump directly into a project</p>
                <p className="mt-2 text-sm text-muted-foreground">Each result opens the corresponding project detail view without changing the underlying search data.</p>
              </div>
            </div>
          </div>
      </section>
    </div>
  );
}
