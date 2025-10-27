# Capstone Team 7 Logs

## Week 8 (October 20 - 26)

This week we continued developing the backend, moving from setup into more functional implementation. Alongside expanding the CLI to better support backend workflows.

**Joaquin:** This week I improved the CLI’s parsing features. I added safer zip handling that skips unnecessary folders, made the table display reusable, and introduced two new flags: --relevant-only (to include only key project files) and --code (to show language breakdowns). The README now includes examples, and all new features are tested and verified to work.

**Jacob:** This week I worked on the backend by starting the Supabase integration. I set up the environment with the project URL and anon key, created the initial database schema, and began defining storage policies. I also started on an upload test to check file and metadata handling, but ran into bugs that I’m still working through. While I didn’t get to a finished PR yet, this lays the base for connecting secure storage to the CLI in the next step.

**Vlad:** Focused on integrating Supabase authentication and consent management into the backend CLI as part of issue #86. Extended auth_cli.py to support secure sign-up, log-in, and access-token retrieval directly from the terminal, allowing verified users to authenticate and submit consent records to the Supabase database. Added a new SQL migration file, 04_consent_policies.sql, to define row level security (RLS) policies ensuring that each user can only access or modify their own consent data. Tested the complete CLI workflow end to end, including token handling, database persistence, and error cases and confirmed seamless interaction between the authentication layer and the Consent Validation Module. 

**Aaron:** This week I refactored the config manager class to work with the database. This involved ensuring crud operations work with the supabase db we setup. I also added testing for all use cases. I then began the local analysis for coding feature, but yet to make a PR for that. The branch has the beginning implementation now for analyzing files for coding metrics. I made a PR for the refactored config manager that uses the db now, this includes new methods like 'get_allowed_extensions()' and changing code so that we store to the database.

**Om:** Implemented a privacy‑first local PDF analysis pipeline including a robust PDFParser that extracts text and metadata with configurable size and page limits, and a PDFSummarizer that uses an in‑house TF‑IDF extractive approach with sentence filtering, tokenization, keyword extraction, and document statistics. I added a user-friendly CLI `(pdf_cli.py)` plus quick-reference docs to parse, summarize, batch-process, and inspect PDFs. The test suite was expanded to 68 tests covering edge cases and integration paths, yielding 100% coverage for the summarizer and high coverage for the parser. I migrated from the deprecated PyPDF2 to pypdf, added a conftest import helper for cleaner tests, and exposed factory functions `(create_parser, create_summarizer)`. For Supabase consent flows I hardened `auth_cli.py` to prompt securely for passwords, added revoke/delete support, and updated SQL with an RLS DELETE policy for safe consent revocation. README and CLI references were updated for usage and CI-friendly testing, and added minor docs and examples.

**Samarth:** Worked on developing the LLM-powered summarization and analysis module for the system, generating structured insights from portfolio data. Implemented the `summarize_tagged_file()` and `analyze_project()` functions to produce detailed summaries, technical highlights, and qualitative analysis for resume-ready reports. Also built helper functions including `chunk_and_summarize()` for efficient large-file handling, `_count_tokens()` for dynamic token measurement, and `_make_llm_call()` for standardized LLM communication. Finally, added `suggest_feedback()` to deliver personalized career aligned insights. 

All the updates this week build on each other to make the whole system smarter and more reliable. The new CLI features make it easier to parse and display project data, while the authentication and consent setup ensures everything stays secure and user-specific. The local PDF tools keep things privacy-first but still powerful enough for deep analysis, and the LLM module ties it all together by turning that data into useful insights. Altogether, these improvements connect the technical, privacy, and intelligence sides of the system so it runs more efficiently and feels more seamless to use.


<p align="center">
  <img src="./charts/w8burnup.png" alt="Week 5 Burnup Chart width="400"/>
</p>


## Week 7 (October 13 - 19)

This week was our first real dive into backend development. After spending the past few weeks planning and documenting, we finally started building the core of the system: setting up the main functions, initializing the database, adding user consent handling, adding configuration profiles, and creating the first version of the file parsing pipeline. The main goal was to lay a solid foundation so future milestones can build on a working backend

**Joaquin:** Focused on building the archive ingestion pipeline in `backend/src/scanner/parser.py`. Implemented path validation, zip handling, and traversal protection, while structuring results through `FileMetadata`, `ParseIssue`, and `ParseResult` dataclasses. Added clear error types (`UnsupportedArchiveError`, `CorruptArchiveError`) and a CLI tool in `scripts/parse_archive.py` for testing. Updated the `README.md` with setup and usage instructions for the new parser.

**Jacob:** 
Implemented the Consent Management Module responsible for handling user permissions when interacting with external services such as LLMs. Developed core functions to request, record, verify, and withdraw user consent, integrating a detailed privacy notice to inform users about data transmission and storage risks prior to granting permission. Added a comprehensive unit test suite with 5 test cases covering positive and negative consent flows, default states, and withdrawal handling. Resolved rebase conflicts with main to ensure seamless backend integration and submitted a structured pull request documenting all changes.

