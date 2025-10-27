#!/usr/bin/env python3
"""
Supabase terminal auth + consent_v1 CLI

Windows quick notes:
- PowerShell env vars:   $env:SUPABASE_URL="https://<proj>.supabase.co"
                         $env:SUPABASE_ANON_KEY="ey..."
- Virtualenv:            py -m venv .venv; .\.venv\Scripts\Activate.ps1
- Run:                    py scripts/auth_cli.py signup you@example.com

Security:
- Passwords are read via getpass.getpass() to avoid shell history / process list leaks.
- Avoid passing passwords via command-line args.
"""

import os, sys, json, argparse, datetime, re, getpass, requests

# ---------- Constants ----------
AUTH_SIGNUP_PATH = "/auth/v1/signup"
AUTH_TOKEN_PATH  = "/auth/v1/token?grant_type=password"
CONSENTS_TABLE   = "consents_v1"
REST_TABLE_PATH  = f"/rest/v1/{CONSENTS_TABLE}"
TIMEOUT_SECS     = 20

SB_URL  = os.getenv("SUPABASE_URL")
SB_ANON = os.getenv("SUPABASE_ANON_KEY")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def die(msg: str, code: int = 1):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(code)

def ok(msg: str):
    print(f"✓ {msg}")

def require_env():
    if not SB_URL or not SB_ANON:
        die("Missing SUPABASE_URL or SUPABASE_ANON_KEY. "
            "Find them in Supabase → Settings → API, then export as env vars.")

def valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email))

def _post(path, data, token=None, extra_headers=None):
    h = {"apikey": SB_ANON, "Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    if extra_headers:
        h.update(extra_headers)
    r = requests.post(f"{SB_URL}{path}", headers=h, data=json.dumps(data), timeout=TIMEOUT_SECS)
    r.raise_for_status()
    return r.json() if r.text else {}

def _get(path, token):
    h = {"apikey": SB_ANON, "Authorization": f"Bearer {token}"}
    r = requests.get(f"{SB_URL}{path}", headers=h, timeout=TIMEOUT_SECS)
    r.raise_for_status()
    return r.json()

def _delete(path, token):
    h = {"apikey": SB_ANON, "Authorization": f"Bearer {token}"}
    r = requests.delete(f"{SB_URL}{path}", headers=h, timeout=TIMEOUT_SECS)
    r.raise_for_status()
    # PostgREST DELETE returns count via preference; we keep it simple
    return True

def signup(email: str, password: str):
    return _post(AUTH_SIGNUP_PATH, {"email": email, "password": password})

def login(email: str, password: str):
    return _post(AUTH_TOKEN_PATH, {"email": email, "password": password})

def consent_upsert(token: str, user_id: str):
    payload = {
        "user_id": user_id,
        "accepted": True,
        "accepted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "version": "v1",
    }
    return _post(REST_TABLE_PATH, payload, token, {"Prefer": "resolution=merge-duplicates"})

def consent_check(token: str, user_id: str):
    return _get(f"{REST_TABLE_PATH}?user_id=eq.{user_id}&select=*", token)

def consent_revoke(token: str, user_id: str):
    # Requires DELETE policy (see SQL change)
    return _delete(f"{REST_TABLE_PATH}?user_id=eq.{user_id}", token)

def read_password(flag_pw: str | None):
    if flag_pw:
        print("⚠ Using --password from CLI is not recommended (leaks to history/process list). "
              "Press Enter to continue or Ctrl+C to cancel.")
        input()
        return flag_pw
    return getpass.getpass("Password: ")

def main():
    require_env()

    p = argparse.ArgumentParser(description="Supabase terminal auth + consent_v1")
    sub = p.add_subparsers(dest="cmd", required=True)

    # Common: email, optional --password for CI/automation; otherwise getpass()
    def add_common(sp):
        sp.add_argument("email")
        sp.add_argument("--password", help="NOT RECOMMENDED: password via CLI (use interactive prompt)")

    add_common(sub.add_parser("signup"))
    add_common(sub.add_parser("login"))
    add_common(sub.add_parser("consent"))
    add_common(sub.add_parser("check"))
    add_common(sub.add_parser("revoke"))  # delete consent (revocation)

    a = p.parse_args()

    if not valid_email(a.email):
        die(f"Invalid email address: {a.email}")

    try:
        if a.cmd == "signup":
            pw = read_password(a.password)
            resp = signup(a.email, pw)
            ok("Sign-up request sent.")
            print(json.dumps(resp, indent=2))
            return

        # For all other commands, log in first
        pw = read_password(a.password)
        auth = login(a.email, pw)
        token, uid = auth["access_token"], auth["user"]["id"]

        if a.cmd == "login":
            ok("Logged in successfully.")
            print(json.dumps({"user_id": uid, "token_tail": token[-12:]}, indent=2))
            return

        if a.cmd == "consent":
            consent_upsert(token, uid)
            rows = consent_check(token, uid)
            ok("Consent recorded.")
            print(json.dumps(rows, indent=2))
            return

        if a.cmd == "check":
            rows = consent_check(token, uid)
            ok("Fetched consent status.")
            print(json.dumps(rows, indent=2))
            return

        if a.cmd == "revoke":
            consent_revoke(token, uid)
            ok("Consent revoked (deleted).")
            return

    except requests.HTTPError as e:
        # Add context to errors
        msg = getattr(e.response, "text", str(e))
        die(f"HTTP error from Supabase: {e} :: {msg}")
    except Exception as e:
        die(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()