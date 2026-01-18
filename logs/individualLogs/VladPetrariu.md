# Week 16: December 12 - December 18


<img width="1082" height="642" alt="Screenshot 2026-01-18 at 2 42 46 PM" src="https://github.com/user-attachments/assets/399898a6-4c0b-469b-888a-33a711bd185d" />

# Week 15: December 4 - December 11
This week I implemented PR ([212](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/212)) the one‑shot scan API in the main backend, delivering authenticated POST /api/scans and GET /api/scans/{scan_id} endpoints with background execution, progress polling, and result payloads. The implementation integrates auth via get_auth_context, enforces per‑user scan isolation, and validates input early to protect the system.

  Key achievements:

  - Added user_id to ScanStatus and enforced ownership checks on both create/retrieve so users can only access their own
    scans.
  - Implemented strict path validation to block sensitive system directories, reject invalid/unsafe paths, and return
    clear code/message errors (403/404/400) before any background work starts.
  - Hardened request handling with idempotency key support, profile_id authorization (must match the authenticated user),
    and a default profile_id derived from auth for downstream persistence.
  - Limited response payload size by capping returned file metadata to a constant (MAX_FILES_IN_RESPONSE) to keep
    responses predictable.
  - Switched scan status updates to immutable model_copy updates for safer concurrency in the in‑memory scan store.
  - Expanded tests to cover auth requirements, idempotency behavior, scan completion/progress, path validation (blocked +
    nonexistent paths), and profile_id enforcement.

  This PR stabilizes the scan workflow end‑to‑end in backend/src/api/spec_routes.py and adds robust coverage in tests/
  test_scan_api.py, making the scan API secure, testable, and ready for frontend polling integration.

In addition to these changes, i reviewed PR's ([214](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/214), ([213](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/213)), and ([209](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/209)).

<img width="1089" height="640" alt="Screenshot 2026-01-11 at 4 57 25 PM" src="https://github.com/user-attachments/assets/b0638a30-07b7-444b-b421-8a1b2281dd87" />

