## Component Diagram
<pre>
  ---
config:
  theme: redux
---
flowchart TD

  %% %%{init: {'flowchart': {'nodeSpacing': 50, 'rankSpacing': 60}}}%%

  subgraph DS["Data Sources Layer"]
        FS["File System<br>Documents, Code, Media Files"]
        GR["Git Repositories<br>Commit History, Branch Data"]
        PM["Project Metadata<br>package.json, requirements.txt"]
        AD["Application Data<br>IDE Logs, Browser History"]
        CS["Cloud Storage<br>Google Drive, Dropbox, OneDrive"]
  end

  subgraph CP["Data Collection and Processing Layer"]
        %% invisible padding block to add vertical space below the title
        subgraph CPpad[" "]
        end
        SC["File Scanner<br>Cross-platform walker<br>File type detection<br>Metadata extraction"]
        CA["Content Analyzers<br>Code analysis<br>Document parsing<br>Media processing"]
        PD["Project Detector<br>Boundary detection<br>Technology stack<br>Categorization"]
        PF["Privacy Filter<br>Sensitive data detection<br>Anonymization<br>Consent management"]
        DN["Data Normalizer<br>Format standardization<br>Schema validation<br>Quality checks"]
        IP["Incremental Processor<br>Change detection<br>Delta processing<br>Cache management"]
  end

  style CPpad fill:none,stroke:none,opacity:0;

  subgraph ST["Data Storage Layer"]
        RDS["Raw Data Store<br>File metadata, content hashes"]
        PRD["Processed Data<br>Projects, artifacts, metrics"]
        AC["Analytics Cache<br>Computed insights, trends"]
        UP["User Preferences<br>Settings, privacy choices"]
        ED["Export Data<br>Portfolio ready formats"]
  end

  subgraph BL["Business Logic and Analytics Layer"]
        subgraph BLpad[" "]
        end
        IE["Insight Engine<br>Skill extraction<br>Productivity analysis<br>Project evolution"]
        MC["Metrics Calculator<br>LOC counting<br>Complexity metrics<br>Time tracking"]
        PG["Portfolio Generator<br>Template system<br>Data formatting<br>Export options"]
        TA["Trend Analyzer<br>Activity patterns<br>Growth tracking<br>Recommendations"]
        RB["Report Builder<br>Dashboard data<br>Resume metrics<br>Visual summaries"]
        SCH["Scheduler<br>Periodic scans<br>Background updates<br>Maintenance tasks"]
  end

  style BLpad fill:none,stroke:none,opacity:0;

  subgraph API["API and Interface Layer Future"]
        REST["REST API<br>Project &amp; Analytics endpoints<br>Config panel"]
        WD["Web Dashboard<br>Interactive visualizations<br>Real-time metrics"]
        PGUI["Portfolio Generator UI<br>Template selection<br>Customization"]
        CLI["CLI Interface<br>Scan commands<br>Export utilities<br>Config tools"]
  end

  DS --> CP
  CP --> ST
  ST --> BL
  BL --> API
</pre>
