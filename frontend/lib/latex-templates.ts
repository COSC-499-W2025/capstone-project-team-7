/**
 * LaTeX Resume Templates
 * 
 * These templates are based on popular open-source resume templates.
 * Users can select a base template and customize it.
 */

import type { ResumeTemplate, ResumeStructuredData } from "@/types/user-resume";

// ============================================================================
// Jake's Resume Template (MIT License)
// Based on: https://github.com/jakegut/resume
// ============================================================================

export const JAKE_TEMPLATE = `%-------------------------
% Resume in Latex
% Author : Jake Gutierrez
% Based off of: https://github.com/sb2nov/resume
% License : MIT
%------------------------

\\documentclass[letterpaper,11pt]{article}

\\usepackage{latexsym}
\\usepackage[empty]{fullpage}
\\usepackage{titlesec}
\\usepackage{marvosym}
\\usepackage[usenames,dvipsnames]{color}
\\usepackage{verbatim}
\\usepackage{enumitem}
\\usepackage[hidelinks]{hyperref}
\\usepackage{fancyhdr}
\\usepackage[english]{babel}
\\usepackage{tabularx}
\\input{glyphtounicode}

\\pagestyle{fancy}
\\fancyhf{} % clear all header and footer fields
\\fancyfoot{}
\\renewcommand{\\headrulewidth}{0pt}
\\renewcommand{\\footrulewidth}{0pt}

% Adjust margins
\\addtolength{\\oddsidemargin}{-0.5in}
\\addtolength{\\evensidemargin}{-0.5in}
\\addtolength{\\textwidth}{1in}
\\addtolength{\\topmargin}{-.5in}
\\addtolength{\\textheight}{1.0in}

\\urlstyle{same}

\\raggedbottom
\\raggedright
\\setlength{\\tabcolsep}{0in}

% Sections formatting
\\titleformat{\\section}{
  \\vspace{-4pt}\\scshape\\raggedright\\large
}{}{0em}{}[\\color{black}\\titlerule \\vspace{-5pt}]

% Ensure that generate pdf is machine readable/ATS parsable
\\pdfgentounicode=1

%-------------------------
% Custom commands
\\newcommand{\\resumeItem}[1]{
  \\item\\small{
    {#1 \\vspace{-2pt}}
  }
}

\\newcommand{\\resumeSubheading}[4]{
  \\vspace{-2pt}\\item
    \\begin{tabular*}{0.97\\textwidth}[t]{l@{\\extracolsep{\\fill}}r}
      \\textbf{#1} & #2 \\\\
      \\textit{\\small#3} & \\textit{\\small #4} \\\\
    \\end{tabular*}\\vspace{-7pt}
}

\\newcommand{\\resumeSubSubheading}[2]{
    \\item
    \\begin{tabular*}{0.97\\textwidth}{l@{\\extracolsep{\\fill}}r}
      \\textit{\\small#1} & \\textit{\\small #2} \\\\
    \\end{tabular*}\\vspace{-7pt}
}

\\newcommand{\\resumeProjectHeading}[2]{
    \\item
    \\begin{tabular*}{0.97\\textwidth}{l@{\\extracolsep{\\fill}}r}
      \\small#1 & #2 \\\\
    \\end{tabular*}\\vspace{-7pt}
}

\\newcommand{\\resumeSubItem}[1]{\\resumeItem{#1}\\vspace{-4pt}}

\\renewcommand\\labelitemii{$\\vcenter{\\hbox{\\tiny$\\bullet$}}$}

\\newcommand{\\resumeSubHeadingListStart}{\\begin{itemize}[leftmargin=0.15in, label={}]}
\\newcommand{\\resumeSubHeadingListEnd}{\\end{itemize}}
\\newcommand{\\resumeItemListStart}{\\begin{itemize}}
\\newcommand{\\resumeItemListEnd}{\\end{itemize}\\vspace{-5pt}}

%-------------------------------------------
%%%%%%  RESUME STARTS HERE  %%%%%%%%%%%%%%%%%%%%%%%%%%%%


\\begin{document}

%----------HEADING----------
\\begin{center}
    \\textbf{\\Huge \\scshape Your Name} \\\\ \\vspace{1pt}
    \\small 123-456-7890 $|$ \\href{mailto:you@email.com}{\\underline{you@email.com}} $|$ 
    \\href{https://linkedin.com/in/yourprofile}{\\underline{linkedin.com/in/yourprofile}} $|$
    \\href{https://github.com/yourusername}{\\underline{github.com/yourusername}}
\\end{center}


%-----------EDUCATION-----------
\\section{Education}
  \\resumeSubHeadingListStart
    \\resumeSubheading
      {University Name}{City, State}
      {Degree in Field of Study}{Aug. 20XX -- May 20XX}
  \\resumeSubHeadingListEnd


%-----------EXPERIENCE-----------
\\section{Experience}
  \\resumeSubHeadingListStart

    \\resumeSubheading
      {Job Title}{Start Date -- End Date}
      {Company Name}{City, State}
      \\resumeItemListStart
        \\resumeItem{Describe your accomplishments and responsibilities}
        \\resumeItem{Use action verbs and quantify results when possible}
        \\resumeItem{Focus on impact and outcomes}
      \\resumeItemListEnd

  \\resumeSubHeadingListEnd


%-----------PROJECTS-----------
\\section{Projects}
    \\resumeSubHeadingListStart
      \\resumeProjectHeading
          {\\textbf{Project Name} $|$ \\emph{Technologies Used}}{Date Range}
          \\resumeItemListStart
            \\resumeItem{Describe what you built}
            \\resumeItem{Highlight key features or technical achievements}
            \\resumeItem{Mention the impact or results}
          \\resumeItemListEnd
    \\resumeSubHeadingListEnd


%-----------TECHNICAL SKILLS-----------
\\section{Technical Skills}
 \\begin{itemize}[leftmargin=0.15in, label={}]
    \\small{\\item{
     \\textbf{Languages}{: Python, JavaScript, TypeScript, Java, C++} \\\\
     \\textbf{Frameworks}{: React, Node.js, FastAPI, Next.js} \\\\
     \\textbf{Developer Tools}{: Git, Docker, VS Code, Linux} \\\\
     \\textbf{Libraries}{: pandas, NumPy, TensorFlow}
    }}
 \\end{itemize}


%-------------------------------------------
\\end{document}
`;

