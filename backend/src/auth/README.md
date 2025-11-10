# Consent Management System

This directory contains the integrated consent management system for the portfolio analysis application. The system consists of two complementary modules that work together to provide comprehensive consent handling.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│          (File Upload, Analysis, External Services)         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              consent_validator.py                           │
│         (Validation & Type Safety Layer)                    │
│                                                             │
│  • Validates consent data structure                         │
│  • Enforces required fields                                 │
│  • Provides type-safe ConsentRecord dataclass               │
│  • Handles custom exceptions                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  consent.py                                 │
│              (Storage Layer)                                │
│                                                             │
│  • Manages in-memory consent storage                        │
│  • Provides privacy notice to users                         │
│  • Handles consent lifecycle (save/retrieve/withdraw)       │
│  • Service-based consent tracking                           │
└─────────────────────────────────────────────────────────────┘
```

## Module Descriptions

### consent_validator.py

The **validation and business logic layer** that ensures consent data meets all requirements before storage.

**Key Features:**
- **Type-Safe ConsentRecord**: Dataclass with all required consent fields
- **Comprehensive Validation**: Validates data types, required fields, and business rules
- **Custom Exceptions**: Granular error handling (ConsentError, AuthorizationError, etc.)
- **Integration Layer**: Bridges application logic with storage layer
- **Database-Ready**: Prepared for future Supabase integration

**Core Methods:**
```python
validator = ConsentValidator(use_consent_storage=True)

# Validate and store consent
consent_record = validator.validate_upload_consent(user_id, consent_data)

# Check if user has required consents
consent_record = validator.check_required_consent(user_id)

# Validate external services consent
has_external = validator.validate_external_services_consent(user_id)

# Check specific permissions
can_process = validator.is_file_processing_allowed(user_id)
can_metadata = validator.is_metadata_processing_allowed(user_id)
```

### consent.py

The **storage and privacy notice layer** that manages consent persistence and user communication.

**Key Features:**
- **Database Persistence**: Consents stored in Supabase `consents_v1` table
- **Session Management**: Authenticated requests using user access tokens
- **In-Memory Caching**: Fast access with database fallback
- **Privacy Notice Management**: Single source of truth for privacy policy
- **Service-Based Tracking**: Track consent per service (LLM, file analysis, metadata, etc.)
- **Audit Trail**: Stores timestamps and privacy notice versions
- **Lifecycle Management**: Request → Save → Retrieve → Withdraw

**Consent Persistence:**
Consents are now automatically persisted to the database and restored across sessions:
- Login: Consents loaded from database into memory
- Logout: Memory cache cleared (database retains records)
- Session Restoration: Consents automatically reloaded

**Core Functions:**
```python
# Session token management (for authenticated database requests)
consent.set_session_token(access_token)  # Set after login
consent.clear_session_token()            # Clear on logout

# Show privacy notice to user
notice = consent.request_consent(user_id, "LLM")

# Save user's consent decision (persists to database)
consent.save_consent(user_id, service_name, consent_given=True, access_token=token)

# Check if consent exists (reads from database)
has_it = consent.has_consent(user_id, service_name)

# Retrieve full consent record (from database or cache)
record = consent.get_consent(user_id, service_name, access_token=token)

# Load all consents on login (called automatically by CLI)
consent.load_user_consents(user_id, access_token=token)

# Clear cache on logout (called automatically by CLI)
consent.clear_user_consents_cache(user_id)

