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
    
    include_file_list: bool = False  # Disabled by default - not needed in portfolio report
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
            html_content = self._generate_html_report(payload, project_name, for_pdf=True)
            
            # Try WeasyPrint first (requires GTK on Windows)
            pdf_generated = False
            pdf_error = None
            
            try:
                from weasyprint import HTML as WeasyHTML
                pdf_doc = WeasyHTML(string=html_content)
                pdf_doc.write_pdf(output_path)
                pdf_generated = True
            except ImportError:
                pdf_error = "weasyprint package not installed"
            except OSError as e:
                # GTK libraries not found on Windows
                pdf_error = f"PDF library dependencies missing: {e}"
            except Exception as e:
                pdf_error = f"PDF generation failed: {e}"
            
            if pdf_generated:
                return ExportResult(
                    success=True,
                    file_path=output_path,
                    format="pdf",
                    file_size_bytes=output_path.stat().st_size,
                )
            else:
                # Fallback: save as HTML (user can print to PDF from browser)
                fallback_path = output_path.with_suffix(".html")
                fallback_path.write_text(html_content, encoding="utf-8")
                return ExportResult(
                    success=True,
                    file_path=fallback_path,
                    format="html",
                    error=f"{pdf_error}. Saved as HTML instead - open in browser and use Print > Save as PDF.",
                    file_size_bytes=len(html_content.encode("utf-8")),
                )
        except Exception as exc:
            return ExportResult(
                success=False,
                format="pdf",
                error=str(exc),
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
        contribution_ranking = payload.get("contribution_ranking", {})
        git_analysis = payload.get("git_analysis", {})
        media_analysis = payload.get("media_analysis", {})
        pdf_analysis = payload.get("pdf_analysis", {})
        document_analysis = payload.get("document_analysis", {})
        
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
        
        # Executive Summary with key insights
        html_parts.append(self._html_executive_summary(
            payload, code_analysis, skills_analysis, 
            contribution_metrics, contribution_ranking
        ))
        
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
        
        # PDF Document Analysis
        if pdf_analysis and pdf_analysis.get("summaries") and self.config.include_pdf_summaries:
            html_parts.append(self._html_pdf_analysis_section(pdf_analysis))
        
        # Document Analysis (DOCX, etc.)
        if document_analysis and document_analysis.get("documents"):
            html_parts.append(self._html_document_analysis_section(document_analysis))
        
        # Media Analysis
        if media_analysis and self.config.include_media_analysis:
            html_parts.append(self._html_media_analysis_section(media_analysis))
        
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
        """Generate code analysis section with detailed breakdowns."""
        
        metrics = code_analysis.get("metrics", {})
        quality = code_analysis.get("quality", {})
        refactor_candidates = code_analysis.get("refactor_candidates", [])
        languages = code_analysis.get("languages", {})
        
        total_lines = metrics.get("total_lines", 0)
        code_lines = metrics.get("total_code_lines", 0)
        comments = metrics.get("total_comments", 0)
        functions = metrics.get("total_functions", 0)
        classes = metrics.get("total_classes", 0)
        complexity = metrics.get("average_complexity", 0)
        maintainability = metrics.get("average_maintainability", 0)
        
        # Quality indicators
        security_issues = quality.get("security_issues", 0)
        todos = quality.get("todos", 0)
        high_priority = quality.get("high_priority_files", 0)
        
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
        
        # Build quality issues section
        quality_issues_html = ""
        if security_issues or todos or high_priority:
            issues_parts = []
            if security_issues > 0:
                issues_parts.append(f'<span class="quality-issue security">🔒 {security_issues} security issue(s)</span>')
            if todos > 0:
                issues_parts.append(f'<span class="quality-issue todo">📝 {todos} TODO(s) found</span>')
            if high_priority > 0:
                issues_parts.append(f'<span class="quality-issue priority">⚠️ {high_priority} high-priority file(s)</span>')
            
            quality_issues_html = f'''
            <div class="quality-issues" style="margin-top: 1rem;">
                {" ".join(issues_parts)}
            </div>
'''
        
        # Build language breakdown section
        languages_html = ""
        if languages:
            total_files = sum(languages.values())
            lang_items = []
            
            # Sort by count descending
            sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)
            
            for lang, count in sorted_langs[:8]:
                percentage = (count / total_files * 100) if total_files > 0 else 0
                lang_items.append(f'''
                <div class="lang-item">
                    <span class="lang-name">{self._escape_html(lang)}</span>
                    <div class="lang-bar-container">
                        <div class="lang-bar" style="width: {percentage:.0f}%;"></div>
                    </div>
                    <span class="lang-count">{count} files ({percentage:.0f}%)</span>
                </div>
''')
            
            languages_html = f'''
            <div class="languages-detail" style="margin-top: 1.5rem;">
                <h3 style="font-size: 1rem; color: var(--gray-700); margin-bottom: 1rem;">📊 Language Distribution</h3>
                <div class="lang-list">
                    {"".join(lang_items)}
                </div>
            </div>
'''
        
        # Build refactor candidates section with actual data structure
        refactor_html = ""
        if refactor_candidates:
            candidates_list = []
            for candidate in refactor_candidates[:5]:
                # Handle both old format (file, reason) and new format (path, complexity, maintainability)
                file_path = candidate.get("path", candidate.get("file", ""))
                complexity_val = candidate.get("complexity", 0)
                maintainability_val = candidate.get("maintainability", 0)
                priority = candidate.get("priority", "")
                language = candidate.get("language", "")
                
                # Generate reason based on metrics if not provided
                reason = candidate.get("reason", "")
                if not reason:
                    reasons = []
                    if complexity_val > 10:
                        reasons.append(f"High complexity ({complexity_val:.1f})")
                    elif complexity_val > 5:
                        reasons.append(f"Moderate complexity ({complexity_val:.1f})")
                    if maintainability_val < 40:
                        reasons.append("Low maintainability")
                    elif maintainability_val < 60:
                        reasons.append("Could improve maintainability")
                    if priority:
                        reasons.append(f"Priority: {priority}")
                    reason = "; ".join(reasons) if reasons else "Consider refactoring"
                
                # Shorten path if needed
                display_path = file_path if len(file_path) <= 40 else "..." + file_path[-37:]
                
                # Get top functions if available
                top_funcs = candidate.get("top_functions", [])
                funcs_html = ""
                if top_funcs:
                    func_names = [f.get("name", "") for f in top_funcs[:2] if f.get("needs_refactor", False)]
                    if func_names:
                        funcs_html = f'<div class="refactor-funcs">Functions: {", ".join(func_names)}</div>'
                
                candidates_list.append(f'''
                <div class="refactor-card">
                    <div class="refactor-header">
                        <span class="refactor-file" title="{self._escape_html(file_path)}">{self._escape_html(display_path)}</span>
                        {f'<span class="refactor-lang">{self._escape_html(language)}</span>' if language else ''}
                    </div>
                    <div class="refactor-reason">{self._escape_html(reason)}</div>
                    <div class="refactor-metrics">
                        <span>Complexity: {complexity_val:.1f}</span>
                        <span>Maintainability: {maintainability_val:.0f}</span>
                    </div>
                    {funcs_html}
                </div>
''')
            
            if candidates_list:
                refactor_html = f'''
            <div style="margin-top: 1.5rem;">
                <h3 style="font-size: 1rem; color: var(--gray-700); margin-bottom: 1rem;">🔧 Refactoring Suggestions</h3>
                <p style="color: var(--gray-500); font-size: 0.85rem; margin-bottom: 1rem;">
                    Files that may benefit from refactoring based on complexity and maintainability analysis.
                </p>
                <div class="refactor-list">
                    {"".join(candidates_list)}
                </div>
            </div>
'''
        
        # Explanation helper
        complexity_desc = "Low (simple)" if complexity <= 5 else ("Medium" if complexity <= 10 else "High (complex)")
        maintainability_desc = "highly maintainable" if maintainability >= 80 else ("reasonably maintainable" if maintainability >= 60 else "may need refactoring")
        
        return f'''
        <div class="section">
            <h2 class="section-title">Code Analysis</h2>
            
            <div style="margin-bottom: 1.5rem;">
                <span class="quality-badge {quality_class}">{quality_emoji} Code Quality: {quality_label}</span>
                {quality_issues_html}
            </div>
            
            <p style="color: var(--gray-600); font-size: 0.9rem; margin-bottom: 1.5rem; line-height: 1.6;">
                Static analysis of your codebase measuring complexity, maintainability, and code structure.
                <strong>Cyclomatic Complexity</strong> measures decision points in code (lower is better, 1-10 ideal).
                <strong>Maintainability Index</strong> (0-100) indicates how easy code is to understand and modify (higher is better).
            </p>
            
            <div class="metrics-grid">
                <div class="metric-item">
                    <div class="metric-value">{total_lines:,}</div>
                    <div class="metric-label">Total Lines</div>
                    <div class="metric-desc">Including comments & blanks</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{code_lines:,}</div>
                    <div class="metric-label">Code Lines</div>
                    <div class="metric-desc">Executable statements</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{comments:,}</div>
                    <div class="metric-label">Comments</div>
                    <div class="metric-desc">Documentation lines</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{functions:,}</div>
                    <div class="metric-label">Functions</div>
                    <div class="metric-desc">Methods & functions defined</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{classes:,}</div>
                    <div class="metric-label">Classes</div>
                    <div class="metric-desc">Class definitions</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{complexity:.1f}</div>
                    <div class="metric-label">Avg Complexity</div>
                    <div class="metric-desc">{complexity_desc}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{maintainability:.0f}</div>
                    <div class="metric-label">Maintainability</div>
                    <div class="metric-desc">Code is {maintainability_desc}</div>
                </div>
            </div>
            {languages_html}
            {refactor_html}
        </div>
        <style>
            .lang-list {{
                display: grid;
                gap: 0.5rem;
            }}
            .lang-item {{
                display: flex;
                align-items: center;
                gap: 0.75rem;
                padding: 0.5rem 0;
            }}
            .lang-name {{
                width: 100px;
                font-weight: 500;
                color: var(--gray-700);
                font-size: 0.85rem;
            }}
            .lang-bar-container {{
                flex: 1;
                max-width: 200px;
                height: 8px;
                background: var(--gray-200);
                border-radius: 4px;
                overflow: hidden;
            }}
            .lang-bar {{
                height: 100%;
                background: var(--primary);
                border-radius: 4px;
            }}
            .lang-count {{
                font-size: 0.8rem;
                color: var(--gray-500);
                min-width: 100px;
            }}
            .refactor-list {{
                display: grid;
                gap: 1rem;
            }}
            .refactor-card {{
                background: var(--gray-50);
                border: 1px solid var(--gray-200);
                border-left: 3px solid var(--warning);
                border-radius: var(--radius);
                padding: 1rem;
            }}
            .refactor-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 0.5rem;
            }}
            .refactor-file {{
                font-weight: 600;
                color: var(--gray-800);
                font-size: 0.9rem;
            }}
            .refactor-lang {{
                font-size: 0.75rem;
                background: var(--gray-200);
                color: var(--gray-600);
                padding: 0.15rem 0.5rem;
                border-radius: 4px;
            }}
            .refactor-reason {{
                color: var(--gray-600);
                font-size: 0.85rem;
                margin-bottom: 0.5rem;
            }}
            .refactor-metrics {{
                display: flex;
                gap: 1rem;
                font-size: 0.8rem;
                color: var(--gray-500);
            }}
            .refactor-funcs {{
                margin-top: 0.5rem;
                font-size: 0.8rem;
                color: var(--gray-500);
                font-style: italic;
            }}
            .quality-issues {{
                display: flex;
                flex-wrap: wrap;
                gap: 0.75rem;
            }}
            .quality-issue {{
                display: inline-block;
                padding: 0.375rem 0.75rem;
                border-radius: 4px;
                font-size: 0.8rem;
                font-weight: 500;
            }}
            .quality-issue.security {{
                background: rgba(239, 68, 68, 0.1);
                color: var(--danger);
            }}
            .quality-issue.todo {{
                background: rgba(245, 158, 11, 0.1);
                color: var(--warning);
            }}
            .quality-issue.priority {{
                background: rgba(59, 130, 246, 0.1);
                color: var(--info);
            }}
        </style>
'''
    
    def _html_skills_section(self, skills_analysis: Dict[str, Any]) -> str:
        """Generate skills analysis section with rich narrative content."""
        
        # Check if we have analysis data
        if not skills_analysis.get("success", False):
            return ""
        
        total_skills = skills_analysis.get("total_skills", 0)
        if total_skills == 0:
            return ""
        
        # Get paragraph summary
        paragraph_summary = skills_analysis.get("paragraph_summary", "")
        
        # Get skills by category
        skills_by_category = skills_analysis.get("skills_by_category", {})
        top_skills = skills_analysis.get("top_skills", [])
        all_skills = skills_analysis.get("all_skills", [])
        
        # Category display names
        category_display = {
            "oop": "Object-Oriented Programming",
            "data_structures": "Data Structures",
            "algorithms": "Algorithms",
            "patterns": "Design Patterns",
            "practices": "Best Practices",
            "frameworks": "Frameworks & Libraries",
            "databases": "Database Technologies",
            "architecture": "Software Architecture"
        }
        
        # Calculate statistics
        total_evidence = sum(s.get("evidence_count", 0) for s in all_skills)
        avg_proficiency = sum(s.get("proficiency", 0) for s in all_skills) / len(all_skills) if all_skills else 0
        
        # Determine proficiency tier
        if avg_proficiency >= 0.75:
            proficiency_badge = "Advanced Developer"
            badge_class = "excellent"
            badge_emoji = "🌟"
        elif avg_proficiency >= 0.6:
            proficiency_badge = "Experienced Developer"
            badge_class = "good"
            badge_emoji = "✅"
        elif avg_proficiency >= 0.4:
            proficiency_badge = "Growing Developer"
            badge_class = "fair"
            badge_emoji = "📈"
        else:
            proficiency_badge = "Learning Developer"
            badge_class = "learning"
            badge_emoji = "🌱"
        
        # Build top skills HTML with descriptions
        top_skills_html = ""
        if top_skills:
            skill_items = []
            for i, skill in enumerate(top_skills[:5], 1):
                name = skill.get("name", "")
                category = skill.get("category", "")
                proficiency = skill.get("proficiency", 0)
                evidence = skill.get("evidence_count", 0)
                
                # Get display category
                display_cat = category_display.get(category, category)
                
                # Proficiency bar width
                bar_width = int(proficiency * 100)
                
                # Find description if available
                desc = ""
                for s in all_skills:
                    if s.get("name") == name:
                        desc = s.get("description", "")
                        break
                
                skill_items.append(f'''
                <div class="top-skill-item">
                    <div class="skill-header">
                        <span class="skill-rank">#{i}</span>
                        <span class="skill-name">{self._escape_html(name)}</span>
                        <span class="skill-category-badge">{self._escape_html(display_cat)}</span>
                    </div>
                    <div class="skill-bar-container">
                        <div class="skill-bar" style="width: {bar_width}%;"></div>
                        <span class="skill-percentage">{proficiency:.0%}</span>
                    </div>
                    {f'<p class="skill-description">{self._escape_html(desc)}</p>' if desc else ''}
                    <div class="skill-meta">
                        <span>📝 {evidence} evidence instances</span>
                    </div>
                </div>
''')
            
            top_skills_html = f'''
            <div class="top-skills-section">
                <h3 style="font-size: 1.1rem; color: var(--gray-700); margin-bottom: 1rem;">🏆 Top Skills</h3>
                <div class="top-skills-list">
                    {"".join(skill_items)}
                </div>
            </div>
'''
        
        # Build category breakdown
        category_html = ""
        if skills_by_category:
            category_items = []
            # Sort by number of skills in category
            sorted_categories = sorted(
                skills_by_category.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )
            
            for cat_key, cat_skills in sorted_categories[:6]:  # Top 6 categories
                display_name = category_display.get(cat_key, cat_key)
                skill_count = len(cat_skills)
                
                # Get skill names
                skill_names = [s.get("name", "") for s in cat_skills[:4]]
                more_count = max(0, skill_count - 4)
                
                category_items.append(f'''
                <div class="category-card">
                    <div class="category-name">{self._escape_html(display_name)}</div>
                    <div class="category-count">{skill_count} skill{'s' if skill_count != 1 else ''}</div>
                    <div class="category-skills">
                        {', '.join(self._escape_html(n) for n in skill_names)}
                        {f' +{more_count} more' if more_count > 0 else ''}
                    </div>
                </div>
''')
            
            category_html = f'''
            <div class="categories-section" style="margin-top: 2rem;">
                <h3 style="font-size: 1.1rem; color: var(--gray-700); margin-bottom: 1rem;">📚 Skills by Category</h3>
                <div class="category-grid">
                    {"".join(category_items)}
                </div>
            </div>
'''
        
        # Build all skills tags (secondary display)
        all_skills_html = ""
        if all_skills:
            skill_tags = []
            for skill in sorted(all_skills, key=lambda x: x.get("proficiency", 0), reverse=True)[:20]:
                name = skill.get("name", "")
                proficiency = skill.get("proficiency", 0)
                
                # Determine tag class based on proficiency
                if proficiency >= 0.7:
                    tag_class = "skill-tag expert"
                elif proficiency >= 0.5:
                    tag_class = "skill-tag proficient"
                else:
                    tag_class = "skill-tag familiar"
                
                skill_tags.append(f'<span class="{tag_class}">{self._escape_html(name)}</span>')
            
            all_skills_html = f'''
            <div class="all-skills-section" style="margin-top: 2rem;">
                <h3 style="font-size: 1.1rem; color: var(--gray-700); margin-bottom: 1rem;">🔧 All Detected Skills</h3>
                <div class="skills-tag-cloud">
                    {"".join(skill_tags)}
                </div>
            </div>
'''
        
        return f'''
        <div class="section">
            <h2 class="section-title">Skills & Technical Expertise</h2>
            
            <div class="skills-overview" style="margin-bottom: 1.5rem;">
                <span class="quality-badge {badge_class}">{badge_emoji} {proficiency_badge}</span>
            </div>
            
            {f'<div class="narrative-paragraph"><p>{self._escape_html(paragraph_summary)}</p></div>' if paragraph_summary else ''}
            
            <div class="skills-stats" style="margin: 1.5rem 0;">
                <div class="stats-row">
                    <div class="stat-item">
                        <span class="stat-value">{total_skills}</span>
                        <span class="stat-label">Skills Detected</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">{len(skills_by_category)}</span>
                        <span class="stat-label">Categories</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">{total_evidence:,}</span>
                        <span class="stat-label">Evidence Instances</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">{avg_proficiency:.0%}</span>
                        <span class="stat-label">Avg Proficiency</span>
                    </div>
                </div>
            </div>
            
            {top_skills_html}
            {category_html}
            {all_skills_html}
        </div>
        <style>
            .narrative-paragraph {{
                background: linear-gradient(135deg, var(--gray-50) 0%, var(--gray-100) 100%);
                border-left: 4px solid var(--primary);
                padding: 1.25rem 1.5rem;
                margin-bottom: 1.5rem;
                border-radius: 0 var(--radius) var(--radius) 0;
            }}
            .narrative-paragraph p {{
                color: var(--gray-700);
                line-height: 1.7;
                font-size: 0.95rem;
                margin: 0;
            }}
            .skills-stats .stats-row {{
                display: flex;
                gap: 1.5rem;
                flex-wrap: wrap;
            }}
            .skills-stats .stat-item {{
                background: var(--gray-50);
                padding: 1rem 1.5rem;
                border-radius: var(--radius);
                text-align: center;
                flex: 1;
                min-width: 120px;
            }}
            .skills-stats .stat-value {{
                display: block;
                font-size: 1.5rem;
                font-weight: 700;
                color: var(--primary);
            }}
            .skills-stats .stat-label {{
                display: block;
                font-size: 0.8rem;
                color: var(--gray-500);
                margin-top: 0.25rem;
            }}
            .top-skills-list {{
                display: grid;
                gap: 1rem;
            }}
            .top-skill-item {{
                background: var(--gray-50);
                padding: 1rem 1.25rem;
                border-radius: var(--radius);
                border: 1px solid var(--gray-200);
            }}
            .skill-header {{
                display: flex;
                align-items: center;
                gap: 0.75rem;
                margin-bottom: 0.75rem;
            }}
            .skill-rank {{
                background: var(--primary);
                color: white;
                font-size: 0.75rem;
                font-weight: 600;
                padding: 0.25rem 0.5rem;
                border-radius: 4px;
            }}
            .skill-name {{
                font-weight: 600;
                color: var(--gray-800);
                font-size: 1rem;
            }}
            .skill-category-badge {{
                background: var(--gray-200);
                color: var(--gray-600);
                font-size: 0.7rem;
                padding: 0.2rem 0.5rem;
                border-radius: 4px;
                margin-left: auto;
            }}
            .skill-bar-container {{
                display: flex;
                align-items: center;
                gap: 0.75rem;
                margin-bottom: 0.5rem;
            }}
            .skill-bar {{
                height: 8px;
                background: var(--primary);
                border-radius: 4px;
                flex: 1;
                max-width: 200px;
            }}
            .skill-percentage {{
                font-size: 0.85rem;
                font-weight: 600;
                color: var(--gray-600);
            }}
            .skill-description {{
                color: var(--gray-600);
                font-size: 0.85rem;
                line-height: 1.5;
                margin: 0.5rem 0;
            }}
            .skill-meta {{
                font-size: 0.75rem;
                color: var(--gray-500);
            }}
            .category-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                gap: 1rem;
            }}
            .category-card {{
                background: var(--gray-50);
                padding: 1rem 1.25rem;
                border-radius: var(--radius);
                border: 1px solid var(--gray-200);
            }}
            .category-name {{
                font-weight: 600;
                color: var(--gray-800);
                margin-bottom: 0.25rem;
            }}
            .category-count {{
                font-size: 0.8rem;
                color: var(--primary);
                font-weight: 500;
                margin-bottom: 0.5rem;
            }}
            .category-skills {{
                font-size: 0.8rem;
                color: var(--gray-600);
                line-height: 1.4;
            }}
            .skills-tag-cloud {{
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
            }}
            .skill-tag {{
                padding: 0.375rem 0.75rem;
                border-radius: 20px;
                font-size: 0.8rem;
                font-weight: 500;
            }}
            .skill-tag.expert {{
                background: rgba(99, 102, 241, 0.15);
                color: var(--primary);
                border: 1px solid rgba(99, 102, 241, 0.3);
            }}
            .skill-tag.proficient {{
                background: rgba(16, 185, 129, 0.1);
                color: var(--success);
                border: 1px solid rgba(16, 185, 129, 0.3);
            }}
            .skill-tag.familiar {{
                background: var(--gray-100);
                color: var(--gray-600);
                border: 1px solid var(--gray-200);
            }}
        </style>
'''
    
    def _html_contributions_section(self, contribution_metrics: Dict[str, Any]) -> str:
        """Generate contribution metrics section."""
        
        # Extract metrics
        total_commits = contribution_metrics.get("total_commits", 0)
        total_contributors = contribution_metrics.get("total_contributors", 0)
        project_type = contribution_metrics.get("project_type", "unknown")
        is_solo = contribution_metrics.get("is_solo_project", False)
        duration_days = contribution_metrics.get("project_duration_days", 0)
        commit_frequency = contribution_metrics.get("commit_frequency", 0)
        
        # Activity breakdown
        activity = contribution_metrics.get("overall_activity_breakdown", {})
        lines = activity.get("lines", {})
        percentages = activity.get("percentages", {})
        
        total_lines = lines.get("total", 0)
        code_lines = lines.get("code", 0)
        test_lines = lines.get("test", 0)
        doc_lines = lines.get("documentation", 0)
        
        # Date range
        start_date = contribution_metrics.get("project_start_date", "")
        end_date = contribution_metrics.get("project_end_date", "")
        
        # Contributors info
        contributors = contribution_metrics.get("contributors", [])
        primary = contribution_metrics.get("primary_contributor", {})
        
        # Languages
        languages = contribution_metrics.get("languages_detected", [])
        
        # Project type description
        if is_solo:
            project_desc = "Solo Project"
            project_icon = "👤"
        elif total_contributors > 1:
            project_desc = f"Collaborative ({total_contributors} contributors)"
            project_icon = "👥"
        else:
            project_desc = "Project"
            project_icon = "📁"
        
        # Format duration
        if duration_days:
            if duration_days > 365:
                duration_str = f"{duration_days // 365}y {(duration_days % 365) // 30}m"
            elif duration_days > 30:
                duration_str = f"{duration_days // 30} months"
            else:
                duration_str = f"{duration_days} days"
        else:
            duration_str = "N/A"
        
        # Activity breakdown bars
        activity_html = ""
        if total_lines > 0:
            code_pct = percentages.get("code", 0)
            test_pct = percentages.get("test", 0)
            doc_pct = percentages.get("documentation", 0)
            
            activity_html = f'''
            <div class="activity-breakdown" style="margin-top: 1.5rem;">
                <h3 style="font-size: 1rem; color: var(--gray-700); margin-bottom: 1rem;">Activity Breakdown</h3>
                <p style="color: var(--gray-500); font-size: 0.8rem; margin-bottom: 1rem;">
                    How time and effort were distributed across different types of work.
                </p>
                <div class="activity-bar-container">
                    <div class="activity-bar">
                        <div class="activity-segment code" style="width: {code_pct:.0f}%;" title="Code: {code_pct:.0f}%"></div>
                        <div class="activity-segment test" style="width: {test_pct:.0f}%;" title="Tests: {test_pct:.0f}%"></div>
                        <div class="activity-segment doc" style="width: {doc_pct:.0f}%;" title="Docs: {doc_pct:.0f}%"></div>
                    </div>
                    <div class="activity-legend">
                        <span class="legend-item"><span class="dot code"></span> Code ({code_pct:.0f}%)</span>
                        <span class="legend-item"><span class="dot test"></span> Tests ({test_pct:.0f}%)</span>
                        <span class="legend-item"><span class="dot doc"></span> Documentation ({doc_pct:.0f}%)</span>
                    </div>
                </div>
            </div>
'''
        
        # Top contributors
        contributors_html = ""
        if contributors and len(contributors) > 0:
            contrib_items = []
            for contrib in contributors[:5]:
                name = contrib.get("name", "Unknown")
                commits = contrib.get("commits", 0)
                pct = contrib.get("commit_percentage", 0)
                contrib_items.append(f'''
                <div class="contributor-item">
                    <span class="contributor-name">{self._escape_html(name)}</span>
                    <span class="contributor-stats">{commits:,} commits ({pct:.0f}%)</span>
                </div>
''')
            
            contributors_html = f'''
            <div class="contributors-section" style="margin-top: 1.5rem;">
                <h3 style="font-size: 1rem; color: var(--gray-700); margin-bottom: 1rem;">Contributors</h3>
                <div class="contributors-list">
                    {"".join(contrib_items)}
                </div>
            </div>
'''
        
        return f'''
        <div class="section">
            <h2 class="section-title">Contribution Metrics</h2>
            
            <div class="project-badge" style="margin-bottom: 1.5rem;">
                <span style="font-size: 1.5rem; margin-right: 0.5rem;">{project_icon}</span>
                <span style="font-weight: 600; color: var(--gray-700);">{project_desc}</span>
                {f'<span style="color: var(--gray-500); margin-left: 1rem;">Duration: {duration_str}</span>' if duration_days else ''}
            </div>
            
            <p style="color: var(--gray-600); font-size: 0.9rem; margin-bottom: 1.5rem; line-height: 1.6;">
                This section shows your development activity, including commits, code contributions, 
                and how you've balanced different types of work like writing code, tests, and documentation.
            </p>
            
            <div class="metrics-grid">
                <div class="metric-item">
                    <div class="metric-value">{total_commits:,}</div>
                    <div class="metric-label">Total Commits</div>
                    <div class="metric-desc">Version control snapshots</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{total_lines:,}</div>
                    <div class="metric-label">Lines Changed</div>
                    <div class="metric-desc">Added + modified + deleted</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{code_lines:,}</div>
                    <div class="metric-label">Code Lines</div>
                    <div class="metric-desc">Application source code</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{test_lines:,}</div>
                    <div class="metric-label">Test Lines</div>
                    <div class="metric-desc">Unit & integration tests</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{commit_frequency:.1f}</div>
                    <div class="metric-label">Commits/Day</div>
                    <div class="metric-desc">Average development pace</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{len(languages)}</div>
                    <div class="metric-label">Languages</div>
                    <div class="metric-desc">Programming languages used</div>
                </div>
            </div>
            
            {activity_html}
            {contributors_html}
        </div>
        <style>
            .metric-desc {{
                font-size: 0.7rem;
                color: var(--gray-400);
                margin-top: 0.25rem;
            }}
            .activity-bar-container {{
                background: var(--gray-100);
                border-radius: var(--radius);
                padding: 1rem;
            }}
            .activity-bar {{
                height: 24px;
                border-radius: 12px;
                overflow: hidden;
                display: flex;
                background: var(--gray-200);
            }}
            .activity-segment {{
                height: 100%;
                transition: width 0.3s;
            }}
            .activity-segment.code {{ background: var(--primary); }}
            .activity-segment.test {{ background: var(--success); }}
            .activity-segment.doc {{ background: var(--warning); }}
            .activity-legend {{
                display: flex;
                gap: 1.5rem;
                margin-top: 0.75rem;
                font-size: 0.8rem;
                color: var(--gray-600);
            }}
            .legend-item {{
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }}
            .dot {{
                width: 10px;
                height: 10px;
                border-radius: 50%;
            }}
            .dot.code {{ background: var(--primary); }}
            .dot.test {{ background: var(--success); }}
            .dot.doc {{ background: var(--warning); }}
            .contributors-list {{
                display: grid;
                gap: 0.5rem;
            }}
            .contributor-item {{
                display: flex;
                justify-content: space-between;
                padding: 0.75rem 1rem;
                background: var(--gray-50);
                border-radius: var(--radius);
            }}
            .contributor-name {{
                font-weight: 500;
                color: var(--gray-700);
            }}
            .contributor-stats {{
                color: var(--gray-500);
                font-size: 0.875rem;
            }}
        </style>
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
    
    def _html_executive_summary(
        self,
        payload: Dict[str, Any],
        code_analysis: Dict[str, Any],
        skills_analysis: Dict[str, Any],
        contribution_metrics: Dict[str, Any],
        contribution_ranking: Dict[str, Any],
    ) -> str:
        """Generate executive summary section with key insights."""
        
        insights = []
        
        # Code quality insight
        if code_analysis and code_analysis.get("success"):
            metrics = code_analysis.get("metrics", {})
            maintainability = metrics.get("average_maintainability", 0)
            complexity = metrics.get("average_complexity", 0)
            total_functions = metrics.get("total_functions", 0)
            total_classes = metrics.get("total_classes", 0)
            
            if maintainability >= 80:
                quality_level = "excellent"
                quality_text = "Excellent code quality"
            elif maintainability >= 60:
                quality_level = "good"
                quality_text = "Good code quality"
            elif maintainability >= 40:
                quality_level = "fair"
                quality_text = "Fair code quality"
            else:
                quality_level = "needs-work"
                quality_text = "Code needs improvement"
            
            insights.append(f'''
            <div class="insight-card">
                <div class="insight-icon">📊</div>
                <div class="insight-content">
                    <div class="insight-title">Code Quality</div>
                    <div class="quality-badge {quality_level}">{quality_text}</div>
                    <p class="insight-detail">
                        Maintainability: {maintainability:.0f}/100 • Complexity: {complexity:.1f} avg
                        <br>{total_functions:,} functions • {total_classes:,} classes
                    </p>
                </div>
            </div>
