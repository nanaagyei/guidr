# Profile Completion & Input Parsing Rules

## Profile Completion Levels

The profile completion system uses a **3-level model** instead of a flat percentage:

| Level | Requirements | Unlocks |
|-------|-------------|---------|
| 0 | Account created, no profile data | Nothing |
| 1 | `intended_degree` + `primary_field_of_study` | Dashboard access |
| 2 | Level 1 + `research_areas` (>=1) + `preferred_countries` (>=1) + (`country_of_citizenship` OR `current_country`) | Recommendations, Funding |
| 3 | Level 2 + at least 1 `AcademicRecord` | Professor matching (email generation) |

### API Endpoint

```
GET /profile/completion
```

Returns:
```json
{
  "percent": 75,
  "level": 2,
  "missing_fields": ["academic_record"],
  "unlocks": {
    "dashboard": true,
    "recommendations": true,
    "funding": true,
    "professors": false
  }
}
```

### Server-Side Gating

Routes are protected with `require_level(N)` dependency:
- `POST /recommendations/run` — Level 2
- `POST /recommendations/request` — Level 2
- `GET /funding` — Level 2
- `POST /professors/{id}/generate-email` — Level 3

Returns `403` with:
```json
{
  "code": "INSUFFICIENT_PROFILE",
  "required_level": 2,
  "current_level": 1,
  "missing_fields": ["research_areas", "preferred_countries"],
  "missing_labels": ["Research Areas", "Preferred Countries"],
  "message": "Complete your targeting profile..."
}
```

## Input Parsing Rules

### Multi-value fields

Fields: `preferred_countries`, `preferred_cities`, `research_areas`, `secondary_fields`

**Backend (Pydantic validator):**
- Accepts `list[str]` (preferred) or comma-separated `str` (backward compat)
- Trims whitespace from each item
- Collapses internal multiple spaces to single space
- Truncates items to 100 characters
- Deduplicates case-insensitively (keeps first occurrence)
- Caps at 30 items

**Frontend (TagInput component):**
- Comma or Enter creates a tag
- Paste with commas auto-splits into multiple tags
- Case-insensitive dedup
- `maxTags` and `maxTagLength` props
- Spaces within tags preserved ("Machine Learning" = 1 tag)

### Shared Sanitization

`src/utils/sanitization.py`:
- `normalize_string_list(value, max_items=30, max_item_length=100)` — str→list conversion + normalization
- `sanitize_text(value, max_length=200)` — strip + truncate
- `SAFE_TEXT_PATTERN` — regex allowlist for LLM-facing text inputs

## Idempotency Keys

`POST /recommendations/run` and `POST /recommendations/request` support an optional `Idempotency-Key` header:
- Redis-backed with 1-hour TTL
- Keyed per user (`guidr:idem:{user_id}:{key}`)
- Returns cached response if same key is reused within TTL
- Prevents duplicate recommendation jobs from double-clicks or retries
