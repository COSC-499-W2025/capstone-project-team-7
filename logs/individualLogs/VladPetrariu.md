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