''')
            
            # Security issues
            quality = code_analysis.get("quality", {})
            security_issues = quality.get("security_issues", 0)
            if security_issues > 0:
                insights.append(f'''
            <div class="insight-card warning">
                <div class="insight-icon">⚠️</div>
                <div class="insight-content">
                    <div class="insight-title">Security Notice</div>
                    <p class="insight-detail">{security_issues} potential security issue(s) detected. Review recommended.</p>
                </div>
            </div>
''')
        
        # Skills insight
        if skills_analysis and skills_analysis.get("success"):
            skills = skills_analysis.get("skills", [])
            if skills:
                top_skills = [s.get("name", "") for s in skills[:5]]
                insights.append(f'''
            <div class="insight-card">
                <div class="insight-icon">🎯</div>
                <div class="insight-content">
                    <div class="insight-title">Key Technologies</div>
                    <p class="insight-detail">{", ".join(top_skills)}</p>
                </div>
            </div>
''')
        
        # Contribution insight
        if contribution_metrics:
            total_commits = contribution_metrics.get("total_commits", 0)
            lines_added = contribution_metrics.get("total_lines_added", 0)
            
            if total_commits > 0:
                insights.append(f'''
            <div class="insight-card">
                <div class="insight-icon">📈</div>
                <div class="insight-content">
                    <div class="insight-title">Development Activity</div>
                    <p class="insight-detail">{total_commits:,} commits with {lines_added:,} lines of code contributed</p>
                </div>
            </div>
