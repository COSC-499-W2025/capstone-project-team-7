"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/input";
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
    router.push(`/project?id=${projectId}`);
  };

  // Format file size
  const formatSize = (bytes?: number) => {
    if (!bytes) return "";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="p-8">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        {/* Header */}
        <div className="px-8 py-6 border-b border-gray-200">
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
            Search
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            Search across your projects and files
          </p>
        </div>

        {/* Search Controls */}
        <div className="p-8">
          <div className="flex flex-col sm:flex-row gap-4 mb-6">
            {/* Search Input */}
            <div className="flex-1">
              <Input
                type="search"
                placeholder="Search projects, files, skills..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                className="w-full"
              />
            </div>

            {/* Scope Filter */}
            <Select
              value={scope}
              onValueChange={(value) =>
                setScope(value as "all" | "files" | "skills")
              }
            >
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Scope" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="files">Files</SelectItem>
                <SelectItem value="skills">Skills</SelectItem>
              </SelectContent>
            </Select>

            {/* Skill Filter */}
            <Select value={selectedSkill} onValueChange={setSelectedSkill}>
              <SelectTrigger className="w-[180px]">
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

            {/* Search Button */}
            <Button
              onClick={handleSearch}
              disabled={loading || !query.trim()}
              className="bg-gray-900 text-white hover:bg-gray-800"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
              <span className="ml-2">Search</span>
            </Button>
          </div>

          {/* Error State */}
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg mb-6">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {/* Results Header */}
          {hasSearched && !loading && (
            <div className="mb-4 text-sm text-gray-600">
              {filteredResults.length === 0
                ? "No results found"
                : `Found ${filteredResults.length} result${filteredResults.length === 1 ? "" : "s"}${selectedSkill !== "all" ? ` (filtered from ${total})` : ""}`}
            </div>
          )}

          {/* Loading State */}
          {loading && (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
              <span className="ml-3 text-gray-500">Searching...</span>
            </div>
          )}

          {/* Results List */}
          {!loading && filteredResults.length > 0 && (
            <div className="space-y-3">
              {filteredResults.map((item, idx) => (
                <div
                  key={`${item.project_id}-${item.type}-${idx}`}
                  className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => handleResultClick(item.project_id)}
                >
                  <div className="flex items-start gap-3">
                    {/* Icon */}
                    <div className="flex-shrink-0 mt-0.5">
                      {item.type === "file" ? (
                        <FileText className="h-5 w-5 text-blue-500" />
                      ) : (
                        <Sparkles className="h-5 w-5 text-amber-500" />
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      {item.type === "file" ? (
                        <>
                          <p className="font-medium text-gray-900 truncate">
                            {item.name || item.path?.split("/").pop() || "Unknown file"}
                          </p>
                          <p className="text-sm text-gray-600 truncate">
                            {item.path}
                          </p>
                          <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
                            <span>{item.project_name}</span>
                            {item.size_bytes && (
                              <>
                                <span>•</span>
                                <span>{formatSize(item.size_bytes)}</span>
                              </>
                            )}
                            {item.mime_type && (
                              <>
                                <span>•</span>
                                <span>{item.mime_type}</span>
                              </>
                            )}
                          </div>
                        </>
                      ) : (
                        <>
                          <p className="font-medium text-gray-900">
                            {item.skill}
                          </p>
                          <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
                            <span>{item.project_name}</span>
                            {item.category && (
                              <>
                                <span>•</span>
                                <span className="capitalize">{item.category}</span>
                              </>
                            )}
                            {item.proficiency && (
                              <>
                                <span>•</span>
                                <span>{item.proficiency}</span>
                              </>
                            )}
                          </div>
                        </>
                      )}
                    </div>

                    {/* Type Badge */}
                    <div className="flex-shrink-0">
                      <span
                        className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full ${
                          item.type === "file"
                            ? "bg-blue-100 text-blue-700"
                            : "bg-amber-100 text-amber-700"
                        }`}
                      >
                        {item.type === "file" ? "File" : "Skill"}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Empty State */}
          {!loading && hasSearched && filteredResults.length === 0 && (
            <div className="text-center py-16">
              <Search className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No results found</p>
              <p className="text-sm text-gray-400 mt-1">
                Try a different search term or adjust your filters
              </p>
            </div>
          )}

          {/* Initial State */}
          {!loading && !hasSearched && (
            <div className="text-center py-16">
              <Search className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">Enter a search term to get started</p>
              <p className="text-sm text-gray-400 mt-1">
                Search by file name, project name, or skill
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