// ============================================================================
// Classic Template - Traditional professional layout
// ============================================================================

export const CLASSIC_TEMPLATE = `%-------------------------
% Classic Resume Template
% A traditional, professional resume layout
%------------------------

\\documentclass[11pt,a4paper]{article}

\\usepackage[margin=0.75in]{geometry}
\\usepackage{enumitem}
\\usepackage{hyperref}
\\usepackage{titlesec}

\\pagestyle{empty}

% Section formatting
\\titleformat{\\section}{\\large\\bfseries}{}{0em}{}[\\titlerule]
\\titlespacing{\\section}{0pt}{12pt}{6pt}

\\begin{document}

%----------HEADING----------
\\begin{center}
    {\\LARGE\\bfseries Your Name}\\\\[4pt]
    City, State $\\bullet$ (123) 456-7890 $\\bullet$ you@email.com\\\\
    linkedin.com/in/yourprofile $\\bullet$ github.com/yourusername
\\end{center}

%-----------SUMMARY-----------
\\section{Professional Summary}
Results-driven software developer with X years of experience in building scalable applications. Skilled in full-stack development with expertise in modern frameworks and cloud technologies.

%-----------EXPERIENCE-----------
\\section{Experience}

\\textbf{Job Title} \\hfill Start Date -- End Date\\\\
\\textit{Company Name, City, State}
\\begin{itemize}[leftmargin=*, nosep]
    \\item Accomplishment or responsibility
    \\item Accomplishment or responsibility
    \\item Accomplishment or responsibility
\\end{itemize}

%-----------EDUCATION-----------
\\section{Education}

\\textbf{Degree in Field} \\hfill Graduation Date\\\\
\\textit{University Name, City, State}

%-----------SKILLS-----------
\\section{Skills}

\\textbf{Programming:} Python, JavaScript, TypeScript, Java\\\\
\\textbf{Frameworks:} React, Node.js, FastAPI\\\\
\\textbf{Tools:} Git, Docker, AWS

\\end{document}
`;

// ============================================================================
// Modern Template - Contemporary design with sidebar
// ============================================================================