''')
        
        # Contribution score
        if contribution_ranking:
            score = contribution_ranking.get("score", 0)
            level = contribution_ranking.get("level", "")
            if score > 0:
                insights.append(f'''
            <div class="insight-card highlight">
                <div class="insight-icon">🏆</div>
                <div class="insight-content">
                    <div class="insight-title">Contribution Score</div>
                    <div class="score-badge">{score:.0f}</div>
                    <p class="insight-detail">Level: {level}</p>
                </div>
            </div>
''')
        
        if not insights:
            return ""
        
        return f'''
        <div class="section executive-summary">
            <h2 class="section-title">Executive Summary</h2>
            <div class="insights-grid">
                {"".join(insights)}
            </div>
        </div>
        <style>
            .executive-summary {{
                background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
            }}
            .insights-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 1rem;
            }}
            .insight-card {{
                display: flex;
                gap: 1rem;
                padding: 1.25rem;
                background: white;
                border-radius: var(--radius);
                box-shadow: var(--shadow-sm);
                border-left: 4px solid var(--primary);
            }}
            .insight-card.warning {{
                border-left-color: var(--warning);
            }}
            .insight-card.highlight {{
                border-left-color: var(--success);
                background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
            }}
            .insight-icon {{
                font-size: 1.5rem;
                flex-shrink: 0;
            }}
            .insight-content {{
                flex: 1;
            }}
            .insight-title {{
                font-weight: 600;
                color: var(--gray-800);
                margin-bottom: 0.5rem;
            }}
            .insight-detail {{
                font-size: 0.875rem;
                color: var(--gray-600);
                line-height: 1.5;
            }}
            .score-badge {{
                display: inline-block;
                font-size: 1.5rem;
                font-weight: 700;
                color: var(--success);
                margin: 0.25rem 0;
            }}
        </style>
