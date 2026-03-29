## 📝 Description

Harden the backend API against common abuse vectors by adding rate limiting, security response headers, and path traversal validation.

### Changes

- **Rate limiting (slowapi)** – Added per-endpoint rate limits to abuse-prone auth and upload routes: signup (5/min), login (10/min), request-reset (3/min), reset-password (5/min), upload (10/min). Exceeded limits return a JSON 429 response.
- **Security response headers** – Added `SecurityHeadersMiddleware` that injects `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, and `Permissions-Policy: camera=(), microphone=(), geolocation=()` on every response. HSTS is opt-in via `ENABLE_HSTS=true` env var.
- **Path traversal validation** – Added `validate_storage_path()` utility that rejects `../`, null bytes, absolute paths, backslash traversal, and Windows drive letters before writing uploaded files.
- **New security module** – Centralised all security concerns in `backend/src/api/security.py`.

**Closes** # (issue number)

---

## 🔧 Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [x] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation added/updated
- [x] ✅ Test added/updated
- [ ] ♻️ Refactoring
- [ ] ⚡ Performance improvement

---

## 🧪 Testing

> 17 automated tests — all passing.

- [x] **Security headers (7 tests)** – Verify each header is present with correct value; HSTS absent by default, present when `ENABLE_HSTS=true`
- [x] **Rate limiting (2 tests)** – Requests under limit succeed (200); requests over limit return 429 with JSON error body
- [x] **Path traversal validation (8 tests)** – Simple filenames and nested subdirs allowed; `../`, absolute paths, null bytes, backslash traversal, Windows drive letters, and double-encoded traversal all rejected with `ValueError`
- [x] Login/signup still work correctly after adding rate limit decorators

---

## ✓ Checklist

- [x] 🤖 GenAI was used in generating the code and I have performed a self-review of my own code
- [x] 💬 I have commented my code where needed
- [ ] 📖 I have made corresponding changes to the documentation
- [x] ⚠️ My changes generate no new warnings
- [x] ✅ I have added tests that prove my fix is effective or that my feature works and tests are passing locally
- [ ] 🔗 Any dependent changes have been merged and published in downstream modules
- [ ] 📱 Any UI changes have been checked to work on desktop, tablet, and/or mobile

---

## 📸 Screenshots

> No UI changes – backend-only security hardening.

<details>
<summary>Click to expand screenshots</summary>

N/A

</details>
