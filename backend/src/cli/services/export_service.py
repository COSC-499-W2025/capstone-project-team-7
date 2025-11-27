"""
Export Service Module

Generates formatted PDF and HTML reports from scan results.
Provides professional-looking portfolio reports with charts and statistics.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

_DATACLASS_KWARGS = {"slots": True} if sys.version_info >= (3, 10) else {}


@dataclass(**_DATACLASS_KWARGS)
class ExportConfig:
    """Configuration for export generation."""
    
    include_file_list: bool = True
    include_code_analysis: bool = True
    include_skills: bool = True
    include_contributions: bool = True
    include_git_analysis: bool = True
    include_media_analysis: bool = True
    include_pdf_summaries: bool = True
    max_files_in_list: int = 100
    chart_style: str = "modern"  # modern, minimal, classic


@dataclass(**_DATACLASS_KWARGS)
class ExportResult:
    """Result of an export operation."""
    
    success: bool
    file_path: Optional[Path] = None
    format: str = "html"
    error: Optional[str] = None
    file_size_bytes: int = 0


class ExportService:
    """Service for generating formatted PDF and HTML reports."""
    
    def __init__(self, config: Optional[ExportConfig] = None):
        self.config = config or ExportConfig()
    
    def export_html(
        self,
        payload: Dict[str, Any],
        output_path: Path,
        project_name: Optional[str] = None,
    ) -> ExportResult:
        """
        Generate a beautifully formatted HTML report.
        
        Args:
            payload: The scan export payload dictionary
            output_path: Where to save the HTML file
            project_name: Optional project name for the report title
            
        Returns:
            ExportResult with success status and file path
        """
        try:
            html_content = self._generate_html_report(payload, project_name)
            output_path.write_text(html_content, encoding="utf-8")
            return ExportResult(
                success=True,
                file_path=output_path,
                format="html",
                file_size_bytes=len(html_content.encode("utf-8")),
            )
        except Exception as exc:
            return ExportResult(
                success=False,
                format="html",
                error=str(exc),
            )
    
    def export_pdf(
        self,
        payload: Dict[str, Any],
        output_path: Path,
        project_name: Optional[str] = None,
    ) -> ExportResult:
        """
        Generate a PDF report from scan results.
        
        Uses HTML as intermediate format, then converts to PDF.
        Falls back to HTML if PDF generation fails.
        
        Args:
            payload: The scan export payload dictionary
            output_path: Where to save the PDF file
            project_name: Optional project name for the report title
            
        Returns:
            ExportResult with success status and file path
        """
        try:
            # Try to import weasyprint for PDF generation
            try:
                from weasyprint import HTML as WeasyHTML
                has_weasyprint = True
            except ImportError:
                has_weasyprint = False
            
            html_content = self._generate_html_report(payload, project_name, for_pdf=True)
            
            if has_weasyprint:
                # Generate PDF using WeasyPrint
                pdf_doc = WeasyHTML(string=html_content)
                pdf_doc.write_pdf(output_path)
                return ExportResult(
                    success=True,
                    file_path=output_path,
                    format="pdf",
                    file_size_bytes=output_path.stat().st_size,
                )
            else:
                # Fallback: save as HTML with .pdf.html extension
                fallback_path = output_path.with_suffix(".pdf.html")
                fallback_path.write_text(html_content, encoding="utf-8")
                return ExportResult(
                    success=True,
                    file_path=fallback_path,
                    format="html",
                    error="PDF generation requires 'weasyprint' package. Saved as HTML instead.",
                    file_size_bytes=len(html_content.encode("utf-8")),
                )
        except Exception as exc:
            return ExportResult(
                success=False,
                format="pdf",
                error=str(exc),
            )
    
    def _generate_html_report(
        self,
        payload: Dict[str, Any],
        project_name: Optional[str] = None,
        for_pdf: bool = False,
    ) -> str:
        """Generate the complete HTML report content."""
        
        # Extract data from payload
        summary = payload.get("summary", {})
        files = payload.get("files", [])
        languages = summary.get("languages", [])
        code_analysis = payload.get("code_analysis", {})
        skills_analysis = payload.get("skills_analysis", {})
        contribution_metrics = payload.get("contribution_metrics", {})
        git_analysis = payload.get("git_analysis", {})
        media_analysis = payload.get("media_analysis", {})
        
        # Determine project name
        if not project_name:
            target = payload.get("target", "")
            if target:
                project_name = Path(target).name
            else:
                project_name = "Portfolio Scan Report"
        
        # Generate report timestamp
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        
        # Build HTML sections
        html_parts = [
            self._html_header(project_name, for_pdf),
            self._html_hero_section(project_name, timestamp, summary),
            self._html_summary_cards(summary, len(files), languages),
        ]
        
        # Language breakdown
        if languages and self.config.include_code_analysis:
            html_parts.append(self._html_language_section(languages))
        
        # Code analysis
        if code_analysis and code_analysis.get("success") and self.config.include_code_analysis:
            html_parts.append(self._html_code_analysis_section(code_analysis))
        
        # Skills analysis
        if skills_analysis and skills_analysis.get("success") and self.config.include_skills:
            html_parts.append(self._html_skills_section(skills_analysis))
        
        # Contribution metrics
        if contribution_metrics and self.config.include_contributions:
            html_parts.append(self._html_contributions_section(contribution_metrics))
        
        # Git analysis
        if git_analysis and self.config.include_git_analysis:
            html_parts.append(self._html_git_section(git_analysis))
        
        # File list
        if files and self.config.include_file_list:
            html_parts.append(self._html_file_list_section(files))
        
        html_parts.append(self._html_footer())
        
        return "\n".join(html_parts)
    
    def _html_header(self, title: str, for_pdf: bool = False) -> str:
        """Generate HTML header with embedded CSS."""
        
        pdf_styles = """
            @page {
                size: A4;
                margin: 1.5cm;
            }
        """ if for_pdf else ""
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self._escape_html(title)} - Portfolio Report</title>
    <style>
        {pdf_styles}
        
        :root {{
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --secondary: #8b5cf6;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --info: #3b82f6;
            --dark: #1f2937;
            --light: #f3f4f6;
            --white: #ffffff;
            --gray-100: #f7f7f8;
            --gray-200: #e5e7eb;
            --gray-300: #d1d5db;
            --gray-400: #9ca3af;
            --gray-500: #6b7280;
            --gray-600: #4b5563;
            --gray-700: #374151;
            --gray-800: #1f2937;
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
            --shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
            --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
            --radius: 0.5rem;
            --radius-lg: 0.75rem;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: var(--gray-800);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 2rem;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: var(--white);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-lg);
            overflow: hidden;
        }}
        
        /* Hero Section */
        .hero {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: var(--white);
            padding: 3rem 2rem;
            text-align: center;
        }}
        
        .hero h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .hero .subtitle {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        .hero .timestamp {{
            margin-top: 1rem;
            font-size: 0.9rem;
            opacity: 0.8;
        }}
        
        /* Summary Cards */
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            padding: 2rem;
            background: var(--gray-100);
        }}
        
        .card {{
            background: var(--white);
            border-radius: var(--radius);
            padding: 1.5rem;
            box-shadow: var(--shadow);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .card:hover {{
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }}
        
        .card-icon {{
            width: 48px;
            height: 48px;
            border-radius: var(--radius);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            margin-bottom: 1rem;
        }}
        
        .card-icon.files {{ background: rgba(99, 102, 241, 0.1); color: var(--primary); }}
        .card-icon.size {{ background: rgba(16, 185, 129, 0.1); color: var(--success); }}
        .card-icon.languages {{ background: rgba(139, 92, 246, 0.1); color: var(--secondary); }}
        .card-icon.issues {{ background: rgba(245, 158, 11, 0.1); color: var(--warning); }}
        
        .card-value {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--gray-800);
            line-height: 1.2;
        }}
        
        .card-label {{
            font-size: 0.875rem;
            color: var(--gray-500);
            margin-top: 0.25rem;
        }}
        
        /* Sections */
        .section {{
            padding: 2rem;
            border-bottom: 1px solid var(--gray-200);
        }}
        
        .section:last-child {{
            border-bottom: none;
        }}
        
        .section-title {{
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--gray-800);
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .section-title::before {{
            content: '';
            width: 4px;
            height: 24px;
            background: var(--primary);
            border-radius: 2px;
        }}
        
        /* Language Bars */
        .language-bar {{
            margin-bottom: 1rem;
        }}
        
        .language-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
        }}
        
        .language-name {{
            font-weight: 500;
            color: var(--gray-700);
        }}
        
        .language-stats {{
            font-size: 0.875rem;
            color: var(--gray-500);
        }}
        
        .language-progress {{
            height: 8px;
            background: var(--gray-200);
            border-radius: 4px;
            overflow: hidden;
        }}
        
        .language-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }}
        
        /* Skill Tags */
        .skills-grid {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
        }}
        
        .skill-tag {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: var(--gray-100);
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 500;
            color: var(--gray-700);
            border: 1px solid var(--gray-200);
        }}
        
        .skill-tag.primary {{
            background: rgba(99, 102, 241, 0.1);
            color: var(--primary-dark);
            border-color: rgba(99, 102, 241, 0.2);
        }}
        
        .skill-level {{
            font-size: 0.75rem;
            padding: 0.125rem 0.5rem;
            background: var(--gray-200);
            border-radius: 9999px;
        }}
        
        /* Metrics Grid */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
        }}
        
        .metric-item {{
            text-align: center;
            padding: 1rem;
            background: var(--gray-100);
            border-radius: var(--radius);
        }}
        
        .metric-value {{
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--primary);
        }}
        
        .metric-label {{
            font-size: 0.75rem;
            color: var(--gray-500);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 0.25rem;
        }}
        
        /* File Table */
        .file-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
        }}
        
        .file-table th {{
            background: var(--gray-100);
            padding: 0.75rem 1rem;
            text-align: left;
            font-weight: 600;
            color: var(--gray-600);
            border-bottom: 2px solid var(--gray-200);
        }}
        
        .file-table td {{
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--gray-200);
        }}
        
        .file-table tr:hover {{
            background: var(--gray-50);
        }}
        
        .file-path {{
            font-family: 'SF Mono', 'Consolas', monospace;
            font-size: 0.8rem;
            color: var(--gray-700);
        }}
        
        .file-size {{
            color: var(--gray-500);
            white-space: nowrap;
        }}
        
        .file-type {{
            display: inline-block;
            padding: 0.125rem 0.5rem;
            background: var(--gray-100);
            border-radius: 4px;
            font-size: 0.75rem;
            color: var(--gray-600);
        }}
        
        /* Footer */
        .footer {{
            background: var(--gray-800);
            color: var(--gray-400);
            padding: 1.5rem 2rem;
            text-align: center;
            font-size: 0.875rem;
        }}
        
        .footer a {{
            color: var(--primary);
            text-decoration: none;
        }}
        
        /* Chart Container */
        .chart-container {{
            margin: 1.5rem 0;
            padding: 1rem;
            background: var(--gray-50);
            border-radius: var(--radius);
        }}
        
        /* Contribution Timeline */
        .timeline {{
            display: flex;
            flex-wrap: wrap;
            gap: 3px;
            padding: 1rem;
            background: var(--gray-50);
            border-radius: var(--radius);
        }}
        
        .timeline-day {{
            width: 12px;
            height: 12px;
            border-radius: 2px;
            background: var(--gray-200);
        }}
        
        .timeline-day.level-1 {{ background: #c6e48b; }}
        .timeline-day.level-2 {{ background: #7bc96f; }}
        .timeline-day.level-3 {{ background: #449450; }}
        .timeline-day.level-4 {{ background: #196127; }}
        
        /* Quality Badge */
        .quality-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            border-radius: var(--radius);
            font-weight: 600;
        }}
        
        .quality-badge.excellent {{
            background: rgba(16, 185, 129, 0.1);
            color: var(--success);
        }}
        
        .quality-badge.good {{
            background: rgba(59, 130, 246, 0.1);
            color: var(--info);
        }}
        
        .quality-badge.fair {{
            background: rgba(245, 158, 11, 0.1);
            color: var(--warning);
        }}
        
        .quality-badge.needs-work {{
            background: rgba(239, 68, 68, 0.1);
            color: var(--danger);
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            body {{
                padding: 1rem;
            }}
            
            .hero h1 {{
                font-size: 1.75rem;
            }}
            
            .summary-cards {{
                grid-template-columns: repeat(2, 1fr);
                padding: 1rem;
            }}
            
            .section {{
                padding: 1.5rem 1rem;
            }}
        }}
        
        /* Print styles */
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            
            .container {{
                box-shadow: none;
            }}
            
            .card:hover {{
                transform: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
'''
    
    def _html_hero_section(self, project_name: str, timestamp: str, summary: Dict[str, Any]) -> str:
        """Generate the hero section."""
        files_count = summary.get("files_processed", 0)
        
        return f'''
        <div class="hero">
            <h1>📊 {self._escape_html(project_name)}</h1>
            <p class="subtitle">Portfolio Analysis Report</p>
            <p class="timestamp">Generated on {timestamp}</p>
        </div>
'''
    
    def _html_summary_cards(
        self,
        summary: Dict[str, Any],
        file_count: int,
        languages: List[Dict[str, Any]],
    ) -> str:
        """Generate summary cards section."""
        
        files_processed = summary.get("files_processed", file_count)
        bytes_processed = summary.get("bytes_processed", 0)
        issues_count = summary.get("issues_count", 0)
        language_count = len(languages) if languages else 0
        
        # Format bytes
        size_str = self._format_bytes(bytes_processed)
        
        return f'''
        <div class="summary-cards">
            <div class="card">
                <div class="card-icon files">📁</div>
                <div class="card-value">{files_processed:,}</div>
                <div class="card-label">Files Analyzed</div>
            </div>
            <div class="card">
                <div class="card-icon size">💾</div>
                <div class="card-value">{size_str}</div>
                <div class="card-label">Total Size</div>
            </div>
            <div class="card">
                <div class="card-icon languages">🔤</div>
                <div class="card-value">{language_count}</div>
                <div class="card-label">Languages</div>
            </div>
            <div class="card">
                <div class="card-icon issues">⚠️</div>
                <div class="card-value">{issues_count}</div>
                <div class="card-label">Issues Found</div>
            </div>
        </div>
'''
    
    def _html_language_section(self, languages: List[Dict[str, Any]]) -> str:
        """Generate language breakdown section."""
        
        if not languages:
            return ""
        
        # Calculate total for percentages
        total_files = sum(lang.get("count", 0) for lang in languages)
        if total_files == 0:
            return ""
        
        # Color palette for languages
        colors = [
            "#6366f1", "#8b5cf6", "#ec4899", "#ef4444", "#f59e0b",
            "#10b981", "#14b8a6", "#06b6d4", "#3b82f6", "#6366f1",
        ]
        
        bars_html = []
        for i, lang in enumerate(languages[:10]):  # Top 10 languages
            name = lang.get("language", "Unknown")
            count = lang.get("count", 0)
            percentage = (count / total_files) * 100
            color = colors[i % len(colors)]
            
            bars_html.append(f'''
            <div class="language-bar">
                <div class="language-header">
                    <span class="language-name">{self._escape_html(name)}</span>
                    <span class="language-stats">{count} files ({percentage:.1f}%)</span>
                </div>
                <div class="language-progress">
                    <div class="language-fill" style="width: {percentage}%; background: {color};"></div>
                </div>
            </div>
''')
        
        return f'''
        <div class="section">
            <h2 class="section-title">Language Breakdown</h2>
            {"".join(bars_html)}
        </div>
'''
    
    def _html_code_analysis_section(self, code_analysis: Dict[str, Any]) -> str:
        """Generate code analysis section."""
        
        metrics = code_analysis.get("metrics", {})
        quality = code_analysis.get("quality", {})
        
        total_lines = metrics.get("total_lines", 0)
        code_lines = metrics.get("total_code_lines", 0)
        comments = metrics.get("total_comments", 0)
        functions = metrics.get("total_functions", 0)
        classes = metrics.get("total_classes", 0)
        complexity = metrics.get("average_complexity", 0)
        maintainability = metrics.get("average_maintainability", 0)
        
        # Determine quality badge
        if maintainability >= 80:
            quality_class = "excellent"
            quality_label = "Excellent"
            quality_emoji = "🌟"
        elif maintainability >= 60:
            quality_class = "good"
            quality_label = "Good"
            quality_emoji = "✅"
        elif maintainability >= 40:
            quality_class = "fair"
            quality_label = "Fair"
            quality_emoji = "⚡"
        else:
            quality_class = "needs-work"
            quality_label = "Needs Work"
            quality_emoji = "🔧"
        
        return f'''
        <div class="section">
            <h2 class="section-title">Code Analysis</h2>
            
            <div style="margin-bottom: 1.5rem;">
                <span class="quality-badge {quality_class}">{quality_emoji} Code Quality: {quality_label}</span>
            </div>
            
            <div class="metrics-grid">
                <div class="metric-item">
                    <div class="metric-value">{total_lines:,}</div>
                    <div class="metric-label">Total Lines</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{code_lines:,}</div>
                    <div class="metric-label">Code Lines</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{comments:,}</div>
                    <div class="metric-label">Comments</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{functions:,}</div>
                    <div class="metric-label">Functions</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{classes:,}</div>
                    <div class="metric-label">Classes</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{complexity:.1f}</div>
                    <div class="metric-label">Avg Complexity</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{maintainability:.0f}</div>
                    <div class="metric-label">Maintainability</div>
                </div>
            </div>
        </div>
'''
    
    def _html_skills_section(self, skills_analysis: Dict[str, Any]) -> str:
        """Generate skills analysis section."""
        
        skills = skills_analysis.get("skills", [])
        if not skills:
            return ""
        
        # Group skills by category
        primary_skills = []
        secondary_skills = []
        
        for skill in skills:
            name = skill.get("name", "")
            level = skill.get("proficiency_level", "Familiar")
            file_count = skill.get("file_count", 0)
            
            if file_count >= 5 or level in ["Expert", "Proficient"]:
                primary_skills.append((name, level, file_count))
            else:
                secondary_skills.append((name, level, file_count))
        
        def render_skills(skill_list: List, is_primary: bool = False) -> str:
            tags = []
            for name, level, count in skill_list[:15]:  # Limit to 15
                css_class = "skill-tag primary" if is_primary else "skill-tag"
                tags.append(f'''
                <span class="{css_class}">
                    {self._escape_html(name)}
                    <span class="skill-level">{level}</span>
                </span>
''')
            return "".join(tags)
        
        html = f'''
        <div class="section">
            <h2 class="section-title">Skills & Technologies</h2>
'''
        
        if primary_skills:
            html += f'''
            <h3 style="font-size: 1rem; color: var(--gray-600); margin-bottom: 1rem;">Primary Skills</h3>
            <div class="skills-grid" style="margin-bottom: 1.5rem;">
                {render_skills(primary_skills, is_primary=True)}
            </div>
'''
        
        if secondary_skills:
            html += f'''
            <h3 style="font-size: 1rem; color: var(--gray-600); margin-bottom: 1rem;">Additional Skills</h3>
            <div class="skills-grid">
                {render_skills(secondary_skills)}
            </div>
'''
        
        html += "</div>"
        return html
    
    def _html_contributions_section(self, contribution_metrics: Dict[str, Any]) -> str:
        """Generate contribution metrics section."""
        
        # Extract metrics
        total_commits = contribution_metrics.get("total_commits", 0)
        total_lines_added = contribution_metrics.get("total_lines_added", 0)
        total_lines_deleted = contribution_metrics.get("total_lines_deleted", 0)
        total_files_changed = contribution_metrics.get("total_files_changed", 0)
        
        # Date range
        first_commit = contribution_metrics.get("first_commit_date", "")
        last_commit = contribution_metrics.get("last_commit_date", "")
        
        date_range = ""
        if first_commit and last_commit:
            date_range = f"<p style='color: var(--gray-500); font-size: 0.875rem; margin-bottom: 1rem;'>Activity period: {first_commit[:10]} to {last_commit[:10]}</p>"
        
        return f'''
        <div class="section">
            <h2 class="section-title">Contribution Metrics</h2>
            {date_range}
            
            <div class="metrics-grid">
                <div class="metric-item">
                    <div class="metric-value">{total_commits:,}</div>
                    <div class="metric-label">Commits</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value" style="color: var(--success);">+{total_lines_added:,}</div>
                    <div class="metric-label">Lines Added</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value" style="color: var(--danger);">-{total_lines_deleted:,}</div>
                    <div class="metric-label">Lines Deleted</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{total_files_changed:,}</div>
                    <div class="metric-label">Files Changed</div>
                </div>
            </div>
        </div>
'''
    
    def _html_git_section(self, git_analysis: Dict[str, Any]) -> str:
        """Generate Git analysis section."""
        
        repos = git_analysis if isinstance(git_analysis, list) else [git_analysis]
        
        if not repos:
            return ""
        
        repos_html = []
        for repo in repos[:5]:  # Limit to 5 repos
            if isinstance(repo, dict):
                name = repo.get("repo_name", repo.get("name", "Repository"))
                commit_count = repo.get("commit_count", repo.get("commits", 0))
                branch = repo.get("current_branch", repo.get("branch", ""))
                
                repos_html.append(f'''
                <div class="card" style="margin-bottom: 1rem;">
                    <h3 style="font-size: 1.1rem; margin-bottom: 0.5rem;">📂 {self._escape_html(name)}</h3>
                    <p style="color: var(--gray-500); font-size: 0.875rem;">
                        {commit_count:,} commits{f" • Branch: {branch}" if branch else ""}
                    </p>
                </div>
''')
        
        return f'''
        <div class="section">
            <h2 class="section-title">Git Repositories</h2>
            {"".join(repos_html)}
        </div>
'''
    
    def _html_file_list_section(self, files: List[Dict[str, Any]]) -> str:
        """Generate file list section."""
        
        # Limit files shown
        max_files = self.config.max_files_in_list
        displayed_files = files[:max_files]
        remaining = len(files) - max_files if len(files) > max_files else 0
        
        rows_html = []
        for f in displayed_files:
            path = f.get("path", "")
            size = f.get("size_bytes", 0)
            mime_type = f.get("mime_type", "")
            
            # Shorten path if too long
            display_path = path if len(path) <= 60 else "..." + path[-57:]
            
            rows_html.append(f'''
            <tr>
                <td class="file-path" title="{self._escape_html(path)}">{self._escape_html(display_path)}</td>
                <td class="file-size">{self._format_bytes(size)}</td>
                <td><span class="file-type">{self._escape_html(mime_type.split("/")[-1] if mime_type else "unknown")}</span></td>
            </tr>
''')
        
        remaining_note = f'''
            <p style="color: var(--gray-500); font-size: 0.875rem; margin-top: 1rem; text-align: center;">
                ... and {remaining:,} more files
            </p>
''' if remaining > 0 else ""
        
        return f'''
        <div class="section">
            <h2 class="section-title">Files Analyzed</h2>
            <table class="file-table">
                <thead>
                    <tr>
                        <th>Path</th>
                        <th>Size</th>
                        <th>Type</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows_html)}
                </tbody>
            </table>
            {remaining_note}
        </div>
'''
    
    def _html_footer(self) -> str:
        """Generate HTML footer."""
        
        year = datetime.now().year
        
        return f'''
        <div class="footer">
            <p>Generated by Portfolio Scanner • {year}</p>
            <p style="margin-top: 0.5rem; font-size: 0.75rem;">
                This report was automatically generated from your project artifacts.
            </p>
        </div>
    </div>
</body>
</html>
'''
    
    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters."""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )
    
    @staticmethod
    def _format_bytes(size_bytes: int) -> str:
        """Format bytes into human-readable string."""
        if size_bytes == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(size_bytes)
        
        while size >= 1024 and i < len(units) - 1:
            size /= 1024
            i += 1
        
        if i == 0:
            return f"{int(size)} {units[i]}"
        return f"{size:.1f} {units[i]}"
