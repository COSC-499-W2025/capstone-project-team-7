**Features Proposal for Project**   
**Team Number:** 7  
**Team Members:** Joaquin Almora 68642073, Om Mistry 76297597, Samarth Grover 38220463, Aaron Banerjee 18186239, Jacob Damery 58995747, Vlad Petrariu 76370956

1. **Project Scope and Usage Scenario** 

Our project focuses on helping graduate students, early professional and freelance agents who need an effective way to consolidate and present their diverse body of work. These users often have various projects, code, research papers, and creative works scattered across different platforms and mediums, making it a challenge to present a clear picture of their skillset and contributions. For students and job seekers, the tool assists in resume and portfolio preparation by bringing together clear insights into your work that can provide the crucial edge needed in today's competitive market. On the other hand, for freelancers the system can provide a means to organize client deliverables and demonstrate expertise in their field through thorough reports. The tool will also benefit users that are not actively applying but still want an organized view of their personal output for self-improvement or academic growth.

2. **Proposed Solution**

Our proposed solution is to create a system that collects and manages projects and work into a file designed to showcase their work in a clear and summarized format. This application is a tool targeted towards graduating students and individuals looking to build their career. The software would scan files and repositories selected by the user within their own computer. After scanning the files, the application would extract key data and important information. The summarized file would include the data most relevant to the user’s needs and requirements. A graduating computer science student might want to scan their projects saved in their github account, the tool would then summarize their projects by use case, language used, target audience and other relevant information.  
The tool will be built using [next.js](http://next.js) for the front end, supabase as a secure and scalable data storage. Unlike old school resume builders that rely on manual input, our solution would extend the capabilities to also use automated discovery and formatting. Our edge compared to other teams will be the systems ability to automatically detect, analyze and organize the data per the users preference. Our solution is not only effective but also uniquely customizable for each individual user. 

3. **Use Cases**
   
![Use Case Diagram](https://github.com/COSC-499-W2025/capstone-project-team-7/blob/0b3d164bd8c68096cd1f4d92f18e9ede8feed8dc/docs/assets/useCase.png)

**Use Case 1: Select Artifact Locations**

* **Primary Actor:** User  
* **Description:** The user chooses directories or repositories for the system to scan  
* **Precondition:** The user is logged in and has access to file system locations  
* **Postcondition:** The selected directories are saved for scanning and analysis  
* **Main Scenario:**  
  * User navigates to file selection  
  * User chooses one or multiple directories  
  * System stores these paths  
* **Extensions**:   
  * If a directory is invalid or inaccessible, the system notifies the user and skips it   
  * If no directories are selected, scanning cannot proceed  
    

**Use Case 2: Scan & Index Artifacts**

* **Primary Actor:** User  
* **Description:** The system scans files in selected locations and records metadata  
* **Precondition:** Directories have been selected  
* **Postcondition:** Indexed data is saved in the system database and linked to the user’s session.  
* **Main Scenario:**  
  * User initiates a scan  
  * System processes files and extracts metadata  
  * Progress is shown in the UI  
  * Indexed Data is stored and displayed  
* **Extensions:** System skips files it cannot access and logs permission errors 


**Use Case 3: Analyze Artifacts**

* **Primary Actor:** User  
* **Description:** The system performs deeper analysis such as commit history, document history.  
* **Precondition:** Files have been scanned and indexed  
* **Postcondition:** Detailed analysis results are available for insights and saved to the database  
* **Main Scenario:**  
  * User requests analysis  
  * System identifies file types  
  * Specialized analysis is run per file type  
  * Results are saved  
* **Extensions:**   
  * Unknown file types are labeled “Other” and skipped from analysis

**Use Case 4: View Insights & Summaries**

* **Primary Actor:** User  
* **Description:** The user views summaries such as graphs, counts, and timelines of artifacts.  
* **Precondition:** Artifacts have been analyzed   
* **Postcondition:** Insights are displayed in the dashboard  
* **Main Scenario:**  
  * User opens dashboard  
  * System loads charts and metrics  
  * User explores summaries  
* **Extensions:**   
  * Dashboard auto-refreshes if new scans are run  
  * If no data is available, system shows an empty dashboard with instructions to run a scan

**Use Case 5: Manage Data Privacy**

* **Primary Actors:** User, Admin  
* **Description:** Both Users and Admins can manage data privacy. Users control which of their own files are included in analysis and can delete previously indexed data. Admins may apply broader privacy rules for compliance, such as excluding system directories or reinforcing organization-wide restrictions  
* **Precondition:** At least one scan is completed   
* **Postcondition:** Excluded or deleted files are no longer shown in results  
* **Main Scenario:**  
  * Actor navigates to the privacy management panel  
  * Actor selects files or folder to exclude  
  * The system removes related insights from the dashboard  
  * Actor deletes previously indexed data if necessary  
* **Extensions:**   
  * Deleted data can be restored during the same session via an undo option  
  * Admin sets organization-wide restrictions on sensitive folders   
  * If a restricted file is already in use in analysis, the system notifies the actor

**Use Case 6: Manage Configurations**

* **Primary Actors:** User, Admin  
* **Description:** Both Users and Admins can manage configurations. Users create and save personal scanning profile. Admins may define system-wide or default configurations applied across all users  
* **Precondition:** Application is running  
* **Postcondition:** Configurations are saved for reuse and applied automatically  
* **Main Scenario:**  
  * Actor opens system configuration settings  
  * Actor creates or edits a profile with parameters  
  * Actor saves the profile  
  * On restart, the system loads and default or most recent profile  
* **Extensions:**   
  * Admin sets a global default profile  
  * User sets a personal default profile  
  * Admin exports/imports profiles for backup or sharing   
    

**Use Case 7: Detect Duplicates**

* **Primary Actor:** User  
* **Description:** System flags duplicate files, user decides what to keep  
* **Precondition:** Files indexed  
* **Postcondition:** Duplicates resolved per user input  
* **Main Scenario:**  
  * User clicks duplicate detection  
  * System compares file contents  
  * Duplicate list shown  
  * User excludes or keeps duplicates  
* **Extensions:** If none are found, the system notifies the user.

**Use Case 8: Project Grouping & Organization**

* **Primary Actor:** User  
* **Description:** Groups files into projects by folder  
* **Precondition:** Files indexed  
* **Postcondition:** Projects created and viewable  
* **Main scenario:**  
  * System auto-groups files  
  * User reviews groups  
  * User renames, merges, or splits projects  
* **Extension:** System may suggest project names


**Use Case 9: Export Reports**

* **Primary Actor:** User  
* **Description:** User exports summaries into PDF/HTML/JSON  
* **Precondition:** insights available  
* **Postcondition:** Report file generated  
* **Main Scenario:**  
  * User selects “Export”  
  * User chooses filter, format  
  * System generates files  
* **Extensions:** Error shown if export or insight generation fails 


**Use Case 10: Search & Filter Data**

* **Primary Actor:** User  
* **Description:** User searches files/projects by filters  
* **Precondition:** Files indexed   
* **Postcondition:** Filtered results are stored temporarily and can be exported  
* **Main scenario:**  
  * User enters query  
  * System filters results  
  * Results displayed  
* **Extensions:** Saved queries reusable later

4. **Requirements, Testing, Requirement Verification**

Based on discussions in class and coming up with similar ideas for requirements, the following is the **technology stack** we have decided to move forward with.

- **NextJS** for Frontend  
- **SupaBase** for Database and Data Storage Needs  
- **RestFul** API for API Design/Needs  
- **Vercel** for our Cloud and Deployment requirements

For the Test Framework, we have decided to stick with the following frameworks to cover the several different bases and features we intend on developing

- **Unit**: Jest \+ React Testing Library  
- **Integration**: Jest \+ Supertest (+ Supabase CLI locally)  
- **E2E**: Playwright (on Vercel preview deployments)

| Requirement | Description | Test Cases | Who | H/M/E |
| :---: | :---: | :---: | :---: | :---: |
| **Functional Requirements** |  |  |  |  |
| F1. Artifact Discovery/Indexing | Scans all user-selected artifact locations. Segregates files by type and stores metadata (filename, type, creation date, last modified date, and file size). | User selects a directory and the software successfully lists all files with the correct file types and metadata. | Om | M |
| F2. Artifact Analysis | Detects programming languages by file extension. For Git Repos, counts commits and extracts first/last commit dates. Extracts metadata from documents (e.g., word count from Word, last edited dates from PDF/Excel). Extracts resolution (images) or duration (audio/video). | The user scans a folder containing various files, and the software displays all specialized information (commits, resolution, word count, etc.). | Joaquin | H |
| F3. Insights and Summaries | Displays overall count for artifacts by type. Shows a graph of the timeline based on creation or last edited dates. | If implemented, manual testing of the frontend/UI to confirm the dashboard updates when new artifacts are added or existing ones are modified. | Joaquin | M |
| F4. Data Privacy and Control | Allows users to manage data visibility. Users can exclude specific artifacts or folders from analysis. Users can delete previously indexed data from memory. | User excludes a folder, and the insights and summary information related to that folder are removed. The user deletes old data, and it disappears from the frontend dashboard. | Joaquin | M |
| F5. Configuration Management | Allows users to create and manage custom scanning settings and preferences. Users can save multiple scanning profiles (with different priorities/exclusion rules). The system remembers preferences between sessions, and users can set default directories. | The user creates a "Work Projects" profile, saves it, restarts the application, and the profile loads with the correct saved settings. | Om | H |
| F6. Duplicate Detection & Management | System identifies and manages duplicate files using content hash comparison to ensure accurate metrics. Users can view duplicate file lists and choose which instances to include or exclude from analysis. Flags potential duplicate Git projects. | The user has the same document in two folders; the system identifies duplicates and allows the user to exclude one instance from the metrics calculation. | Samarth | H |
| F7. Project Grouping & Organization | The system automatically organizes files into logical project groups based on directory structure and Git repository boundaries. Users can manually create, edit, or merge project groups. The system suggests project names based on folder/repo information. | Files within the same Git repository are automatically grouped, and the user can successfully split the group or rename the project. | Aaron | H |
| F8. Export & Reporting | The system generates formatted reports and data exports suitable for portfolio use. Creates PDF and HTML reports with summaries and key metrics. Users can export filtered data (by time period, type, or project). Generates JSON exports for external tool integration. | The user exports a 6-month coding activity report and receives a properly formatted PDF with charts and statistics. | Samarth | H |
| F9. Search & Filtering | Provides advanced search capabilities. Users can search by filename, project name, language, or date range. Offers filtering by file size, modification date, and custom tags. Allows users to save frequently used queries. | The user searches for "Python files modified in the last 30 days larger than 1KB" and receives accurate filtered results. | Aaron | M |
| **Non-Functional Requirements** |  |  |  |  |
| NF1. Basic Scan Performance | System should scan a typical student project folder (150-200 files) within 2 minutes. Show basic progress indication during scanning. UI should remain clickable during file processing. | Test how long project takes to scan a directory with a preselected directory containing 150 documents containing essays and various assignments, ensure that progress indication is always shown clearly, and the UI remains responsive during file processing. The test is successful if the dashboard loads insights on the user’s directory within 2 minutes, while the progress bar displays progress in the form of pa ercentage. Test fails if the progress bar gets stuck/if the dashboard does not load with user insights/if the UI components such as buttons do not trigger during the loading of insights dashboard.  | Vlad | E |
| NF2. File Type Analysis Performance | Applicaiton should analyze and categorize different file types (documents, code files, images, PDFs) within 30 seconds for a mixed directory of 100 files. Display file type breakdown immediately after analysis completion. | Test the system's ability to process a directory containing 25 Word documents, 25 Python files, 25 JPEG images, and 25 PDF files. Verify that the system correctly identifies each file type and displays categorization results within 30 seconds. Check that file type statistics appear in both numerical and visual chart formats. The test is successful if all file types are correctly identified and categorized within the time limit, with accurate counts displayed for each category. Test fails if file types are misidentified, if processing takes longer than 30 seconds, or if the categorization results are inaccurate or incomplete.  | Jacob | M |
| NF3. User Authentication and Data Privacy | System should securely authenticate users and ensure each user can only access their own scanned data. Login process should complete within 10 seconds on typical internet connections. | Test user registration and login functionality using valid credentials, then attempt to access another user's data through URL manipulation or direct database queries. Create two separate user accounts, scan different directories for each user, and verify complete data isolation. The test is successful if users can register and login within 10 seconds, can only view their own scanned data, and cannot access other users' information through any method. Test fails if authentication takes longer than 10 seconds, if users can view other users' data, or if data privacy is compromised in any way. | Om | H |
| NF4. Data Export and Report Generation | System should generate exportable reports in PDF and JSON formats within 60 seconds for datasets containing up to 200 files. Reports should include comprehensive analytics and visualizations. | Test report generation functionality by creating a comprehensive dataset with 200 mixed files (code, documents, images) and requesting both PDF and JSON exports. Verify that exports include file statistics, project timelines, language breakdowns, and identified patterns. Time the export process from user request to file download completion. The test is successful if both PDF and JSON reports generate within 60 seconds, contain accurate and complete data, include proper formatting and visualizations, and download successfully without corruption. Test fails if export takes longer than 60 seconds, if reports contain incorrect data, if files are corrupted or incomplete, or if the export process encounters errors. | Vlad | H |
| NF5. System Scalability and Resource Usage  | The application should maintain acceptable performance levels and not consume more than 4GB of system RAM during typical usage scenarios. Background processes should not interfere with other applications. |  Test system resource consumption during various operations: scanning large directories, generating complex analytics, displaying multiple charts simultaneously, and running background data processing. Monitor CPU usage, RAM consumption, and disk I/O using system monitoring tools throughout extended usage sessions. The test is successful if RAM usage stays below 2GB during all operations, CPU usage remains reasonable during background tasks, the system doesn't slow down other applications, and performance remains consistent during extended use. Test fails if memory usage exceeds 2GB, if the system significantly impacts other applications' performance, or if performance degrades substantially over time. | Samarth | E |
| NF6. File System Permission Handling |  Application should respect file system permissions and handle restricted directories gracefully without exposing sensitive system files or requiring administrative privileges. Scanner/parser should skip protected directories and continue processing accessible files. | Test the scanner's behavior when encountering system directories (Windows System32, macOS /private, Linux /root), password-protected folders, and files with restricted read permissions. Run scans as a standard user account without admin privileges and verify the system continues functioning when denied access to certain locations. The test is successful if the scanner skips inaccessible directories, logs permission errors appropriately, continues scanning accessible files, and never requests elevated privileges or crashes due to permission issues. Test fails if the system crashes on permission errors, requests admin access, or exposes files that should be restricted. | Aaron | H |

	

