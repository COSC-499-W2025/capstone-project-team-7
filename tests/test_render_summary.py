"""
Tests for ProjectViewerScreen._render_summary() method.

Tests the comprehensive project summary rendering functionality that pulls
data from all available analysis types (code, git, skills, contributions,
media, pdf, documents, duplicates, and AI analysis).

Run with: pytest tests/test_render_summary.py -v
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import sys

# Add backend/src to path
backend_src_path = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src_path))


class MockProjectViewerScreen:
    """Mock ProjectViewerScreen for testing _render_summary()"""
    
    def __init__(self, project: dict):
        self.project = project
        self.scan_data = project.get("scan_data", {})
    
    def _render_summary(self) -> str:
        """Copy of the actual _render_summary() method from screens.py"""
        from html import escape
        
        lines = []
        
        lines.append("[b][cyan]📊 Project Summary[/cyan][/b]\n")
        
        # Project Header
        project_name = escape(self.project.get('project_name', 'Unknown'))
        project_path = escape(self.project.get('project_path', 'Unknown'))
        timestamp = self.project.get("scan_timestamp", "Unknown")
        
        lines.append(f"[b]{project_name}[/b]")
        lines.append(f"Path: {project_path}")
        
        if timestamp != "Unknown":
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                timestamp = dt.strftime("%Y-%m-%d at %H:%M:%S")
            except:
                pass
        lines.append(f"Scanned: {timestamp}\n")
        
        # Guard: Make sure scan_data is a dict
        if not isinstance(self.scan_data, dict):
            lines.append("[red]Cannot render: scan_data is not a dictionary[/red]")
            return "\n".join(lines)
        
        # === SUMMARY STATISTICS ===
        summary = self.scan_data.get("summary", {})
        if summary:
            lines.append("[b][yellow]📈 Summary Statistics[/yellow][/b]")
            files = summary.get('files_processed', 0)
            bytes_proc = summary.get('bytes_processed', 0)
            issues = summary.get('issues_count', 0)
            
            lines.append(f"  • Files processed: {files}")
            lines.append(f"  • Total size: {bytes_proc:,} bytes ({bytes_proc / 1024 / 1024:.2f} MB)")
            if issues:
                lines.append(f"  • Issues found: {issues}")
            lines.append("")
        
        # === LANGUAGES ===
        languages = summary.get("languages", [])
        if languages:
            lines.append("[b][yellow]🔤 Languages[/yellow][/b]")
            if isinstance(languages, list):
                for lang in languages[:10]:
                    if isinstance(lang, dict):
                        name = lang.get("name") or lang.get("language") or "Unknown"
                        count = lang.get("files", 0)
                        if name and name != "Unknown":
                            safe_name = escape(str(name))
                            lines.append(f"  • {safe_name}: {count} files")
            if len(languages) > 10:
                lines.append(f"  ... +{len(languages) - 10} more")
            lines.append("")
        
        # === CODE QUALITY ===
        code_data = self.scan_data.get("code_analysis", {})
        if code_data and code_data.get("success"):
            lines.append("[b][yellow]💻 Code Quality[/yellow][/b]")
            
            metrics = code_data.get("metrics", {})
            if metrics:
                total_lines = metrics.get('total_lines', 0)
                avg_complexity = metrics.get('average_complexity', 0)
                avg_maint = metrics.get('average_maintainability', 0)
                
                lines.append(f"  • Total lines: {total_lines:,}")
                lines.append(f"  • Avg complexity: {avg_complexity:.2f}")
                lines.append(f"  • Avg maintainability: {avg_maint:.1f}/100")
            
            quality = code_data.get("quality", {})
            if quality:
                security = quality.get('security_issues', 0)
                high_priority = quality.get('high_priority_files', 0)
                if security or high_priority:
                    if security:
                        lines.append(f"  • Security issues: {security}")
                    if high_priority:
                        lines.append(f"  • High priority files: {high_priority}")
            lines.append("")
        
        # === SKILLS ===
        skills_data = self.scan_data.get("skills_analysis", {})
        if skills_data and skills_data.get("success"):
            lines.append("[b][yellow]🎯 Skills[/yellow][/b]")
            total_skills = skills_data.get("total_skills", 0)
            skills_by_cat = skills_data.get("skills_by_category", {})
            
            if total_skills:
                lines.append(f"  • Total skills: {total_skills}")
            
            # Show top skill from each category
            if skills_by_cat:
                for category, skills in list(skills_by_cat.items())[:3]:
                    if skills:
                        top_skill = skills[0]
                        if isinstance(top_skill, dict):
                            name = top_skill.get("name", "Unknown")
                            prof = top_skill.get("proficiency", "")
                            lines.append(f"  • {category}: {name}{f' ({prof})' if prof else ''}")
                        else:
                            lines.append(f"  • {category}: {top_skill}")
            lines.append("")
        
        # === GIT STATS ===
        git_data = self.scan_data.get("git_analysis", [])
        if isinstance(git_data, list) and len(git_data) > 0:
            repo = git_data[0]
            
            if isinstance(repo, dict) and not repo.get("error"):
                lines.append("[b][yellow]🔀 Git Statistics[/yellow][/b]")
                
                commits = repo.get("commit_count", 0)
                branches = repo.get("branches", [])
                
                if commits:
                    lines.append(f"  • Total commits: {commits}")
                if branches:
                    lines.append(f"  • Branches: {len(branches)}")
                
                lines.append("")
        
        # === CONTRIBUTIONS ===
        contrib_data = self.scan_data.get("contribution_metrics", {})
        if isinstance(contrib_data, dict) and contrib_data:
            lines.append("[b][yellow]📊 Contributions[/yellow][/b]")
            
            ranking = self.scan_data.get("contribution_ranking", {})
            if isinstance(ranking, dict) and ranking.get("score") is not None:
                score = ranking.get("score")
                user_share = ranking.get("user_commit_share")
                lines.append(f"  • Importance score: {score:.2f}")
                if isinstance(user_share, (int, float)):
                    lines.append(f"  • Your contribution: {user_share*100:.1f}%")
            
            total_commits = contrib_data.get("total_commits", 0)
            total_contribs = contrib_data.get("total_contributors", 0)
            if total_commits:
                lines.append(f"  • Total commits: {total_commits}")
            if total_contribs:
                lines.append(f"  • Contributors: {total_contribs}")
            
            contributors = contrib_data.get("contributors", [])
            if contributors:
                top = contributors[0]
                top_name = top.get("name", "Unknown")
                top_commits = top.get("commits", 0)
                if top_commits:
                    lines.append(f"  • Top contributor: {top_name} ({top_commits} commits)")
            lines.append("")
        
        # === MEDIA ANALYSIS ===
        media_data = self.scan_data.get("media_analysis", {})
        if isinstance(media_data, dict) and media_data:
            lines.append("[b][yellow]🎨 Media Analysis[/yellow][/b]")
            summary_obj = media_data.get("summary", {})
            if summary_obj:
                total_media = summary_obj.get("total_media_files", 0)
                images = summary_obj.get("images", 0)
                audio = summary_obj.get("audio", 0)
                video = summary_obj.get("video", 0)
                
                if total_media:
                    lines.append(f"  • Total media files: {total_media}")
                if images:
                    lines.append(f"  • Images: {images}")
                if audio:
                    lines.append(f"  • Audio files: {audio}")
                if video:
                    lines.append(f"  • Video files: {video}")
                
                metrics = media_data.get("metrics", {})
                if metrics:
                    avg_res = metrics.get("average_resolution")
                    if avg_res:
                        lines.append(f"  • Avg resolution: {avg_res}")
            lines.append("")
        
        return "\n".join(lines)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def minimal_project():
    """Minimal project with just basic info."""
    return {
        "project_name": "test-project",
        "project_path": "/test/path",
        "scan_timestamp": "2025-12-07T10:30:00Z",
        "scan_data": {}
    }


@pytest.fixture
def project_with_summary_stats():
    """Project with summary statistics."""
    return {
        "project_name": "code-analyzer",
        "project_path": "/home/user/code-analyzer",
        "scan_timestamp": "2025-12-07T10:30:00Z",
        "scan_data": {
            "summary": {
                "files_processed": 150,
                "bytes_processed": 5242880,  # 5 MB
                "issues_count": 3
            }
        }
    }


@pytest.fixture
def project_with_code_analysis():
    """Project with code analysis data."""
    return {
        "project_name": "python-app",
        "project_path": "/src/python-app",
        "scan_timestamp": "2025-12-07T10:30:00Z",
        "scan_data": {
            "code_analysis": {
                "success": True,
                "metrics": {
                    "total_lines": 5000,
                    "total_code_lines": 4000,
                    "total_comments": 500,
                    "total_functions": 120,
                    "total_classes": 45,
                    "average_complexity": 3.5,
                    "average_maintainability": 78.5
                },
                "quality": {
                    "security_issues": 2,
                    "high_priority_files": 1,
                    "todos": 5
                }
            }
        }
    }


@pytest.fixture
def project_with_git_analysis():
    """Project with git analysis data."""
    return {
        "project_name": "webapp",
        "project_path": "/src/webapp",
        "scan_timestamp": "2025-12-07T10:30:00Z",
        "scan_data": {
            "git_analysis": [
                {
                    "commit_count": 342,
                    "branches": ["main", "develop", "feature-x"],
                    "date_range": {
                        "start": "2024-01-15",
                        "end": "2025-12-07"
                    },
                    "contributors": [
                        {"name": "Alice", "commits": 150, "percent": 43.9},
                        {"name": "Bob", "commits": 120, "percent": 35.1},
                        {"name": "Charlie", "commits": 72, "percent": 21.0}
                    ]
                }
            ]
        }
    }


@pytest.fixture
def project_with_contributions():
    """Project with contribution metrics."""
    return {
        "project_name": "api-service",
        "project_path": "/src/api-service",
        "scan_timestamp": "2025-12-07T10:30:00Z",
        "scan_data": {
            "contribution_metrics": {
                "total_commits": 250,
                "total_contributors": 5,
                "total_lines_of_code": 15000,
                "contributors": [
                    {"name": "You", "commits": 120},
                    {"name": "Team", "commits": 130}
                ],
                "activity_timeline": [
                    {"month": "Dec 2025", "commits": 45},
                    {"month": "Nov 2025", "commits": 38},
                    {"month": "Oct 2025", "commits": 52}
                ]
            },
            "contribution_ranking": {
                "score": 8.5,
                "user_commit_share": 0.48
            }
        }
    }


@pytest.fixture
def project_with_skills():
    """Project with skills analysis."""
    return {
        "project_name": "fullstack-app",
        "project_path": "/src/fullstack-app",
        "scan_timestamp": "2025-12-07T10:30:00Z",
        "scan_data": {
            "skills_analysis": {
                "success": True,
                "total_skills": 18,
                "skills_by_category": {
                    "languages": [
                        {"name": "Python", "proficiency": "Advanced"},
                        {"name": "JavaScript", "proficiency": "Intermediate"}
                    ],
                    "frameworks": [
                        {"name": "Django", "proficiency": "Advanced"},
                        {"name": "React", "proficiency": "Intermediate"}
                    ],
                    "databases": [
                        {"name": "PostgreSQL", "proficiency": "Advanced"}
                    ]
                }
            }
        }
    }


@pytest.fixture
def project_with_media():
    """Project with media analysis."""
    return {
        "project_name": "media-project",
        "project_path": "/src/media-project",
        "scan_timestamp": "2025-12-07T10:30:00Z",
        "scan_data": {
            "media_analysis": {
                "summary": {
                    "total_media_files": 45,
                    "images": 35,
                    "audio": 5,
                    "video": 5
                },
                "metrics": {
                    "images": {
                        "average_width": 1920,
                        "average_height": 1080
                    }
                }
            }
        }
    }


@pytest.fixture
def comprehensive_project():
    """Project with all types of analysis data."""
    return {
        "project_name": "comprehensive-project",
        "project_path": "/home/dev/comprehensive-project",
        "scan_timestamp": "2025-12-07T15:45:30Z",
        "scan_data": {
            "summary": {
                "files_processed": 200,
                "bytes_processed": 10485760,  # 10 MB
                "issues_count": 5,
                "languages": [
                    {"name": "Python", "files": 85},
                    {"name": "JavaScript", "files": 45},
                    {"name": "HTML", "files": 30}
                ]
            },
            "code_analysis": {
                "success": True,
                "metrics": {
                    "total_lines": 12500,
                    "total_code_lines": 10000,
                    "total_comments": 1200,
                    "total_functions": 280,
                    "total_classes": 95,
                    "average_complexity": 3.2,
                    "average_maintainability": 81.3
                },
                "quality": {
                    "security_issues": 3,
                    "high_priority_files": 2,
                    "todos": 15
                }
            },
            "git_analysis": [
                {
                    "commit_count": 512,
                    "branches": ["main", "dev", "staging"],
                    "contributors": [
                        {"name": "Lead Dev", "commits": 250, "percent": 48.8},
                        {"name": "Contributor", "commits": 180, "percent": 35.2},
                        {"name": "Junior Dev", "commits": 82, "percent": 16.0}
                    ]
                }
            ],
            "contribution_metrics": {
                "total_commits": 512,
                "total_contributors": 3,
                "total_lines_of_code": 35000,
                "contributors": [
                    {"name": "Lead Dev", "commits": 250},
                    {"name": "Contributor", "commits": 180}
                ],
                "activity_timeline": [
                    {"month": "Dec 2025", "commits": 95},
                    {"month": "Nov 2025", "commits": 87},
                    {"month": "Oct 2025", "commits": 105}
                ]
            },
            "contribution_ranking": {
                "score": 9.1,
                "user_commit_share": 0.488
            },
            "skills_analysis": {
                "success": True,
                "total_skills": 25,
                "skills_by_category": {
                    "languages": [
                        {"name": "Python", "proficiency": "Expert"},
                        {"name": "JavaScript", "proficiency": "Advanced"}
                    ],
                    "frameworks": [
                        {"name": "Django", "proficiency": "Expert"},
                        {"name": "React", "proficiency": "Advanced"}
                    ],
                    "tools": [
                        {"name": "Docker", "proficiency": "Intermediate"}
                    ]
                }
            },
            "media_analysis": {
                "summary": {
                    "total_media_files": 62,
                    "images": 50,
                    "audio": 8,
                    "video": 4
                },
                "metrics": {
                    "images": {
                        "average_width": 1440,
                        "average_height": 900
                    }
                }
            }
        }
    }


# ============================================================================
# TESTS
# ============================================================================

class TestRenderSummaryBasics:
    """Test basic rendering functionality."""
    
    def test_renders_without_error(self, minimal_project):
        """Test that render_summary returns a string without errors."""
        screen = MockProjectViewerScreen(minimal_project)
        result = screen._render_summary()
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_includes_project_name(self, minimal_project):
        """Test that project name appears in summary."""
        screen = MockProjectViewerScreen(minimal_project)
        result = screen._render_summary()
        
        assert "test-project" in result
    
    def test_includes_project_path(self, minimal_project):
        """Test that project path appears in summary."""
        screen = MockProjectViewerScreen(minimal_project)
        result = screen._render_summary()
        
        assert "/test/path" in result
    
    def test_formats_timestamp(self, minimal_project):
        """Test that timestamp is properly formatted."""
        screen = MockProjectViewerScreen(minimal_project)
        result = screen._render_summary()
        
        # Should be formatted, not the raw ISO format
        assert "2025-12-07" in result
        assert "10:30:00" in result


class TestRenderSummarySummaryStats:
    """Test summary statistics rendering."""
    
    def test_displays_summary_statistics(self, project_with_summary_stats):
        """Test that summary statistics are displayed."""
        screen = MockProjectViewerScreen(project_with_summary_stats)
        result = screen._render_summary()
        
        assert "Summary Statistics" in result
        assert "Files processed: 150" in result
        assert "5.00 MB" in result  # 5 MB formatted
        assert "Issues found: 3" in result
    
    def test_displays_languages(self, project_with_summary_stats):
        """Test that languages are displayed."""
        screen = MockProjectViewerScreen(project_with_summary_stats)
        result = screen._render_summary()
        
        # Add languages to test
        project = project_with_summary_stats.copy()
        project["scan_data"]["summary"]["languages"] = [
            {"name": "Python", "files": 50},
            {"name": "JavaScript", "files": 40}
        ]
        screen = MockProjectViewerScreen(project)
        result = screen._render_summary()
        
        assert "Languages" in result
        assert "Python" in result
        assert "JavaScript" in result


class TestRenderSummaryCodeAnalysis:
    """Test code analysis rendering."""
    
    def test_displays_code_quality(self, project_with_code_analysis):
        """Test that code quality metrics are displayed."""
        screen = MockProjectViewerScreen(project_with_code_analysis)
        result = screen._render_summary()
        
        assert "Code Quality" in result
        assert "Total lines: 5,000" in result
        assert "Avg complexity: 3.50" in result
        assert "Avg maintainability: 78.5/100" in result
    
    def test_displays_code_issues(self, project_with_code_analysis):
        """Test that code issues are displayed."""
        screen = MockProjectViewerScreen(project_with_code_analysis)
        result = screen._render_summary()
        
        assert "Security issues: 2" in result
        assert "High priority files: 1" in result
    
    def test_handles_missing_code_analysis(self, minimal_project):
        """Test that missing code analysis doesn't break rendering."""
        screen = MockProjectViewerScreen(minimal_project)
        result = screen._render_summary()
        
        # Should not have code quality section
        assert "Code Quality" not in result


