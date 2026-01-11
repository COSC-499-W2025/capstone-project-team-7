# Aaron Banerjee (@aaronbanerjee123)
## Week 15: January 4 - January 11
This week, I focused on implementing and testing a comprehensive REST API for project scan management, integrating JWT authentication with Supabase, and ensuring secure, user-isolated data access through proper authentication and authorization mechanisms.

**Key Accomplishments:**

1. **Complete Project Routes API Implementation**: Designed and implemented a full CRUD API with four endpoints for managing project scans:
   - POST `/api/projects` - Creates new project scans with complete analysis data (code, git, skills, contributions, media, documents)
   - GET `/api/projects` - Retrieves all projects for authenticated user with metadata (contribution scores, languages, analysis flags)
   - GET `/api/projects/{id}` - Fetches detailed project data including full scan results
   - DELETE `/api/projects/{id}` - Removes projects with proper ownership verification
   
   Implemented comprehensive request/response models using Pydantic for type safety and validation, including `ProjectScanData`, `ProjectMetadata`, `ProjectDetail`, and error response schemas.

2. **JWT Authentication Infrastructure**: Implemented the authentication layer with JWT token verification for Supabase integration. Created the `verify_auth_token()` dependency that extracts Bearer tokens from Authorization headers, decodes JWT payloads, and extracts user IDs from the `sub` claim for request authorization. The current implementation successfully validates token structure and expiration, though signature verification with Supabase's HS256-signed secrets requires additional debugging (currently operating with `verify_signature: False` for testing purposes).

3. **Supabase Integration & RLS Configuration**: Integrated with Supabase for persistent storage with Row Level Security (RLS) policies enforcing user data isolation. Configured both anon and service role keys appropriately - using service role keys for backend operations to bypass RLS when needed, while maintaining security through JWT verification at the API layer. Ensured all database operations properly scope to the authenticated user's ID extracted from the JWT token.

4. **Comprehensive API Testing in Postman**: Conducted thorough end-to-end testing of all project endpoints using Postman. Created test collections with proper Authorization headers containing valid JWT tokens. Validated that:
   - JWT token extraction and payload decoding works correctly
   - User ID extraction from the `sub` claim properly identifies authenticated users
   - RLS policies correctly isolate user data (users can only access their own projects)
   - Request validation catches invalid inputs (empty project names, missing fields)
   - Response models return correct data structures with proper HTTP status codes (201 Created, 200 OK, 204 No Content, 401 Unauthorized, 404 Not Found)
   - All CRUD operations function correctly for the authenticated user

5. **Error Handling & Logging**: Implemented comprehensive error handling with specific HTTP exceptions for different failure scenarios (missing auth, invalid tokens, expired tokens, signature failures, not found, server errors). Added detailed logging throughout the authentication and service layers to aid in debugging and monitoring production issues. The logging infrastructure will be particularly useful for debugging the signature verification issues in the next iteration.

**Challenges & Learning:**

The primary challenge this week was debugging JWT signature verification with Supabase tokens. While I successfully implemented the basic authentication flow (token extraction, payload decoding, user ID extraction), enabling full signature verification with Supabase's JWT secrets proved more complex than anticipated. 

I discovered that Supabase's JWT secrets with the `sb_secret_` prefix are base64url-encoded, requiring special decoding logic. Despite implementing base64 decoding with proper padding calculations, the signature verification still fails with "Invalid token signature" errors. I attempted multiple approaches:
- Direct secret usage as a string
- Converting the secret to bytes using `.encode('utf-8')`
- Base64 decoding with standard padding
- Base64url decoding with automatic padding

The issue appears to be related to how Supabase encodes their JWT secrets versus how PyJWT expects the HMAC secret for HS256 verification. This debugging process taught me about the nuances of JWT signature algorithms, the difference between `base64.b64decode()` and `base64.urlsafe_b64decode()`, and the importance of understanding vendor-specific authentication implementations.

For now, the API operates with `verify_signature: False`, which still validates token structure, expiration, and user claims - providing functional authentication for development and testing. However, this is not suitable for production deployment.

Another learning experience was understanding FastAPI's dependency injection system. The `Depends()` mechanism provides an elegant way to inject authentication logic into route handlers, automatically handling token validation before endpoint code executes. This pattern keeps the authentication logic DRY and makes it easy to secure multiple endpoints consistently.