export const MODERN_TEMPLATE = `%-------------------------
% Modern Resume Template
% Contemporary design with clean sections
%------------------------

\\documentclass[11pt]{article}

\\usepackage[margin=0.6in]{geometry}
\\usepackage{xcolor}
\\usepackage{enumitem}
\\usepackage{hyperref}
\\usepackage{titlesec}
\\usepackage{fontawesome5}

\\definecolor{primary}{HTML}{2563EB}
\\definecolor{gray}{HTML}{6B7280}

\\pagestyle{empty}

% Section formatting
\\titleformat{\\section}{\\color{primary}\\large\\bfseries}{}{0em}{}[\\color{primary}\\titlerule]
\\titlespacing{\\section}{0pt}{10pt}{6pt}

\\begin{document}

%----------HEADING----------
\\begin{center}
    {\\Huge\\bfseries Your Name}\\\\[6pt]
    {\\color{gray}\\faPhone\\ (123) 456-7890 \\quad
    \\faEnvelope\\ you@email.com \\quad
    \\faLinkedin\\ linkedin.com/in/you \\quad
    \\faGithub\\ github.com/you}
\\end{center}

\\vspace{8pt}

%-----------EXPERIENCE-----------
\\section{Experience}

\\textbf{Job Title} \\hfill {\\color{gray}Start -- End}\\\\
{\\color{gray}\\textit{Company Name $\\bullet$ City, State}}
\\begin{itemize}[leftmargin=*, nosep, topsep=4pt]
    \\item Accomplishment using action verbs and metrics
    \\item Another accomplishment with quantifiable results
\\end{itemize}

\\vspace{6pt}

%-----------PROJECTS-----------
\\section{Projects}

\\textbf{Project Name} | {\\color{gray}\\textit{Tech Stack}} \\hfill {\\color{gray}Date}
\\begin{itemize}[leftmargin=*, nosep, topsep=4pt]
    \\item Brief description of what you built
    \\item Key technical achievement or impact
\\end{itemize}

\\vspace{6pt}

%-----------EDUCATION-----------
\\section{Education}

\\textbf{Degree in Field} \\hfill {\\color{gray}Graduation Date}\\\\
{\\color{gray}\\textit{University Name}}

\\vspace{6pt}

%-----------SKILLS-----------
\\section{Skills}

\\textbf{Languages:} Python, JavaScript, TypeScript, Go\\\\
\\textbf{Technologies:} React, Node.js, PostgreSQL, Docker, AWS

\\end{document}
`;

// ============================================================================
// Minimal Template - Ultra-clean minimalist design
// ============================================================================

export const MINIMAL_TEMPLATE = `%-------------------------
% Minimal Resume Template
% Clean, content-focused design
%------------------------

\\documentclass[11pt]{article}

\\usepackage[margin=0.75in]{geometry}
\\usepackage{enumitem}
\\usepackage{hyperref}

\\pagestyle{empty}
\\setlength{\\parindent}{0pt}

\\begin{document}

%----------HEADING----------
{\\Large\\bfseries Your Name}\\\\[2pt]
you@email.com $\\cdot$ (123) 456-7890 $\\cdot$ github.com/you

\\vspace{12pt}
\\hrule
\\vspace{12pt}

%-----------EXPERIENCE-----------
{\\large\\bfseries Experience}\\\\[6pt]

\\textbf{Job Title}, Company Name \\hfill Start -- End
\\begin{itemize}[leftmargin=12pt, nosep]
    \\item Key accomplishment
    \\item Key accomplishment
\\end{itemize}

\\vspace{8pt}

%-----------PROJECTS-----------
{\\large\\bfseries Projects}\\\\[6pt]

\\textbf{Project Name} -- Brief description of the project and technologies used.

\\vspace{8pt}

%-----------EDUCATION-----------
{\\large\\bfseries Education}\\\\[6pt]

\\textbf{Degree}, University Name \\hfill Year

\\vspace{8pt}

%-----------SKILLS-----------
{\\large\\bfseries Skills}\\\\[6pt]

Python, JavaScript, React, Node.js, PostgreSQL, Docker, Git

\\end{document}
`;

// ============================================================================
// Custom Template - Empty starting point
// ============================================================================

export const CUSTOM_TEMPLATE = `%-------------------------
% Custom Resume
% Start from scratch with your own design
%------------------------

\\documentclass[11pt]{article}

\\usepackage[margin=1in]{geometry}
\\usepackage{hyperref}

\\pagestyle{empty}

\\begin{document}

% Start building your resume here!

{\\Large\\bfseries Your Name}

\\vspace{12pt}

Add your content...

\\end{document}
`;

// ============================================================================
// Template Map
// ============================================================================

export const LATEX_TEMPLATES: Record<ResumeTemplate, string> = {
  jake: JAKE_TEMPLATE,
  classic: CLASSIC_TEMPLATE,
  modern: MODERN_TEMPLATE,
  minimal: MINIMAL_TEMPLATE,
  custom: CUSTOM_TEMPLATE,
};

/**
 * Get the default LaTeX content for a template
 */
export function getTemplateLatex(template: ResumeTemplate): string {
  return LATEX_TEMPLATES[template] || JAKE_TEMPLATE;
}