'''
    
    def _html_pdf_analysis_section(self, pdf_analysis: Dict[str, Any]) -> str:
        """Generate PDF document analysis section."""
        
        summaries = pdf_analysis.get("summaries", [])
        total_pdfs = pdf_analysis.get("total_pdfs", 0)
        successful = pdf_analysis.get("successful", 0)
        
        if not summaries:
            return ""
        
        pdf_cards = []
        for pdf in summaries[:10]:  # Limit to 10 PDFs
            if not pdf.get("success"):
                continue
                
            file_name = pdf.get("file_name", "Unknown")
            summary_text = pdf.get("summary", "")
            key_points = pdf.get("key_points", [])
            keywords = pdf.get("keywords", [])
            stats = pdf.get("statistics", {})
            
            # Truncate summary if too long
            if summary_text and len(summary_text) > 300:
                summary_text = summary_text[:297] + "..."
            
            # Format key points
            key_points_html = ""
            if key_points:
                points = [f"<li>{self._escape_html(p)}</li>" for p in key_points[:5]]
                key_points_html = f'<ul class="key-points">{"".join(points)}</ul>'
            
            # Format keywords as tags
            keywords_html = ""
            if keywords:
                keyword_tags = [
                    f'<span class="keyword-tag">{self._escape_html(kw.get("word", kw) if isinstance(kw, dict) else kw)}</span>'
                    for kw in keywords[:8]
                ]
                keywords_html = f'<div class="keywords-row">{" ".join(keyword_tags)}</div>'
            
            # Stats
            stats_html = ""
            if stats:
                page_count = stats.get("page_count", 0)
                word_count = stats.get("word_count", 0)
                if page_count or word_count:
                    stats_html = f'<p class="pdf-stats">{page_count} pages • {word_count:,} words</p>'
            
            pdf_cards.append(f'''
            <div class="pdf-card">
                <div class="pdf-header">
                    <span class="pdf-icon">📄</span>
                    <h3 class="pdf-title">{self._escape_html(file_name)}</h3>
                </div>
                {stats_html}
                {f'<p class="pdf-summary">{self._escape_html(summary_text)}</p>' if summary_text else ''}
                {key_points_html}
                {keywords_html}
            </div>
