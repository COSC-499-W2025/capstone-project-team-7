# Work Breakdown Structure

[**Phase 1: Consent & Data Access (Weeks 1–2)	1**](#phase-1:-consent-&-data-access-\(weeks-1–2\))  
[**Phase 2: File Upload, Validation & Parsing (Weeks 3–5)	1**](#phase-2:-file-upload,-validation-&-parsing-\(weeks-3–5\))  
[**Phase 3: Project Analysis Core (Weeks 6–8)	2**](#phase-3:-project-analysis-core-\(weeks-6–8\))  
[**Phase 4: Data Storage & Output Management (Weeks 9–10)	3**](#phase-4:-data-storage-&-output-management-\(weeks-9–10\))  
[**Phase 5: System Design & Testing (Weeks 11–12)	3**](#phase-5:-testing-\(weeks-11–12\).)

### **Phase 1: Consent & Data Access (Weeks 1–2)** {#phase-1:-consent-&-data-access-(weeks-1–2)}

**1.1 User Consent System**

* Implement a consent request mechanism before any data access or file upload.  
* Record and store user consent status in the local database.  
* Clearly communicate data privacy implications when requesting access.

**1.2 External Service Permission & Fallback Logic**

* Implement a permission prompt before using external services (e.g., LLMs).  
* Provide detailed information on what data would be shared externally.  
* Develop a fallback “local analysis” mode when external services are not permitted.

**1.3 Data Privacy & Ethical Handling**

* Document all data-handling rules and ensure compliance with privacy guidelines.  
* Establish secure temporary storage for user files during processing.

*Deliverable:* Consent flow prototype and privacy compliance documentation.

### **Phase 2: File Upload, Validation & Parsing (Weeks 3–5)** {#phase-2:-file-upload,-validation-&-parsing-(weeks-3–5)}

**2.1 File Upload & Validation**

* Implement functionality to upload zipped folders containing nested projects.  
* Validate uploaded file formats and return clear, structured error messages for unsupported or invalid uploads.

**2.2 Zip Parsing & Extraction Engine**

* Develop a recursive parsing module (fallback) to extract all files and subfolders from a zip archive.  
* Capture key metadata (file name, type, size, created/modified date).

**2.3 Error Handling & Logging**

* Implement robust error-handling for invalid zip structures, permission issues, or corrupted files.  
* Store logs for later debugging and test verification.

*Deliverable:* Working file parsing module that outputs extracted data in JSON, CSV, or plain text format.

### **Phase 3: Project Analysis Core (Weeks 6–8)** {#phase-3:-project-analysis-core-(weeks-6–8)}

**3.1 Project Identification**

* Detects whether a project is individual or collaborative using file authorship and Git commit data.  
* Identify programming languages and frameworks used in coding projects.

**3.2 Contribution Analysis**

* Extract and compute contribution metrics (commits, edit frequency, duration, and activity type such as code, test, documentation, design).  
* Estimate individual contributions for collaborative projects.

**3.3 Skill Extraction**

* Analyze code and documentation content to identify recurring technical skills or keywords.  
* Summarize key skills per project for résumé or portfolio use.

**3.4 Alternative Local Analysis**

* Provide in-system analysis alternatives when external service usage is denied.

*Deliverable:* Text-based (JSON/CSV) project summaries including skills, contributions, and metrics.

### **Phase 4: Data Storage & Output Management (Weeks 9–10)** {#phase-4:-data-storage-&-output-management-(weeks-9–10)}

**4.1 Database & Configuration Storage**

* Store parsed results, user configurations, and previous analysis data for reuse.  
* Retrieve previously generated portfolio or résumé information on demand.

**4.2 Project Ranking & Summarization**

* Rank projects by contribution weight and importance.  
* Summarize top-ranked projects for reporting.

**4.3 Chronological Data Output**

* Generate chronological lists of projects and exercised skills.  
* Support export in structured text formats (JSON, CSV, or plain text).

**4.4 Data Deletion & Integrity Management**

* Implement deletion functionality that preserves shared data between multiple reports.

*Deliverable:* Functional backend producing text-based project summaries and ranked reports.

### **Phase 5: Testing (Weeks 11–12)**. {#phase-5:-testing-(weeks-11–12).}

*Note: Testing will take place simultaneously with development but this phase is focused on more rigorous testing and finding any issues with the system*  
**5.1 Testing Framework Setup**

* Set up testing using pytest for unit, integration, and functional testing.  
* Validate complete pipeline: file upload → parse → analyze → output.  
* Test invalid uploads, denied external access, and corrupted file handling.

**5.2 Performance & Privacy Testing**

* Test scalability on large zipped folders.  
* Verify that no unauthorized data is transmitted externally.


**5.3 Documentation & Reporting**

* Compile test result summaries, pass/fail matrices, and milestone reports.

*Deliverable:* Complete comprehensive testing report.  