/**
 * Generate LaTeX from structured data using Jake's template format
 */
export function generateLatexFromStructuredData(data: ResumeStructuredData): string {
  const lines: string[] = [];
  
  // Preamble (Jake's template)
  lines.push(`%-------------------------
% Resume generated from structured data
% Based on Jake's Resume Template
%------------------------

\\documentclass[letterpaper,11pt]{article}

\\usepackage{latexsym}
\\usepackage[empty]{fullpage}
\\usepackage{titlesec}
\\usepackage{marvosym}
\\usepackage[usenames,dvipsnames]{color}
\\usepackage{verbatim}
\\usepackage{enumitem}
\\usepackage[hidelinks]{hyperref}
\\usepackage{fancyhdr}
\\usepackage[english]{babel}
\\usepackage{tabularx}
\\input{glyphtounicode}

\\pagestyle{fancy}
\\fancyhf{}
\\fancyfoot{}
\\renewcommand{\\headrulewidth}{0pt}
\\renewcommand{\\footrulewidth}{0pt}

\\addtolength{\\oddsidemargin}{-0.5in}
\\addtolength{\\evensidemargin}{-0.5in}
\\addtolength{\\textwidth}{1in}
\\addtolength{\\topmargin}{-.5in}
\\addtolength{\\textheight}{1.0in}

\\urlstyle{same}
\\raggedbottom
\\raggedright
\\setlength{\\tabcolsep}{0in}

\\titleformat{\\section}{
  \\vspace{-4pt}\\scshape\\raggedright\\large
}{}{0em}{}[\\color{black}\\titlerule \\vspace{-5pt}]

\\pdfgentounicode=1

\\newcommand{\\resumeItem}[1]{
  \\item\\small{{#1 \\vspace{-2pt}}}
}

\\newcommand{\\resumeSubheading}[4]{
  \\vspace{-2pt}\\item
    \\begin{tabular*}{0.97\\textwidth}[t]{l@{\\extracolsep{\\fill}}r}
      \\textbf{#1} & #2 \\\\
      \\textit{\\small#3} & \\textit{\\small #4} \\\\
    \\end{tabular*}\\vspace{-7pt}
}

\\newcommand{\\resumeProjectHeading}[2]{
    \\item
    \\begin{tabular*}{0.97\\textwidth}{l@{\\extracolsep{\\fill}}r}
      \\small#1 & #2 \\\\
    \\end{tabular*}\\vspace{-7pt}
}

\\newcommand{\\resumeSubHeadingListStart}{\\begin{itemize}[leftmargin=0.15in, label={}]}
\\newcommand{\\resumeSubHeadingListEnd}{\\end{itemize}}
\\newcommand{\\resumeItemListStart}{\\begin{itemize}}
\\newcommand{\\resumeItemListEnd}{\\end{itemize}\\vspace{-5pt}}

\\begin{document}
`);

  // Contact/Heading
  if (data.contact) {
    const c = data.contact;
    const contactParts: string[] = [];
    if (c.phone) contactParts.push(c.phone);
    // URLs inside \href{} should NOT be escaped - hyperref handles URL characters.
    // Only the display text needs escaping.
    if (c.email) contactParts.push(`\\href{mailto:${c.email}}{\\underline{${escapeLatex(c.email)}}}`);
    if (c.linkedin_url) contactParts.push(`\\href{${c.linkedin_url}}{\\underline{${escapeLatex(extractDomain(c.linkedin_url))}}}`);
    if (c.github_url) contactParts.push(`\\href{${c.github_url}}{\\underline{${escapeLatex(extractDomain(c.github_url))}}}`);
    
    lines.push(`\\begin{center}
    \\textbf{\\Huge \\scshape ${escapeLatex(c.full_name)}} \\\\ \\vspace{1pt}
    \\small ${contactParts.join(' $|$ ')}
\\end{center}
`);
  }

  // Education
  if (data.education && data.education.length > 0) {
    lines.push(`\\section{Education}
  \\resumeSubHeadingListStart`);
    for (const edu of data.education) {
      const dateRange = formatDateRange(edu.start_date, edu.end_date);
      lines.push(`    \\resumeSubheading
      {${escapeLatex(edu.institution)}}{${escapeLatex(edu.location || '')}}
      {${escapeLatex(edu.degree)}${edu.field_of_study ? ', ' + escapeLatex(edu.field_of_study) : ''}}{${dateRange}}`);
    }
    lines.push(`  \\resumeSubHeadingListEnd
`);
  }

  // Experience
  if (data.experience && data.experience.length > 0) {
    lines.push(`\\section{Experience}
  \\resumeSubHeadingListStart`);
    for (const exp of data.experience) {
      const dateRange = formatDateRange(exp.start_date, exp.end_date);
      lines.push(`
    \\resumeSubheading
      {${escapeLatex(exp.position)}}{${dateRange}}
      {${escapeLatex(exp.company)}}{${escapeLatex(exp.location || '')}}`);
      if (exp.bullets && exp.bullets.length > 0) {
        lines.push(`      \\resumeItemListStart`);
        for (const bullet of exp.bullets) {
          lines.push(`        \\resumeItem{${escapeLatex(bullet)}}`);
        }
        lines.push(`      \\resumeItemListEnd`);
      }
    }
    lines.push(`
  \\resumeSubHeadingListEnd
`);
  }

  // Projects
  if (data.projects && data.projects.length > 0) {
    lines.push(`\\section{Projects}
    \\resumeSubHeadingListStart`);
    for (const proj of data.projects) {
      const dateRange = formatDateRange(proj.start_date, proj.end_date);
      const techStr = proj.technologies ? ` $|$ \\emph{${escapeLatex(proj.technologies)}}` : '';
      lines.push(`      \\resumeProjectHeading
          {\\textbf{${escapeLatex(proj.name)}}${techStr}}{${dateRange}}`);
      if (proj.bullets && proj.bullets.length > 0) {
        lines.push(`          \\resumeItemListStart`);
        for (const bullet of proj.bullets) {
          lines.push(`            \\resumeItem{${escapeLatex(bullet)}}`);
        }
        lines.push(`          \\resumeItemListEnd`);
      }
    }
    lines.push(`    \\resumeSubHeadingListEnd
`);
  }

  // Skills
  if (data.skills) {
    const skillLines: string[] = [];
    if (data.skills.languages?.length) {
      skillLines.push(`     \\textbf{Languages}{: ${escapeLatex(data.skills.languages.join(', '))}} \\\\`);
    }
    if (data.skills.frameworks?.length) {
      skillLines.push(`     \\textbf{Frameworks}{: ${escapeLatex(data.skills.frameworks.join(', '))}} \\\\`);
    }
    if (data.skills.developer_tools?.length) {
      skillLines.push(`     \\textbf{Developer Tools}{: ${escapeLatex(data.skills.developer_tools.join(', '))}} \\\\`);
    }
    if (data.skills.libraries?.length) {
      skillLines.push(`     \\textbf{Libraries}{: ${escapeLatex(data.skills.libraries.join(', '))}}`);
    }
    
    if (skillLines.length > 0) {
      lines.push(`\\section{Technical Skills}
 \\begin{itemize}[leftmargin=0.15in, label={}]
    \\small{\\item{
${skillLines.join('\n')}
    }}
 \\end{itemize}
`);
    }
  }

  lines.push(`\\end{document}`);
  
  return lines.join('\n');
}