''')
        
        if not pdf_cards:
            return ""
        
        return f'''
        <div class="section">
            <h2 class="section-title">Document Analysis</h2>
            <p style="color: var(--gray-500); margin-bottom: 1.5rem;">
                {successful} of {total_pdfs} PDF documents analyzed successfully
            </p>
            <div class="pdf-grid">
                {"".join(pdf_cards)}
            </div>
        </div>
        <style>
            .pdf-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 1.5rem;
            }}
            .pdf-card {{
                background: var(--gray-50);
                border-radius: var(--radius);
                padding: 1.5rem;
                border: 1px solid var(--gray-200);
            }}
            .pdf-header {{
                display: flex;
                align-items: center;
                gap: 0.75rem;
                margin-bottom: 0.75rem;
            }}
            .pdf-icon {{
                font-size: 1.5rem;
            }}
            .pdf-title {{
                font-size: 1rem;
                font-weight: 600;
                color: var(--gray-800);
                word-break: break-word;
            }}
            .pdf-stats {{
                font-size: 0.75rem;
                color: var(--gray-500);
                margin-bottom: 0.75rem;
            }}
            .pdf-summary {{
                font-size: 0.875rem;
                color: var(--gray-600);
                line-height: 1.6;
                margin-bottom: 1rem;
            }}
            .key-points {{
                margin: 0.75rem 0;
                padding-left: 1.25rem;
                font-size: 0.875rem;
                color: var(--gray-600);
            }}
            .key-points li {{
                margin-bottom: 0.25rem;
            }}
            .keywords-row {{
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                margin-top: 0.75rem;
            }}
            .keyword-tag {{
                display: inline-block;
                padding: 0.25rem 0.5rem;
                background: var(--primary);
                color: white;
                border-radius: 4px;
                font-size: 0.7rem;
                font-weight: 500;
            }}
        </style>
