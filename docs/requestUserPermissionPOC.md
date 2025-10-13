**Requesting user permission \- POC**

1. **Objective**  
- The purpose of this feature in our artifact management system is to gain permission to access certain files before they are analyzed by the system. This will ensure that we comply with privacy and ethical standards. It will also restrict upload to valid files and will handle the permissions for accessing external services like github.

2. **Functional Requirements**  
- Display a consent screen. The consent screen should include a form (checkbox) that needs to be completed before any file gets uploaded. Check box form could include prompts such as:

  \- “Analyze only the files that I upload (The system will not scan any other files on    my device”

  \- “I consent to processing and temporary storage of extracted metadata (file names, language tags, commit stats)”

  \- “I have read the privacy notice”

  \- “Allow external services (optional)”

- Prevent any uploads unless consent is granted and mandatory boxes are checked.  
- Accept only .zip files and reject all other types with relevant error messages.  
- Persist a consent record in the database with each user.  
- On success, take the user to the upload section of the system and the file parsing pipeline.

3. **User Flow**

1\. Open upload page \-\> Open consent text, required checkboxes, optional external   services checkbox and a .zip file picker

2\. User action \-\> User checks the required boxes, chooses projects in a .zip file, and optionally toggles external services so the system can scan projects on places like github.

3\. Validation \-\> If any required checkbox is unchecked, show relevant error messages and disable the user from uploading. If a file is missing, too large, not in a .zip format or corrupted, show the specific error.

4\. Submit \-\> Backend creates a consent record and stores it with the corresponding user ID.

5\. Response \-\> Return JSON summary and route to a “Ready to analyze” page.

6\. Next step \-\> (out of scope fo this POC) but the user would be ready to start parsing. 

4. **Technical Design**

**Architecture (POC scope)**

- Client/UI: simple upload page with consent checkboxes and a .zip file picker.  
- Auth: Supabase Auth (email \+ password). We need user\_id for ownership and row level security (RLS).  
- Data: Supabase Postgres for consent \+ upload metadata.  
- Storage: Supabase storage bucket uploads for raw .zip.  
- API One server endpoint POST /api/consent-upload that verifies consent, uploads zip to storage, inserts DB rows and returns JSON.  
- Parsing service: Out of scope for this POC but will call python later.

	**Sequence:**

- User signs in and gets [user.id](http://user.id).  
- User checks required boxes and picks projects.zip.  
- Client calls POST /api/consent-upload with form data \+ supabase auth token.  
- API validates inputs and streams file to storage at uploads/{user\_id}/{upload\_id}/projects.zip.  
- API inserts consent\_records and uploads rows.  
- API responds with summary payload: upload\_id, consent flags, file infor, next: Ready For Analysis.


**Database schema (SQL)**

**Consent per upload/session:**

create table if not exists public.consent\_records (

 id uuid primary key default gen\_random\_uuid(),

 user\_id uuid not null references auth.users(id) on delete cascade,

  analyze\_uploaded\_only boolean not null,

  process\_store\_metadata boolean not null,

  privacy\_ack boolean not null,

  allow\_external\_services boolean not null default false,

  created\_at timestamptz not null default now()

);

**Upload metadata (raw file lives in storage):**

create table if not exists public.uploads (

 id uuid primary key default gen\_random\_uuid(),

  user\_id uuid not null references auth.users(id) on delete cascade,

  consent\_id uuid not null references public.consent\_records(id) on delete cascade,

  original\_filename text not null,

  storage\_path text not null, \-- e.g., uploads/{user}/{upload}/projects.zip

  size\_bytes bigint not null,

  sha256 text not null,

  status text not null check (status in ('RECEIVED','READY\_FOR\_ANALYSIS','REJECTED')),

  created\_at timestamptz not null default now()

);

**Row Level Security (RLS):**

alter table public.consent\_records enable row level security;

alter table public.uploads enable row level security;

create policy "own-consents"

on public.consent\_records for all

to authenticated

using (user\_id \= auth.uid())

with check (user\_id \= auth.uid());

create policy "own-uploads"

on public.uploads for all

to authenticated

using (user\_id \= auth.uid())

with check (user\_id \= auth.uid());

**Storage layout and permissions:**

- Bucket: uploads  
- Object path: uploads/{user\_id}/{upload\_id}/projects.zip  
- Access: private. App server uses supabase service key to wrote. Client reads via signed URL.  
- Optional guardrails: Bucket denies files \>200 MB, 


  
**API contract:**  
POST /api/consent-upload  
Auth: Supabase  
Body (multipart/form-data):

- File (required) \- .zip only  
- Consent\_analyze\_uploaded\_only (required: true)  
- Consent\_process\_store\_metadata (required: true)  
- Consent\_privacy\_ack (required: true)  
- Allow\_external\_services (optional: true|false, default: false)

**OK form:**  
{  
  "upload\_id": "a7f1b3e4-6c1a-4b8a-90f7-3f6c9cc1b527",  
  "consent": {  
    "analyze\_uploaded\_only": true,  
    "process\_store\_metadata": true,  
    "privacy\_ack": true,  
    "allow\_external\_services": false,  
    "timestamp": "2025-10-12T09:18:00Z"  
  },  
  "file": {  
    "name": "projects.zip",  
    "size\_bytes": 8421931,  
    "sha256": "…"  
  },  
  "next": "READY\_FOR\_ANALYSIS"  
}

**Error messages:**

- {"error":"CONSENT\_REQUIRED","message":"Please accept all required consent items."}  
- {"error":"UNSUPPORTED\_FILE\_TYPE","message":"Only .zip files are allowed."}  
- {"error":"FILE\_TOO\_LARGE","message":"File exceeds 200 MB limit."}  
- {"error":"CORRUPT\_OR\_UNZIP\_ERROR","message":"Zip is corrupted or unsafe."}

5. **Validation rules**  
   

| Rule | Condition  | Failure code | Message |
| :---- | :---- | :---- | :---- |
| Mandatory consent | 3 required boxes \= true | CONSENT\_REQUIRED | “Please accept all required consent items” |
| Auth | Must be logged in | UNAUTHENTICATED | “Sign in to upload” |
| File present | File exists | FILE\_MISSING | “Choose a .zip file to upload” |
| Type | Must be .zip file | UNSUPPORTED\_FILE\_TYPE | “Only .zip files are allowed" |
| Size | \<= 200 MB (Configurable) | FILE\_TOO\_LARGE | “File exceeds 200 MB lmit” |
| Zip sanity | No absolute/../ paths | CORRUPT\_OR\_UNZIP\_EROR | “Zip is corrupted or unsafe” |

6. **Output**  
   User visible:  
- Success page: filename, size, consent summary, and a disabled “Start Analysis” button (placeholder for python parser)

	Programmatic:

- JSON response as above  
- Rows in consent\_records and uploads  
- Object in uploads bucket under the owners path

	Audit trail:

- As an option we can write a small consent snapshot to storage for transparency.