/**
 * Escape special LaTeX characters using single-pass replacement
 * to avoid corrupting backslash sequences (e.g., \textbackslash{} → \textbackslash\{\})
 */
function escapeLatex(text: string): string {
  const replacements: Record<string, string> = {
    '\\': '\\textbackslash{}',
    '&': '\\&',
    '%': '\\%',
    '$': '\\$',
    '#': '\\#',
    '_': '\\_',
    '{': '\\{',
    '}': '\\}',
    '~': '\\textasciitilde{}',
    '^': '\\textasciicircum{}',
  };
  
  // Single-pass regex avoids double-escaping braces in \textbackslash{}
  return text.replace(/[\\&%$#_{}~^]/g, (char) => replacements[char]);
}

/**
 * Format date range for display
 */
function formatDateForLatex(dateStr: string | undefined): string {
  if (!dateStr) return '';
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;
    return date.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateStr;
  }
}

function formatDateRange(start?: string, end?: string): string {
  if (!start && !end) return '';
  const formattedStart = formatDateForLatex(start);
  const formattedEnd = formatDateForLatex(end);

  if (formattedStart && formattedEnd) return `${formattedStart} -- ${formattedEnd}`;
  if (formattedStart) return `${formattedStart} -- Present`;
  return formattedEnd || '';
}

/**
 * Extract display-friendly domain from URL
 */
function extractDomain(url: string): string {
  try {
    const parsed = new URL(url);
    return parsed.hostname.replace(/^www\./, '') + parsed.pathname.replace(/\/$/, '');
  } catch {
    return url;
  }
}