'''
    
    def _html_media_analysis_section(self, media_analysis: Dict[str, Any]) -> str:
        """Generate media analysis section."""
        
        summary = media_analysis.get("summary", {})
        if not summary:
            return ""
        
        total_files = summary.get("total_files", 0)
        total_size = summary.get("total_size_bytes", 0)
        
        # Get breakdowns
        by_type = summary.get("by_type", {})
        images = by_type.get("images", {})
        videos = by_type.get("videos", {})
        audio = by_type.get("audio", {})
        
        if total_files == 0:
            return ""
        
        media_stats = []
        
        if images.get("count", 0) > 0:
            media_stats.append(f'''
            <div class="media-stat-card">
                <div class="media-stat-icon">🖼️</div>
                <div class="media-stat-value">{images.get("count", 0):,}</div>
                <div class="media-stat-label">Images</div>
                <div class="media-stat-size">{self._format_bytes(images.get("size_bytes", 0))}</div>
            </div>
''')
        
        if videos.get("count", 0) > 0:
            media_stats.append(f'''
            <div class="media-stat-card">
                <div class="media-stat-icon">🎬</div>
                <div class="media-stat-value">{videos.get("count", 0):,}</div>
                <div class="media-stat-label">Videos</div>
                <div class="media-stat-size">{self._format_bytes(videos.get("size_bytes", 0))}</div>
            </div>