# Week 14: December 1 - December 7
This week I completed a targeted UI bug fix and contributed to our demo recording. I opened **PR [#186](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/186)**, which resolved a visual issue in the settings and user-preferences menu where text labels and toggle switches were partially hidden, preventing proper user interaction. I also reviewed **PR [#190](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/190)** from Aaron, providing feedback on his UI refresh that improves overall usability and consistency across the interface.

Beyond development work, I recorded several segments of our demo video, specifically the parts shown in the attached screenshot, highlighting how our system identifies programming languages, extracts contribution metrics, and summarizes project information.

<img width="1081" height="636" alt="Screenshot 2025-12-07 at 7 32 43 PM" src="https://github.com/user-attachments/assets/be50d76f-4573-4a8a-961c-a0db6215a9d3" />

# Week 13: November 24 - November 30
This week I implemented a sign up feature into our TUI **[*155](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/169). Previously, when testing we would have to manually create a user within Supabase then use that information to log into the account within the TUI. After adding a sign up feature within our TUI that sends the user infromtation to be stored in Supabase, testing and account creation can be fully done within the TUI while running the program. The sign up feature also has account creation restriction such as requiring the user to enter a real email into the username section as oppossed to a random name and requiring the password to be a certain number of digits to ensure that the account is secure. Along with this implementation I also added tests to verify that the account creation works accross different cases and is properly hooked up to Supabase. 

On top of implementing the sign up feature, I helped set up a meeting with my group to discuss about the upcoming presentation and to decide what each group member will be talking about.

<img width="1081" height="640" alt="Screenshot 2025-11-30 at 4 40 18 PM" src="https://github.com/user-attachments/assets/586e443e-29bc-4adf-aa19-ff2829d602f8" />

# Week 12: November 17 - November 23
This week I focused on containerizing the backend to make the system fully reproducible **[*133](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/154). I created the Dockerfile and docker-compose service, resolved macOS specific Docker issues, and ensured the Textual TUI runs cleanly inside a container. I also optimized the Docker image size by using the python:3.12-slim base image and disabling pip caching, which reduced unnecessary layer bloat. After testing the full flow (docker compose run --rm cli), I updated the documentation so the team can run the CLI with a single command.

<img width="1086" height="637" alt="Screenshot 2025-11-23 at 9 28 54 PM" src="https://github.com/user-attachments/assets/3820a0b4-a594-40dc-b079-48bf4f94cd78" />

# Week 10: November 3 - November 9

This week I focused on improving our Git analysis module by adding a classification system that identifies whether a repository represents an individual, collaborative, or unknown project. The logic determines project type based on the number of contributors found in the Git commit history and integrates seamlessly into the existing analyze_git_repo() function.

I updated the JSON output generated by the parser so each scan now includes a project_type field, providing clearer insights into team versus solo work across repositories. After implementation, I verified the feature through both unit tests in test_git_repo.py and manual CLI runs using real repositories to ensure correct detection and output formatting.

This update adds meaningful context to our overall portfolio analysis pipeline, helping differentiate personal projects from group efforts during scans. 

<img width="1088" height="644" alt="Screenshot 2025-11-09 at 9 42 46 PM" src="https://github.com/user-attachments/assets/45532628-1d7e-4268-a17f-22e590458308" />

# Week 9: October 27 - November 2

This week, I developed and integrated the Git parsing module into our project analysis system. The module enables the CLI to extract and process repository level data, including commit history, contributor activity, and file change metadata, directly from local or remote Git repositories.

To ensure seamless integration, I implemented structured parsing logic that transforms raw Git data into standardized JSON outputs compatible with our Supabase ingestion pipeline. The parser captures detailed commit attributes—such as author, timestamp, message length, and modification counts—allowing downstream modules to perform trend and ownership analysis in future releases.

I focused on maintaining performance and reliability by testing the parser against repositories with varied branching structures, large histories, and detached HEAD states. I also added robust error handling to manage invalid paths, missing .git directories, and permission issues gracefully.

In parallel, I contributed to the CLI workflow integration, introducing a new command flag that lets users trigger Git analysis alongside other project scans. I worked closely with teammates to align the data schema between the Git module, code analyzer, and document/media parsers, ensuring cross-module compatibility within our backend and analytics layers.

Next week, I plan to extend the parser to support pull request metrics, branch-level comparisons, and commit frequency analytics to enhance repository insights and team contribution tracking.

<img width="1099" height="643" alt="Screenshot 2025-11-02 at 11 30 39 PM" src="https://github.com/user-attachments/assets/341a9b5f-03d6-481e-adab-6a3e49b05167" />

# Week 8: October 20 - October 26

This week I focused on integrating Supabase authentication and consent management directly into our command line interface as part of issue #86. I extended the existing auth_cli.py to support secure sign up, log in, and access token generation through terminal commands, allowing developers to authenticate and interact with the Supabase backend entirely through the CLI.

To complement this, I created a new SQL migration script, 04_consent_policies.sql, defining the necessary row-level security (RLS) policies and permission logic for storing and retrieving user consent records in Supabase. These policies ensure that only authenticated users can access or modify their own consent data while maintaining strict data isolation between accounts.

I also migrated the project’s Supabase database from the previous organization to a new dedicated workspace to improve environment management, security, and team access. This migration was completed through a new pull request that successfully closed issue #91, ensuring the database configuration and authentication settings were fully functional in the new environment.

I integrated the authentication flow with the Consent Validation Module, enabling verified users to record and query consent data directly from the terminal. This involved implementing structured JSON outputs, token validation methods, and secure environment-based configuration for API credentials. I also refined how consent records are linked to authenticated user profiles in the database to ensure consistent cross-module data handling.

For testing, I ran multiple end-to-end authentication and consent workflows—verifying successful sign up, log in, token refresh, and Supabase record persistence across sessions. I collaborated with teammates to align schema fields between local and remote consent management systems and confirm the database behavior matched the intended API flow.

Finally, I reviewed and approved PR #94, which introduced the local PDF parsing and summarization modules. I validated the documentation and code quality to ensure alignment with our privacy-first backend architecture.

<img width="1078" height="632" alt="Screenshot 2025-10-26 at 6 43 19 PM" src="https://github.com/user-attachments/assets/1be119eb-6457-4f09-88e3-8716f2600e58" />

# Week 7: October 13 - October 19

This week I focused on setting up the full Supabase backend for our project. I created and tested the core database schema (01_initialize_database_schema.sql) defining user profiles, uploads, and triggers for automatic profile creation on new user sign-up. I also implemented row-level security (RLS) policies (02_storage_policies.sql) to ensure each user can only access their own uploaded files in Supabase Storage. To validate the setup, I wrote an end-to-end upload test (test_upload.mjs) that connects to Supabase using environment variables, uploads a sample file, and verifies that metadata is inserted correctly.

Additionally, I managed the Git workflow for integrating these changes — opening and revising pull requests, handling a mistaken merge, and restoring the correct branch through reverts and reflog recovery. This experience helped me strengthen my understanding of Git branch management and backend database security configuration.

<img width="1092" height="640" alt="Screenshot 2025-10-19 at 9 43 33 PM" src="https://github.com/user-attachments/assets/779fca52-5862-4e15-bcdb-4c10cb6ab9c3" />

# Week 6: October 6 - October 12

After reviewing the milestone 1 requirements, I was focused on developing the proof of concept for the user consent and upload gate component of our system. I designed and docuented a process that would make sure that users procide explicit consent before any data is uploaded or analyzed. The POC I worked on this week includes a blueprint for the consent interface, validation logic, and integration details using supabase for authentication and database storage. I make a full technical design, database schema, row-level security policies and storage layout for ulpoaded files. I defined validation rules and relevant output responses. Next week I plan to start implementing the POC with Supabase and demonstrate a working consent flow.

<img width="1076" height="627" alt="Screenshot 2025-10-12 at 12 45 00 PM" src="https://github.com/user-attachments/assets/260fa110-4171-4b58-95d7-f53c7e897b89" />

# Week 5: September 29 - October 5

This week I worked with my team to create our Data Flow Diagrams for Level 0 and Level 1. First we figured out the main processes in our system and organizing them into a simple list. After we built the diagrams together. We made a few changes to make sure the data flow between each process made sense. Finally, we adjusted the layout to match the examples shown in class.

# Week 4: September 21 - 28

This week I worked on the proposed solution for the project proposal.

# Week 3: September 15 - 21

This week I worked on seeting up the project foundation which included creating functional and non functional requirements. 

<img width="1078" height="632" alt="image" src="https://github.com/user-attachments/assets/88c48709-0fc5-419c-afec-3e03aaaedf08" />
