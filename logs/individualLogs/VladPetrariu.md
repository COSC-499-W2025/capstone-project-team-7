# Week 8: October 20 - October 26



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