''')
        
        if audio.get("count", 0) > 0:
            media_stats.append(f'''
            <div class="media-stat-card">
                <div class="media-stat-icon">🎵</div>
                <div class="media-stat-value">{audio.get("count", 0):,}</div>
                <div class="media-stat-label">Audio Files</div>
                <div class="media-stat-size">{self._format_bytes(audio.get("size_bytes", 0))}</div>
            </div>
''')
        
        if not media_stats:
            return ""
        
        return f'''
        <div class="section">
            <h2 class="section-title">Media Assets</h2>
            <p style="color: var(--gray-500); margin-bottom: 1.5rem;">
                {total_files:,} media files totaling {self._format_bytes(total_size)}
            </p>
            <div class="media-stats-grid">
                {"".join(media_stats)}
            </div>
        </div>
        <style>
            .media-stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 1rem;
            }}
            .media-stat-card {{
                text-align: center;
                padding: 1.5rem;
                background: var(--gray-50);
                border-radius: var(--radius);
                border: 1px solid var(--gray-200);
            }}
            .media-stat-icon {{
                font-size: 2rem;
                margin-bottom: 0.5rem;
            }}
            .media-stat-value {{
                font-size: 2rem;
                font-weight: 700;
                color: var(--primary);
            }}
            .media-stat-label {{
                font-size: 0.875rem;
                color: var(--gray-600);
                margin-top: 0.25rem;
            }}
            .media-stat-size {{
                font-size: 0.75rem;
                color: var(--gray-400);
                margin-top: 0.25rem;
            }}
        </style>