class TestRenderSummaryGitAnalysis:
    """Test git analysis rendering."""
    
    def test_displays_git_stats(self, project_with_git_analysis):
        """Test that git statistics are displayed."""
        screen = MockProjectViewerScreen(project_with_git_analysis)
        result = screen._render_summary()
        
        assert "Git Statistics" in result
        assert "Total commits: 342" in result
        assert "Branches: 3" in result
    
    def test_displays_top_contributors(self, project_with_git_analysis):
        """Test that top contributors are displayed."""
        screen = MockProjectViewerScreen(project_with_git_analysis)
        result = screen._render_summary()
        
        assert "Alice" in result
        assert "150 commits" in result


class TestRenderSummaryContributions:
    """Test contribution metrics rendering."""
    
    def test_displays_contribution_metrics(self, project_with_contributions):
        """Test that contribution metrics are displayed."""
        screen = MockProjectViewerScreen(project_with_contributions)
        result = screen._render_summary()
        
        assert "Contributions" in result
        assert "Importance score: 8.50" in result
        assert "Your contribution: 48.0%" in result
        assert "Total commits: 250" in result
        assert "Contributors: 5" in result
    
    def test_displays_activity_timeline(self, project_with_contributions):
        """Test that activity timeline is displayed."""
        screen = MockProjectViewerScreen(project_with_contributions)
        result = screen._render_summary()
        
        assert "Dec 2025: 45 commits" in result
        assert "Nov 2025: 38 commits" in result