**Next Week Priorities:**

Next week, my primary focus will be resolving the JWT signature verification issue to enable production-ready authentication. This will involve:
- Consulting Supabase documentation on JWT secret formats and verification
- Testing with Supabase's official Python client to see how they handle signature verification
- Potentially reaching out to Supabase support or community forums for guidance on the `sb_secret_` format
- Exploring alternative approaches like using PyJWT's key loading utilities
- Ensuring the verification works consistently with both fresh and long-lived tokens

Once signature verification is working, I'll also add integration tests for the authentication layer and document the JWT configuration process for other team members and future deployments.

**Impact:**

The project routes API provides a complete backend foundation for the application's core feature: saving and retrieving project scan results. This enables users to:
- Persist their code analysis results permanently in the cloud
- Access their scan history across different sessions and devices
- Build a portfolio of analyzed projects over time
- Track project metrics and contribution scores longitudinally

The authentication infrastructure, once signature verification is fully enabled, will ensure secure, user-isolated data access - critical for a multi-user SaaS application. Each user can only view and manage their own projects, preventing unauthorized data access and maintaining privacy compliance.

This work unblocks several downstream features including the frontend project dashboard, project comparison views, and portfolio generation, as they all depend on the ability to reliably save and retrieve project data through this authenticated API.

Issues resolved include:[#197](https://github.com/COSC-499-W2025/capstone-project-team-7/issues/197)

PR[#213 - Project Routes](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/XXX)](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/213)


<img width="1239" height="200" alt="image" src="https://github.com/user-attachments/assets/ceb88bd3-53dd-4ad7-b062-02a4a9e043b8" />
<img width="1451" height="723" alt="image" src="https://github.com/user-attachments/assets/901f5895-dd8e-45e0-a549-67a816fa440f" />


## Week 14: December 1 - December 7
This week, I focused on implementing a comprehensive summary feature for the View Saved Projects screen and fixing critical navigation bugs to improve the user experience.

**Key Accomplishments:**

1. **Summary Tab Implementation**: Created a new Summary tab in the ProjectViewerScreen that aggregates data from all available analyses (code, git, skills, contributions, media, documents, duplicates, and AI) into a single, unified view.

2. **Top Ranked Projects Panel**: Implemented a top-ranked projects summary in the View Saved Projects screen displaying the 3 highest-ranked projects by contribution score, along with key metrics (impact percentage, commits, files, lines, and available analyses).

3. **Project Deletion Bug Fix**: Fixed a critical bug where deleted projects would still appear after pressing Esc. Enhanced the `refresh_after_delete()` method and modified the deletion handler to close and reopen the ProjectsScreen with fresh data, ensuring complete UI refresh.

4. **Enhanced UI Navigation**: Improved ProjectsScreen with better selection handling, arrow key navigation for dynamic detail updates, and more reliable ListView item management.
5. **Presentation Video Editing**: I edited the group's demo vide,o which involved getting everybody's clips and connecting them with subtitles

**Challenges & Learning:**
The main challenge was ensuring proper UI synchronization after deletion. Initially attempted component updates in place, but discovered closing and reopening the screen with fresh data was more reliable. This taught me the importance of understanding Textual's rendering lifecycle and screen stack management.

**Impact:**
The Summary tab provides users with a cleaner way to review project insights at a glance. The top-ranked projects panel helps users identify their most important work. The deletion bug fix ensures proper data synchronization and prevents confusion when managing saved projects.

Issues resolved include:[#53](https://github.com/COSC-499-W2025/capstone-project-team-7/issues/XXX)

PR [#190 - Summary Tab & Deletion Fix](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/XXX)]
<img width="1335" height="786" alt="image" src="https://github.com/user-attachments/assets/ebfe427d-de12-4a32-995b-f3f4fec7cc76" />
<img width="1318" height="887" alt="image" src="https://github.com/user-attachments/assets/93d6c592-dcc0-4fe8-805f-c0acec24a6e3" />


# Week 13: November 24 - November 30

This week, I implemented the AI Auto-Suggestion feature to automatically suggest and apply code improvements based on skill detection and code analysis. This helps users enhance their codebase with AI-powered recommendations while maintaining code integrity and user control. This was implemented using secure file path handling and robust LLM integration for generating contextually relevant suggestions.

**Key Accomplishments:**

1. **AI Auto-Suggestion Module**: Added on to `AIService` class that orchestrates the suggestion workflow, validates file paths securely, generates AI-powered suggestions, and applies improvements to user code. Integrated with CLI and Textual UI for seamless user interaction.

2. **Secure Path Validation**: Implemented critical security layer with `_validate_and_resolve_path()` to prevent path traversal attacks, handle archive prefixes, and ensure all file operations stay within designated directories.

3. **File Selection & Configuration**: Created `AutoSuggestionConfigScreen` to allow users to select which files to process, configure output directories, and customize AI suggestion parameters. Added intelligent file filtering to exclude non-code files.

4. **Testing & Quality Assurance**: Created 28 new tests covering file selection, AI execution, progress tracking, output handling, error recovery, and end-to-end integration. Achieved 100% pass rate.

**Challenges & Learning:**
Faced challenges with secure file path handling in cross-platform environments and archive extraction prefix stripping. Resolved by implementing multi-layer validation with path traversal detection. Learned the importance of fail-safe security measures when executing AI-driven code modifications.

**Impact:**
Users can now leverage AI to automatically identify and implement code improvements, reducing manual refactoring effort while maintaining code quality. The feature integrates seamlessly with skill detection to provide contextually relevant suggestions based on detected competencies. This significantly enhances the portfolio analysis system's value proposition by offering actionable insights.

Issues resolved include: [#151- Ai auto suggestion](https://github.com/COSC-499-W2025/capstone-project-team-7/issues/158)

PR [#170 - Ai suggestion feature](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/170)

<img width="1338" height="762" alt="image" src="https://github.com/user-attachments/assets/cd414d24-bb4a-42b6-ab16-0bc1941761d4" />

<img width="1163" height="64" alt="image" src="https://github.com/user-attachments/assets/fe91c1f0-9c35-4f72-be01-639960b60a9b" />

**Next Week Priorities**:
- Improve other types of local analysis to better provide insights
- Improve threading operations in  ```textual_app.py``` to improve speed and how resources are shared during tasks
- Fix small UI bugs that occur when viewing old proejcts
## Week 12: November 17 - November 23

This week I implemented the backend database connection to our project through implementing the "View saved projects" feature. This feature allows users to view their saved projects after exporting a JSON report. It allows users to view them in chronological order based on when they scanned the project, and lets them view all their key metrics and analysis in a tab format. 

**Key Accomplishments:**

Here's a more concise but descriptive version:

**Projects Service**: Built a robust ProjectService class that encapsulates all CRUD operations for project management, acting as a clean interface between the application and database. The modular architecture ensures easy integration with textual_app.py while maintaining separation of concerns and code reusability throughout the application.

**Project Saving**: Implemented comprehensive project persistence by capturing and serializing all analysis data from the JSON report format directly into the database. This ensures users can reliably retrieve complete analysis sessions with full data integrity preserved across application restarts.

**ProjectViewerScreen**: Designed and built the ProjectViewerScreen class in screens.py to provide an intuitive interface for managing saved projects. Users can seamlessly view, edit, delete, and interact with their stored project analyses through full CRUD functionality.

**Comprehensive Testing**: Developed 5 thorough unit tests covering all critical ProjectService operations including edge cases and error handling. These tests ensure reliability and maintainability of the project management functionality across future updates.

**Challenges & Learning:**
I struggled with implementing the project saving to the application due to needing to understand the entire flow and how our services interact with the the main ```textual_app.py``` file and also how ```screens.py``` works with the main file. Resolved this by taking time to understand how the flow of the application with the TUI and how to add screens. Learned the flow of how to add new UI screens now and can use these skills moving forward. 

**Impact:**
Users are now able to save their projects along with all their saved analysis in the JSON report and view them in the "View Saved Projects" tab. They can now also view the saved projects in chronolgoical order and perform full CRUD functions on the saved projects like adding, deletion, and editing of saved projects.


Issues resolved include:[#60](https://github.com/COSC-499-W2025/capstone-project-team-7/issues/60), [#48](https://github.com/COSC-499-W2025/capstone-project-team-7/issues/48),
[#148](https://github.com/COSC-499-W2025/capstone-project-team-7/issues/148) and [#55](https://github.com/COSC-499-W2025/capstone-project-team-7/issues/55)

[PR #139 - Project Storage](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/139)

[PR #152 - Implement new metrics view project screen #152](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/152)

<img width="1504" height="159" alt="image" src="https://github.com/user-attachments/assets/bec484a6-ad50-466a-a50c-58e6510823bd" />

<img width="1362" height="734" alt="image" src="https://github.com/user-attachments/assets/a0c5204e-a727-47a0-b340-eb76561ab953" />


**Next Week Priorities**

- Add local analysis functionality into the AI component by adding all the types of analysis from local to the AI part
- Ensure no bugs are present from PR's and current TUI flow
- Finish minor refactoring and improve local analysis further

## Week 10: November 4 - November 9

*This week, I integrated the code quality analysis system into our interactive CLI application (app.py), making code analysis accessible through the same workflow as PDF, Git, and Media analysis. The integration follows the established pattern used by other analysis types, offering users code quality analysis after scanning a project and providing a dedicated menu option to view detailed results. I implemented state management for analysis results using self._code_analysis_result and created two core methods: _analyze_code_from_scan() which initializes the CodeAnalyzer with user preferences and runs analysis on the target directory, and _handle_code_analysis_option() which displays results by reusing the existing display_analysis_results() function from code_cli.py. The integration respects user configuration settings, pulling max file size limits from their profile and excluding standard directories like node_modules and .git. I added detection logic that checks parse_zip results for code files (checking 18 different extensions including .py, .js, .ts, .tsx, .java, .cpp, .go, .rs, .rb, .php, .cs, and more), and only offers analysis when code files are present and dependencies are available. The feature includes comprehensive error handling with graceful degradation - if tree-sitter dependencies are missing, it provides clear installation instructions and continues with other CLI features. I also ensured the analysis offer appears at the correct point in the workflow (after PDF analysis but before the "Scan completed successfully" message) so users actually see the prompt before the menu appears.*

**Technical Challenges & Solutions
Import Path Issues**

*Problem: The code analysis integration initially failed silently with CODE_ANALYSIS_AVAILABLE = False, preventing the feature from appearing at all. The root cause was in code_cli.py line 15, which used from code_parser import CodeAnalyzer instead of a relative import. This worked fine when code_cli.py was run as a standalone script, but failed when imported as a module from app.py because Python couldn't find code_parser in sys.path.
Solution: Changed the import to from .code_parser import CodeAnalyzer to use Python's relative import syntax. This was a critical lesson in understanding the difference between running a file as a script versus importing it as a module - the same code works differently in each context. I implemented debug logging (print(f"CODE_ANALYSIS_AVAILABLE = {CODE_ANALYSIS_AVAILABLE}")) to quickly identify when imports were failing, which proved essential for diagnosing the issue. This experience reinforced the importance of using relative imports consistently within a package structure.
Learning: Module imports require careful attention to relative vs absolute paths. Always test imports both as standalone scripts and as imported modules. Adding debug logging at import time helps catch these issues early.*

<img width="1461" height="798" alt="image" src="https://github.com/user-attachments/assets/b8403b50-c069-4115-8e2c-908a46d9dd29" />




## Week 9: October 27 - November 3

*This week, I worked on integrating local code analysis capabilities into our project parsing system. I created a comprehensive code parser module (code_parser.py) that leverages tree-sitter to analyze code quality across 14+ programming languages including Python, JavaScript, TypeScript, Java, C++, Go, Rust, and more. The parser calculates maintainability scores (0-100 scale) based on complexity penalties, comment ratios, and function length, and identifies refactoring candidates by analyzing cyclomatic complexity, function metrics, and code patterns. I also built an interactive CLI tool (code_cli.py) that provides a user-friendly interface for running code analysis, displaying detailed metrics including security issues, TODOs, complex functions needing refactoring, and overall project health assessments. To integrate this with our existing scanning infrastructure, I refactored the parse_zip.py main CLI to support a new --analyze flag that runs static code analysis alongside normal project parsing. I implemented proper error handling throughout, replacing print statements with Python's logging module and adding comprehensive null/error checks for analysis results serialization. This included defensive programming techniques like safe attribute access with getattr(), method existence checking with hasattr(), and wrapping potentially failing operations in try-except blocks. I also added detailed documentation comments explaining the maintainability score calculation formula, including the specific penalty factors (complexity, comment ratio, and function length) that contribute to the scoring system. These enhancements enable users to get actionable insights on code quality, identify high-priority refactoring targets, and detect potential security issues across their entire codebase.*

<img width="1415" height="752" alt="image" src="https://github.com/user-attachments/assets/46266cc0-8a4d-463b-ba2c-b885f8ae09b4" />



## Week 8: October 19 - October 26

*This week, I worked on implementing the database connection to the config manager class. This consisted of refactoring the config manager class to utilize the supabase db in all the CRUD methods. Then I had to update RLS policies for our database so that certain triggers would occur upon a new user being added such as default user configs being added. I then made a test suite for my refactored and new changes to verify that when a new user is made, they can modify their scanning configuration profiles via any CRUD method and our config manager works. The tests all passed. I also reviewed my teammate, Samarths PR for llm integration in analysis. Lastly, I began working towards a new pr in regard to local analysis of coding files in a branch called "local-analysis-coding". This pr isn't finished but so will allow a user to get key metrics and insights on coding files once finished.

<img width="1304" height="683" alt="image" src="https://github.com/user-attachments/assets/10068db4-4b1f-48e5-a20c-92e133f6abb5" />


## Week 7: October 12 - October 19

*This week, I worked on implementing the ConfigManager class which provides the user configuraiton profile logic. This class involved methods that allowed the user to create, delete, and switch between various file configs. The configs allow the user to scan for specific files based on the config they select. For example, the "all" config will scan for all the file extensions that exist, but the documents_only config only iterates through files with extensions like .txt or .md. I then implemented comprehensive testing (about 18 tests) to ensure validity and that the ConfigManager class works in all cases including edge cases. I also reviewed my teammate's pr (Om) for the consent validation module and approved it.*

<img width="1349" height="675" alt="image" src="https://github.com/user-attachments/assets/d8a14dcd-3bae-4c23-9f65-bb7a00a25f43" />




## Week 6: October 6 - October 12

*This week, I spent lots of time studying Docker documentation and understanding how to implement it in our project. Aside from that, I made a code contribution which involed including a template for our fast api backend service. The commit I made will allow our team to move forward with implementing our backend api routes in the future. It involved ensuring using the FastAPI library and uvicorn to test our routes on a default ip to ensure we get a 200 status code. Apart from that, I discussed refinements we can make to our DFD and System architecture diagrams.*

<img width="1438" height="765" alt="image" src="https://github.com/user-attachments/assets/e7ae96fb-b70a-4447-b079-b7e3bd16bcfa" />





## Week 5: September 29 - October 5

*This week, my team and I worked on our DFD level 0 and level 1 diagrams. This entailed us identifying all the key proccees our application would have, and how these processes would communicate with one another. Next, we used a program called Lucid chart to define all the key entities in our DFD's. We then connected all our processes through the key entities, such as connecting the authentication entity to manage the configuration entity, as the user should only be able to manage scanning settings if they are authenticated. On Wednesday, I discussed the DFD's with team 4, team 13, and team 18. I learned some key points from each team during these discussions such as how to better improve our data flow.*


<img width="1180" height="665" alt="Screenshot 2025-10-05 215059" src="https://github.com/user-attachments/assets/219872f7-b4e9-4d4c-8845-6217b57f561f" />



## Week 4: September 22 - 28

*This week, I focused on designing the system architecture diagram with my team. I assisted in figuring out the different layers we would be utilizing and the technologies within each layer. For example, for the service layer, we decided to use REST API. I then worked on the "Requirements, Testing, Requirement Verification" with om in which I worked on the non functional requirements, test cases, and difficulty levels* 


<img width="1340" height="766" alt="image" src="https://github.com/user-attachments/assets/bcf11b48-a62f-451b-b450-1d1ab8998066" />


## Week 3: September 15 - 21 
This week, I worked on defining the non-functional requirements and Work Breakdown Structure (WBS) for our personal artifact discovery and portfolio system. I established performance benchmarks like scanning 1GB of data within 5 seconds and supporting up to 10,000 files, along with security requirements ensuring all user data stays local and encrypted. For the WBS, I organized the project into four phases over 16 weeks: Foundation (research and requirements), System Architecture Design, Database & API Design, and User Interface & Integration. Each phase has clear deliverables and timelines to guide our development of this portfolio tool for graduating students. This planning work provides the technical foundation and project roadmap we need to move forward with implementation.

<img width="1342" height="756" alt="image" src="https://github.com/user-attachments/assets/be4ade06-f6a2-4493-92c2-dac350ff54d5" />