# Withdraw consent (removes from database and cache)
consent.withdraw_consent(user_id, service_name, access_token=token)
```

**Database Schema:**
```sql
create table public.consents_v1(
  user_id uuid primary key references auth.users(id) on delete cascade,
  accepted boolean not null default false,
  accepted_at timestamptz,
  version text not null default 'v1',
  metadata jsonb not null default '{}'
);
```

The `metadata` field stores service-specific consents:
```json
{
  "file_analysis": {"consent_given": true, "timestamp": "2025-11-07T..."},
  "external_services": {"consent_given": false, "timestamp": "2025-11-07T..."}
}
```

**Row-Level Security:**
- Users can only read/write their own consent records
- Enforced by RLS policies using `auth.uid()`
- Requires authenticated requests (access token)

## Integration Points

### How They Work Together

1. **Application requests privacy notice:**
   ```python
   from auth.consent_validator import get_privacy_notice
   
   notice = get_privacy_notice(user_id, "external_services")
   # Returns: {"service": "...", "privacy_notice": "...", "options": [...]}
   ```

2. **User provides consent, application validates and stores:**
   ```python
   from auth.consent_validator import create_consent_validator
   from auth.session import Session  # Has access_token
   
   validator = create_consent_validator(use_consent_storage=True)
   
   consent_data = {
       "analyze_uploaded_only": True,
       "process_store_metadata": True,
       "privacy_ack": True,
       "allow_external_services": True
   }
   
   # Validates structure, then persists to database via consent.py
   consent_record = validator.validate_upload_consent(user_id, consent_data)
   ```

3. **Session management (automatic in CLI):**
   ```python
   import consent
   
   # After login - set token for authenticated requests
   consent.set_session_token(session.access_token)
   
   # Load user's consents from database
   consent.load_user_consents(user_id, session.access_token)
   
   # On logout - clear cache and token
   consent.clear_user_consents_cache(user_id)
   consent.clear_session_token()
   ```

4. **Application checks permissions before operations:**
   ```python
   # Before file upload
   if validator.is_file_processing_allowed(user_id):
       # Process file
       pass
   
   # Before calling external API
   if validator.validate_external_services_consent(user_id):
       # Call external service
       pass
   ```

5. **User withdraws consent:**
   ```python
   from auth.consent_validator import withdraw_user_consent
   
   # Withdraw specific service (removes from database)
   withdraw_user_consent(user_id, "external_services")
   
   # Withdraw all consents
   withdraw_user_consent(user_id)
   ```

## Service Types

The system tracks consent for multiple services:

| Service Name | Description | Required |
|--------------|-------------|----------|
| `file_analysis` | Analyzing uploaded files | Yes |
| `metadata_processing` | Processing and storing metadata | Yes |
| `external_services` | Using external APIs/LLMs | No |

## Consent Record Structure

```python
@dataclass
class ConsentRecord:
    id: str                          # Unique identifier
    user_id: str                     # User who granted consent
    analyze_uploaded_only: bool      # File analysis consent
    process_store_metadata: bool     # Metadata processing consent
    privacy_ack: bool                # Privacy policy acknowledgment
    allow_external_services: bool    # External services consent
    created_at: datetime             # When consent was granted
    privacy_notice_version: str      # Version of privacy notice
```

## Exception Hierarchy

```
Exception
├── ConsentError              # Required consent missing/invalid
├── ExternalServiceError      # External service consent not granted
├── AuthorizationError        # User ID invalid or not found
└── DatabaseError            # Database operation failed
```

## Usage Examples

### Complete User Workflow

```python
from auth.consent_validator import (
    create_consent_validator,
    get_privacy_notice,
    withdraw_user_consent
)

# 1. Show privacy notice
notice = get_privacy_notice(user_id, "LLM")
print(notice["privacy_notice"])

# 2. User agrees, validate and store
validator = create_consent_validator(use_consent_storage=True)
consent_data = {
    "analyze_uploaded_only": True,
    "process_store_metadata": True,
    "privacy_ack": True,
    "allow_external_services": True
}
consent_record = validator.validate_upload_consent(user_id, consent_data)

# 3. Check permissions before operations
if validator.is_file_processing_allowed(user_id):
    # Process file upload
    process_file(file)

if validator.validate_external_services_consent(user_id):
    # Call external API
    api_response = call_external_service(data)

# 4. User withdraws consent later
withdraw_user_consent(user_id)
```

### Error Handling

```python
from auth.consent_validator import (
    ConsentValidator,
    ConsentError,
    AuthorizationError
)