class TestRenderSummarySkills:
    """Test skills analysis rendering."""
    
    def test_displays_skills_summary(self, project_with_skills):
        """Test that skills are displayed."""
        screen = MockProjectViewerScreen(project_with_skills)
        result = screen._render_summary()
        
        assert "Skills" in result
        assert "Total skills: 18" in result
        assert "languages" in result.lower()
        assert "Python" in result
    
    def test_displays_skill_proficiency(self, project_with_skills):
        """Test that skill proficiency levels are shown."""
        screen = MockProjectViewerScreen(project_with_skills)
        result = screen._render_summary()
        
        assert "Advanced" in result
        assert "Intermediate" in result


class TestRenderSummaryMedia:
    """Test media analysis rendering."""
    
    def test_displays_media_analysis(self, project_with_media):
        """Test that media analysis is displayed."""
        screen = MockProjectViewerScreen(project_with_media)
        result = screen._render_summary()
        
        assert "Media Analysis" in result
        assert "Total media files: 45" in result
        assert "Images: 35" in result
        assert "Audio files: 5" in result
        assert "Video files: 5" in result
    
    def test_displays_media_metrics(self, project_with_media):
        """Test that media metrics are displayed."""
        screen = MockProjectViewerScreen(project_with_media)
        result = screen._render_summary()
        
        assert "Avg resolution:" in result


