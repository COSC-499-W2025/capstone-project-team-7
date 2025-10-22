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
- **Privacy Notice Management**: Single source of truth for privacy policy
- **In-Memory Storage**: Dictionary-based storage (easily replaceable with database)
- **Service-Based Tracking**: Track consent per service (LLM, file analysis, metadata, etc.)
- **Audit Trail**: Stores timestamps and privacy notice versions
- **Lifecycle Management**: Request → Save → Retrieve → Withdraw

**Core Functions:**
```python
# Show privacy notice to user
notice = consent.request_consent(user_id, "LLM")

# Save user's consent decision
consent.save_consent(user_id, service_name, consent_given=True)

# Check if consent exists
has_it = consent.has_consent(user_id, service_name)

# Retrieve full consent record
record = consent.get_consent(user_id, service_name)

# Withdraw consent
consent.withdraw_consent(user_id, service_name)
```

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
   
   validator = create_consent_validator(use_consent_storage=True)
   
   consent_data = {
       "analyze_uploaded_only": True,
       "process_store_metadata": True,
       "privacy_ack": True,
       "allow_external_services": True
   }
   
   # Validates structure, then stores in consent.py
   consent_record = validator.validate_upload_consent(user_id, consent_data)
   ```

3. **Application checks permissions before operations:**
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

4. **User withdraws consent:**
   ```python
   from auth.consent_validator import withdraw_user_consent
   
   # Withdraw specific service
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

Run all tests:
```bash
pytest tests/test_consent*.py -v
```

## Future Enhancements

### Planned Database Integration

Replace in-memory storage with Supabase:

```python
# Future implementation in consent_validator.py
validator = ConsentValidator(supabase_client=supabase, use_consent_storage=False)

# Will query from Supabase instead of consent.py storage
consent_record = validator.check_required_consent(user_id)
```

### Consent Versioning

Track changes to privacy notices:
- Store consent history
- Handle consent version updates
- Notify users of policy changes

## Privacy & Compliance

The consent system is designed with privacy in mind:

- ✅ **Clear Communication**: Privacy notice explains data handling
- ✅ **User Control**: Users can grant/withdraw consent anytime
- ✅ **Granular Permissions**: Separate consent for different services
- ✅ **Audit Trail**: Timestamps and version tracking
- ✅ **Explicit Consent**: All required fields must be explicitly granted
- ✅ **No Assumptions**: External services default to disabled