'''
    
    def _html_document_analysis_section(self, document_analysis: Dict[str, Any]) -> str:
        """Generate document analysis section (DOCX, etc.)."""
        
        documents = document_analysis.get("documents", [])
        total_docs = document_analysis.get("total_documents", 0)
        successful = document_analysis.get("successful", 0)
        
        if not documents:
            return ""
        
        doc_cards = []
        for doc in documents[:15]:  # Limit to 15 documents
            if not doc.get("success"):
                continue
                
            file_name = doc.get("file_name", "Unknown")
            summary_text = doc.get("summary", "")
            keywords = doc.get("keywords", [])
            metadata = doc.get("metadata", {})
            
            # Truncate summary if too long
            if summary_text and len(summary_text) > 400:
                summary_text = summary_text[:397] + "..."
            
            # Format metadata
            metadata_html = ""
            if metadata:
                word_count = metadata.get("word_count", 0)
                paragraph_count = metadata.get("paragraph_count", 0)
                reading_time = metadata.get("reading_time_minutes", 0)
                heading_count = metadata.get("heading_count", 0)
                headings = metadata.get("headings", [])
                
                stats_parts = []
                if word_count:
                    stats_parts.append(f"{word_count:,} words")
                if paragraph_count:
                    stats_parts.append(f"{paragraph_count} paragraphs")
                if reading_time:
                    stats_parts.append(f"~{reading_time:.0f} min read")
                
                if stats_parts:
                    metadata_html = f'<p class="doc-stats">{" • ".join(stats_parts)}</p>'
                
                # Show headings preview
                if headings:
                    headings_preview = headings[:3]
                    headings_html = f'''
                    <div class="doc-headings">
                        <span class="headings-label">Sections:</span>
                        {", ".join(self._escape_html(h) for h in headings_preview)}
                        {f" (+{len(headings) - 3} more)" if len(headings) > 3 else ""}
                    </div>
'''
                    metadata_html += headings_html
            
            # Format keywords as tags
            keywords_html = ""
            if keywords:
                keyword_tags = [
                    f'<span class="doc-keyword-tag">{self._escape_html(kw.get("word", kw) if isinstance(kw, dict) else kw)}</span>'
                    for kw in keywords[:10]
                ]
                keywords_html = f'<div class="doc-keywords-row">{" ".join(keyword_tags)}</div>'
            
            doc_cards.append(f'''
            <div class="doc-card">
                <div class="doc-header">
                    <span class="doc-icon">📝</span>
                    <h3 class="doc-title">{self._escape_html(file_name)}</h3>
                </div>
                {metadata_html}
                {f'<p class="doc-summary">{self._escape_html(summary_text)}</p>' if summary_text else ''}
                {keywords_html}
            </div>
''')
        
        if not doc_cards:
            return ""
        
        return f'''
        <div class="section">
            <h2 class="section-title">Document Analysis</h2>
            <p style="color: var(--gray-500); margin-bottom: 1.5rem;">
                {successful} of {total_docs} documents analyzed successfully
            </p>
            <div class="doc-grid">
                {"".join(doc_cards)}
            </div>
        </div>
        <style>
            .doc-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                gap: 1.5rem;
            }}
            .doc-card {{
                background: var(--gray-50);
                border-radius: var(--radius);
                padding: 1.5rem;
                border: 1px solid var(--gray-200);
            }}
            .doc-header {{
                display: flex;
                align-items: center;
                gap: 0.75rem;
                margin-bottom: 0.75rem;
            }}
            .doc-icon {{
                font-size: 1.5rem;
            }}
            .doc-title {{
                font-size: 1rem;
                font-weight: 600;
                color: var(--gray-800);
                word-break: break-word;
            }}
            .doc-stats {{
                font-size: 0.8rem;
                color: var(--gray-500);
                margin-bottom: 0.75rem;
            }}
            .doc-headings {{
                font-size: 0.8rem;
                color: var(--gray-600);
                margin-bottom: 0.75rem;
                padding: 0.5rem;
                background: var(--gray-100);
                border-radius: 4px;
            }}
            .headings-label {{
                font-weight: 600;
                color: var(--gray-700);
            }}
            .doc-summary {{
                font-size: 0.875rem;
                color: var(--gray-600);
                line-height: 1.6;
                margin-bottom: 1rem;
            }}
            .doc-keywords-row {{
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                margin-top: 0.75rem;
            }}
            .doc-keyword-tag {{
                display: inline-block;
                padding: 0.25rem 0.5rem;
                background: var(--secondary);
                color: white;
                border-radius: 4px;
                font-size: 0.7rem;
                font-weight: 500;
            }}
        </style>
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