**Vlad:** 
Setup of the project’s Supabase backend infrastructure, including database initialization, secure row-level storage policies, and integration testing. Created SQL scripts to define and automate key database components such as the profiles and uploads tables, triggers for user creation in auth.users, and row-level security (RLS) policies ensuring users can only access their own storage objects. Implemented an end-to-end upload test (test_upload.mjs) to verify database and Supabase Storage integration. 

**Aaron:** Implemented the configuration scanning profile logic by adding the 'ConfigManager' class which has various methods allowing the user to add, remove, switch between, and delete scanning profiles based on their own preferences in regard to file extensions. Currently stores the users config scanning profile in a json file, but will change to storing in database this week via Supabase. Also added a test suite with 18 test cases to cover all scenarios the user will encounter when utilizing any method pertaining to the configuration profile to ensure robust functionality.  

**Om:** Designed and implemented the Consent Validation Module with comprehensive `ConsentValidator` class, custom exception handling, and `ConsentRecord` dataclass. Developed core validation methods for upload consent, external services, and permission checks. Created extensive unit test suite with 20+ test cases, fixtures, and integration scenarios to ensure robust privacy-compliant functionality.

**Samarth:** Focused on building the LLM Integration setup enabling external AI service capabilities with secure API key verification and robust error handling. Developed the `LLMClient` class for OpenAI API integration, with complete configuration management and consent-based access control. Implemented RESTful API routes for key verification, model information, and service status. Built a comprehensive suite of 30+ unit and integration tests covering client initialization, authentication workflows, and endpoint behavior to ensure secure and reliable LLM operations.

<p align="center">
  <img src="./charts/w7burnup.png" alt="Week 5 Burnup Chart width="400"/>
</p>

## Week 6 (October 6 - 12)

This week our focus was on getting our project setup in place and updating some of our main documents. We started by creating a GitHub Project to organize all our tasks and make progress tracking easier with its built-in burnup chart. 

All previous tasks and the new Milestone 1 requirements were added as issues, each labeled by category and assigned story points so the chart reflects effort more accurately. After that, we worked on updating our Level 1 DFD. Some of the key changes included adding a consent gate, splitting the analysis process into local and external parts, keeping the user more involved through the UI loop, and showing more detail on how data moves into the database. We also cleaned up the process descriptions and arrows so the flow is easier to follow. We also updated our System Architecture diagram to reflect the changes brought by the new requirements, specifically the disctintion between the local and external analysis options. The Work Breakdown Structure was also expanded to cover all the specific tasks and deliverables from Milestone 1, before, it was more general and based on our early understanding of the requirements. Morevoer, the repo was setup with all of our initialy directories so we can start working on our backend. FInally, A Dockerfile was also added to standardize the environment setupand the README was updated to match the current directory structure and now includes direct links to our main documentation: Work Breakdown Structure, Data flow diagrams, and System Architecture.

<p align="center">
  <img src="./charts/w6burnup.png" alt="Week 6 Burnup Chart width="400"/>
</p>

## Week 5 (September 29 - October 5)

This week our focus was on the Data Flow Diagrams (Level 0 and 1).

We started off the week with listing down some simple processes from the start to the end in our google document. This process then led to us discovering some other interconnected processes which allowed us to narrow down onto the 7 main processes that would control the entire flow of data in our diagram. From here we had to just draw the shapes for each one of them and add appropriate description. The next steps were collective efforts into deciding the process flow directions for the different processes and their inputs and outputs. The end step was to add into picture the data storage aspect and connect it to the rest of the diagram. The shapes were then adjusted to match the notation from lecture so the diagram looked clear and consistent, and copies were printed to share with other groups. When comparing diagrams, it became clear that some groups had missing or inconsistent data stores, which made their flows harder to follow and less organized. We also checked over our own diagram to make sure the data stores were being reused correctly across processes. Finally, the repo was reorganized by moving the logs directory out of the docs folder and into its correct place, making the structure consistent with class practices.

<p align="center">
  <img src="./charts/w5burnup.png" alt="Week 5 Burnup Chart width="400"/>
</p>


## Week 4 (September 22 - 28)

This week we focused on the system architecture and the project proposal.

For the architecture, we first made a detailed component diagram that broke down each layer and described the components inside them. While it helped us see exactly what pieces exist in the system, the problem was that the flow of information wasn’t obvious, the arrows just went from one layer to the next without showing how data would actually move. After discussing, we made a second diagram that was less detailed but much clearer in terms of flow. The first diagram works well for showing system structure, while the second works better for understanding process flow. Together they allow for a pretty good understanding of the system.

We also finished the project proposal, which included:
- Usage scenario (Samarth)  
- Proposed solution (Vlad)  
- Use cases (Joaquin & Jacob) – covering artifact discovery, analysis, privacy, reporting, search/filter, etc.  
- Requirements & testing (Om & Aaron) – both functional and non-functional, linked to test frameworks (Jest, Playwright, etc.), with difficulty levels assigned.  

## Week 3 (September 15 - 21)

We worked on developing ideas for the functional and non-functional requirements for the Project Requirements document. Additionally, we added information regarding the target user group and usage scenarios. We also spent time discussing the requirements in class and learning about other teams' requirements as well. One thing we noticed we did not do that other teams did was define a tech stack, but we think it would be better to define our tech stack once we have more defined project specifications.