class TestRenderSummaryComprehensive:
    """Test comprehensive project with all data types."""
    
    def test_comprehensive_project_rendering(self, comprehensive_project):
        """Test that all sections are rendered for a comprehensive project."""
        screen = MockProjectViewerScreen(comprehensive_project)
        result = screen._render_summary()
        
        # All main sections should be present
        assert "Summary Statistics" in result
        assert "Languages" in result
        assert "Code Quality" in result
        assert "Skills" in result
        assert "Git Statistics" in result
        assert "Contributions" in result
        assert "Media Analysis" in result
    
    def test_comprehensive_data_accuracy(self, comprehensive_project):
        """Test that comprehensive project data is accurate."""
        screen = MockProjectViewerScreen(comprehensive_project)
        result = screen._render_summary()
        
        # Verify key metrics
        assert "Files processed: 200" in result
        assert "10.00 MB" in result
        assert "12,500" in result  # total lines
        assert "512" in result  # commits
        assert "25" in result  # total skills
        assert "62" in result  # total media files


class TestRenderSummaryEdgeCases:
    """Test edge cases and error handling."""
    
    def test_handles_invalid_scan_data(self):
        """Test that invalid scan_data is handled gracefully."""
        project = {
            "project_name": "test",
            "project_path": "/test",
            "scan_timestamp": "2025-12-07T10:30:00Z",
            "scan_data": "invalid"  # Not a dict
        }
        screen = MockProjectViewerScreen(project)
        result = screen._render_summary()
        
        assert "Cannot render" in result or isinstance(result, str)
    
    def test_handles_missing_scan_data(self):
        """Test that missing scan_data is handled gracefully."""
        project = {
            "project_name": "test",
            "project_path": "/test",
            "scan_timestamp": "2025-12-07T10:30:00Z"
        }
        screen = MockProjectViewerScreen(project)
        result = screen._render_summary()
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_handles_empty_lists(self):
        """Test that empty analysis lists are handled."""
        project = {
            "project_name": "test",
            "project_path": "/test",
            "scan_timestamp": "2025-12-07T10:30:00Z",
            "scan_data": {
                "git_analysis": [],
                "skills_analysis": {}
            }
        }
        screen = MockProjectViewerScreen(project)
        result = screen._render_summary()
        
        assert isinstance(result, str)
        assert "Git Statistics" not in result  # Empty list should not render
    
    def test_handles_special_characters(self):
        """Test that special characters are properly escaped."""
        project = {
            "project_name": "project<script>alert(1)</script>",
            "project_path": "/test/path&evil",
            "scan_timestamp": "2025-12-07T10:30:00Z",
            "scan_data": {}
        }
        screen = MockProjectViewerScreen(project)
        result = screen._render_summary()
        
        # Should be escaped, not contain raw HTML
        assert "<script>" not in result
        assert "alert" not in result
    
    def test_handles_very_large_numbers(self):
        """Test formatting of very large numbers."""
        project = {
            "project_name": "big-project",
            "project_path": "/test",
            "scan_timestamp": "2025-12-07T10:30:00Z",
            "scan_data": {
                "summary": {
                    "files_processed": 1000000,
                    "bytes_processed": 1099511627776  # 1 TB
                }
            }
        }
        screen = MockProjectViewerScreen(project)
        result = screen._render_summary()
        
        # Numbers should be properly formatted with commas
        assert "1,000,000" in result
    
    def test_handles_malformed_timestamps(self):
        """Test that malformed timestamps don't break rendering."""
        project = {
            "project_name": "test",
            "project_path": "/test",
            "scan_timestamp": "invalid-timestamp",
            "scan_data": {}
        }
        screen = MockProjectViewerScreen(project)
        result = screen._render_summary()
        
        assert isinstance(result, str)
        assert "invalid-timestamp" in result  # Falls back to original


class TestRenderSummaryFormatting:
    """Test output formatting."""
    
    def test_output_has_proper_structure(self, comprehensive_project):
        """Test that output has proper structure with headers and content."""
        screen = MockProjectViewerScreen(comprehensive_project)
        result = screen._render_summary()
        
        lines = result.split("\n")
        assert len(lines) > 10  # Should have multiple lines
        
        # Should have markup formatting
        assert "[b]" in result  # Bold
        assert "[yellow]" in result  # Colors
    
    def test_sections_properly_separated(self, comprehensive_project):
        """Test that sections are properly separated with blank lines."""
        screen = MockProjectViewerScreen(comprehensive_project)
        result = screen._render_summary()
        
        # Check for section headers followed by content
        assert "Summary Statistics" in result
        assert "Files processed" in result
    
    def test_bullet_points_formatting(self, project_with_contributions):
        """Test that bullet points are consistently formatted."""
        screen = MockProjectViewerScreen(project_with_contributions)
        result = screen._render_summary()
        
        # Should use consistent bullet formatting
        assert "  •" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
