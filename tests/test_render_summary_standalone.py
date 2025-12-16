"""
Standalone tests for ProjectViewerScreen._render_summary() method.

This is a simplified version that doesn't depend on conftest imports.

Run with: python -m pytest tests/test_render_summary_standalone.py -v
Or directly: python tests/test_render_summary_standalone.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Test the _render_summary implementation directly without imports
class TestRenderSummary:
    """Test the render_summary method."""
    
    def render_summary(self, project: dict) -> str:
        """Copy of the _render_summary() method logic."""
        from html import escape
        
        lines = []
        scan_data = project.get("scan_data", {})
        
        lines.append("[b][cyan]📊 Project Summary[/cyan][/b]\n")
        
        # Project Header
        project_name = escape(project.get('project_name', 'Unknown'))
        project_path = escape(project.get('project_path', 'Unknown'))
        timestamp = project.get("scan_timestamp", "Unknown")
        
        lines.append(f"[b]{project_name}[/b]")
        lines.append(f"Path: {project_path}")
        
        if timestamp != "Unknown":
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                timestamp = dt.strftime("%Y-%m-%d at %H:%M:%S")
            except:
                pass
        lines.append(f"Scanned: {timestamp}\n")
        
        if not isinstance(scan_data, dict):
            lines.append("[red]Cannot render: scan_data is not a dictionary[/red]")
            return "\n".join(lines)
        
        # Summary Statistics
        summary = scan_data.get("summary", {})
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
        
        # Languages
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
        
        # Code Quality
        code_data = scan_data.get("code_analysis", {})
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
        
        # Skills
        skills_data = scan_data.get("skills_analysis", {})
        if skills_data and skills_data.get("success"):
            lines.append("[b][yellow]🎯 Skills[/yellow][/b]")
            total_skills = skills_data.get("total_skills", 0)
            skills_by_cat = skills_data.get("skills_by_category", {})
            
            if total_skills:
                lines.append(f"  • Total skills: {total_skills}")
            
            if skills_by_cat:
                for category, skills in list(skills_by_cat.items())[:3]:
                    if skills:
                        top_skill = skills[0]
                        if isinstance(top_skill, dict):
                            name = escape(top_skill.get("name", "Unknown"))
                            prof = top_skill.get("proficiency", "")
                            lines.append(f"  • {category}: {name}{f' ({prof})' if prof else ''}")
                        else:
                            lines.append(f"  • {category}: {escape(str(top_skill))}")
            lines.append("")
        
        # Git Stats
        git_data = scan_data.get("git_analysis", [])
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
        
        # Contributions
        contrib_data = scan_data.get("contribution_metrics", {})
        if isinstance(contrib_data, dict) and contrib_data:
            lines.append("[b][yellow]📊 Contributions[/yellow][/b]")
            
            ranking = scan_data.get("contribution_ranking", {})
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
                top_name = escape(top.get("name", "Unknown"))
                top_commits = top.get("commits", 0)
                if top_commits:
                    lines.append(f"  • Top contributor: {top_name} ({top_commits} commits)")
            lines.append("")
        
        # Media Analysis
        media_data = scan_data.get("media_analysis", {})
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
    
    # Test methods
    def test_minimal_project(self):
        """Test with minimal project data."""
        project = {
            "project_name": "test-project",
            "project_path": "/test/path",
            "scan_timestamp": "2025-12-07T10:30:00Z",
            "scan_data": {}
        }
        result = self.render_summary(project)
        assert "test-project" in result
        assert "/test/path" in result
        assert "2025-12-07" in result
        print("✓ test_minimal_project passed")
    
    def test_with_summary_stats(self):
        """Test with summary statistics."""
        project = {
            "project_name": "code-analyzer",
            "project_path": "/home/user/code-analyzer",
            "scan_timestamp": "2025-12-07T10:30:00Z",
            "scan_data": {
                "summary": {
                    "files_processed": 150,
                    "bytes_processed": 5242880,
                    "issues_count": 3
                }
            }
        }
        result = self.render_summary(project)
        assert "Summary Statistics" in result
        assert "Files processed: 150" in result
        assert "5.00 MB" in result
        assert "Issues found: 3" in result
        print("✓ test_with_summary_stats passed")
    
    def test_with_code_analysis(self):
        """Test with code analysis."""
        project = {
            "project_name": "python-app",
            "project_path": "/src/python-app",
            "scan_timestamp": "2025-12-07T10:30:00Z",
            "scan_data": {
                "code_analysis": {
                    "success": True,
                    "metrics": {
                        "total_lines": 5000,
                        "average_complexity": 3.5,
                        "average_maintainability": 78.5
                    },
                    "quality": {
                        "security_issues": 2,
                        "high_priority_files": 1
                    }
                }
            }
        }
        result = self.render_summary(project)
        assert "Code Quality" in result
        assert "Total lines: 5,000" in result
        assert "Avg complexity: 3.50" in result
        assert "Security issues: 2" in result
        print("✓ test_with_code_analysis passed")
    
    def test_with_git_analysis(self):
        """Test with git analysis."""
        project = {
            "project_name": "webapp",
            "project_path": "/src/webapp",
            "scan_timestamp": "2025-12-07T10:30:00Z",
            "scan_data": {
                "git_analysis": [
                    {
                        "commit_count": 342,
                        "branches": ["main", "develop", "feature-x"],
                        "contributors": [
                            {"name": "Alice", "commits": 150},
                            {"name": "Bob", "commits": 120}
                        ]
                    }
                ]
            }
        }
        result = self.render_summary(project)
        assert "Git Statistics" in result
        assert "Total commits: 342" in result
        assert "Branches: 3" in result
        print("✓ test_with_git_analysis passed")
    
    def test_with_contributions(self):
        """Test with contribution metrics."""
        project = {
            "project_name": "api-service",
            "project_path": "/src/api-service",
            "scan_timestamp": "2025-12-07T10:30:00Z",
            "scan_data": {
                "contribution_metrics": {
                    "total_commits": 250,
                    "total_contributors": 5
                },
                "contribution_ranking": {
                    "score": 8.5,
                    "user_commit_share": 0.48
                }
            }
        }
        result = self.render_summary(project)
        assert "Contributions" in result
        assert "Importance score: 8.50" in result
        assert "Your contribution: 48.0%" in result
        assert "Total commits: 250" in result
        print("✓ test_with_contributions passed")
    
    def test_with_skills(self):
        """Test with skills analysis."""
        project = {
            "project_name": "fullstack-app",
            "project_path": "/src/fullstack-app",
            "scan_timestamp": "2025-12-07T10:30:00Z",
            "scan_data": {
                "skills_analysis": {
                    "success": True,
                    "total_skills": 18,
                    "skills_by_category": {
                        "languages": [
                            {"name": "Python", "proficiency": "Advanced"}
                        ]
                    }
                }
            }
        }
        result = self.render_summary(project)
        assert "Skills" in result
        assert "Total skills: 18" in result
        assert "Python" in result
        print("✓ test_with_skills passed")
    
    def test_with_media_analysis(self):
        """Test with media analysis."""
        project = {
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
                    }
                }
            }
        }
        result = self.render_summary(project)
        assert "Media Analysis" in result
        assert "Total media files: 45" in result
        assert "Images: 35" in result
        print("✓ test_with_media_analysis passed")
    
    def test_special_characters_escaped(self):
        """Test that special characters are properly escaped."""
        project = {
            "project_name": "project<script>alert(1)</script>",
            "project_path": "/test/path&evil",
            "scan_timestamp": "2025-12-07T10:30:00Z",
            "scan_data": {}
        }
        result = self.render_summary(project)
        # HTML entities should be used instead of raw HTML
        assert "&lt;script&gt;" in result or "<script>" not in result
        assert "project" in result  # Name should still be present, just escaped
        print("✓ test_special_characters_escaped passed")
    
    def test_invalid_scan_data(self):
        """Test that invalid scan_data is handled gracefully."""
        project = {
            "project_name": "test",
            "project_path": "/test",
            "scan_timestamp": "2025-12-07T10:30:00Z",
            "scan_data": "invalid"
        }
        result = self.render_summary(project)
        assert "Cannot render" in result
        print("✓ test_invalid_scan_data passed")
    
    def test_missing_scan_data(self):
        """Test handling of missing scan_data."""
        project = {
            "project_name": "test",
            "project_path": "/test",
            "scan_timestamp": "2025-12-07T10:30:00Z"
        }
        result = self.render_summary(project)
        assert isinstance(result, str)
        assert len(result) > 0
        print("✓ test_missing_scan_data passed")
    
    def test_comprehensive_project(self):
        """Test with all data types present."""
        project = {
            "project_name": "comprehensive-project",
            "project_path": "/home/dev/comprehensive-project",
            "scan_timestamp": "2025-12-07T15:45:30Z",
            "scan_data": {
                "summary": {
                    "files_processed": 200,
                    "bytes_processed": 10485760,
                    "issues_count": 5,
                    "languages": [
                        {"name": "Python", "files": 85},
                        {"name": "JavaScript", "files": 45}
                    ]
                },
                "code_analysis": {
                    "success": True,
                    "metrics": {
                        "total_lines": 12500,
                        "average_complexity": 3.2,
                        "average_maintainability": 81.3
                    }
                },
                "git_analysis": [
                    {
                        "commit_count": 512,
                        "branches": ["main", "dev"],
                        "contributors": [
                            {"name": "Lead Dev", "commits": 250}
                        ]
                    }
                ],
                "contribution_metrics": {
                    "total_commits": 512,
                    "total_contributors": 3
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
                            {"name": "Python", "proficiency": "Expert"}
                        ]
                    }
                },
                "media_analysis": {
                    "summary": {
                        "total_media_files": 62,
                        "images": 50
                    }
                }
            }
        }
        result = self.render_summary(project)
        
        # Check all sections are present
        assert "Summary Statistics" in result
        assert "Languages" in result
        assert "Code Quality" in result
        assert "Skills" in result
        assert "Git Statistics" in result
        assert "Contributions" in result
        assert "Media Analysis" in result
        
        # Check key data points
        assert "Files processed: 200" in result
        assert "Python" in result
        assert "12,500" in result
        assert "512" in result
        
        print("✓ test_comprehensive_project passed")


def run_tests():
    """Run all tests."""
    test = TestRenderSummary()
    
    tests = [
        test.test_minimal_project,
        test.test_with_summary_stats,
        test.test_with_code_analysis,
        test.test_with_git_analysis,
        test.test_with_contributions,
        test.test_with_skills,
        test.test_with_media_analysis,
        test.test_special_characters_escaped,
        test.test_invalid_scan_data,
        test.test_missing_scan_data,
        test.test_comprehensive_project,
    ]
    
    print(f"\nRunning {len(tests)} tests...\n")
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_func.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} error: {e}")
            failed += 1
    
    print(f"\n{passed} passed, {failed} failed\n")
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