validator = ConsentValidator(use_consent_storage=True)

try:
    consent_record = validator.validate_upload_consent(user_id, consent_data)
except AuthorizationError:
    # Handle invalid user ID
    return {"error": "Invalid user"}
except ConsentError as e:
    # Handle missing/invalid consent
    return {"error": str(e)}
except ValueError:
    # Handle invalid data format
    return {"error": "Invalid consent data format"}
```

## Testing

The system includes comprehensive test coverage:

- **test_consent_validator.py** - 22 tests for validation layer
- **test_consent.py** - 5 tests for storage layer
- **test_consent_integration.py** - 11 tests for integration
- **test_consent_persistence.py** - 10 tests for database persistence

Run all tests:
```bash
pytest tests/test_consent*.py -v
```

Test persistence demo:
```bash
python backend/test_consent_demo.py
```

## Future Enhancements

### Enhanced Database Features

- **Consent History**: Track all consent changes over time
- **Consent Versioning**: Handle privacy notice updates
- **Bulk Operations**: Efficient multi-user consent management
- **Analytics Dashboard**: Consent grant/withdrawal metrics

### Additional Features

- **Consent Expiration**: Time-limited consents with auto-renewal prompts
- **Fine-Grained Permissions**: Sub-service level consent tracking
- **Multi-Language Support**: Localized privacy notices
- **Export Functionality**: Download user's consent history

## Privacy & Compliance

The consent system is designed with privacy in mind:

- ✅ **Clear Communication**: Privacy notice explains data handling
- ✅ **User Control**: Users can grant/withdraw consent anytime
- ✅ **Granular Permissions**: Separate consent for different services
- ✅ **Audit Trail**: Timestamps and version tracking
- ✅ **Explicit Consent**: All required fields must be explicitly granted
- ✅ **No Assumptions**: External services default to disabled
- ✅ **Data Persistence**: Consents saved securely in database
- ✅ **Cross-Session Support**: Consents persist across logins/logouts
- ✅ **Row-Level Security**: Database enforces user isolation
- ✅ **Automatic Cleanup**: Consents deleted when user account removed

## How Consent Persistence Works

### Database Connection

Consents are stored in the `consents_v1` table in Supabase:
- **Primary Key**: `user_id` (UUID from `auth.users`)
- **Foreign Key**: References `auth.users(id)` with cascade delete
- **RLS Enabled**: Users can only access their own records
- **JSONB Metadata**: Stores service-specific consent details

### Authentication Flow

```
1. User logs in
   ↓
2. CLI receives Session with access_token
   ↓
3. consent.set_session_token(access_token)
   ↓
4. consent.load_user_consents(user_id, access_token)
   ↓
5. _get_authenticated_client(access_token) creates authenticated client
   ↓
6. client.auth.set_session(token, token) sets Authorization header
   ↓
7. Database query (authenticated with token via Authorization header)
   ↓
8. Consents loaded into memory cache
   ↓
9. User activities (read from cache)
   ↓
10. Grant/Withdraw (updates database + cache with authenticated requests)
   ↓
11. User logs out
   ↓
12. consent.clear_user_consents_cache(user_id)
13. consent.clear_session_token()
```

### Why Access Tokens Matter

Row-Level Security (RLS) policies check `auth.uid()` to ensure users can only access their own data. Without the access token in the request:
- Database returns `401 Unauthorized`
- RLS policy violations occur
- Consent operations fail

The `_get_authenticated_client()` helper uses the documented supabase-py API:
```python
authenticated_client = create_client(SUPABASE_URL, SUPABASE_KEY)
authenticated_client.auth.set_session(access_token, access_token)
```

This ensures the Authorization header is properly set for PostgREST requests, allowing RLS policies to identify the authenticated user.

The system automatically manages tokens:
- **Login**: Token set and consents loaded
- **Session Resume**: Token restored from saved session
- **Logout**: Token cleared from memory

This ensures secure, isolated access to consent records while maintaining persistence across sessions.

