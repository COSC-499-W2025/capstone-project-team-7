#!/usr/bin/env python3
# 2025-10-25: New CLI to sign up / log in / record + check consent_v1 via Supabase
import os, sys, json, argparse, datetime, requests

SB_URL = os.getenv("SUPABASE_URL")
SB_ANON = os.getenv("SUPABASE_ANON_KEY")
if not SB_URL or not SB_ANON:
    sys.exit("Set SUPABASE_URL and SUPABASE_ANON_KEY env vars first.")

def _post(path, data, token=None, extra_headers=None):
    h = {"apikey": SB_ANON, "Content-Type": "application/json"}
    if token: h["Authorization"] = f"Bearer {token}"
    if extra_headers: h.update(extra_headers)
    r = requests.post(f"{SB_URL}{path}", headers=h, data=json.dumps(data), timeout=20)
    r.raise_for_status()
    return r.json() if r.text else {}

def _get(path, token):
    h = {"apikey": SB_ANON, "Authorization": f"Bearer {token}"}
    r = requests.get(f"{SB_URL}{path}", headers=h, timeout=20)
    r.raise_for_status()
    return r.json()

def signup(email, password):
    return _post("/auth/v1/signup", {"email": email, "password": password})

def login(email, password):
    return _post("/auth/v1/token?grant_type=password", {"email": email, "password": password})

def consent_upsert(token, user_id):
    payload = {
        "user_id": user_id,
        "accepted": True,
        "accepted_at": datetime.datetime.utcnow().isoformat() + "Z",
        "version": "v1",
    }
    return _post("/rest/v1/consents_v1", payload, token, {"Prefer": "resolution=merge-duplicates"})

def consent_check(token, user_id):
    return _get(f"/rest/v1/consents_v1?user_id=eq.{user_id}&select=*", token)

def main():
    p = argparse.ArgumentParser(description="Supabase terminal auth + consent_v1")
    sub = p.add_subparsers(dest="cmd", required=True)
    for cmd in ("signup", "login", "consent", "check"):
        sp = sub.add_parser(cmd); sp.add_argument("email"); sp.add_argument("password")
    a = p.parse_args()

    if a.cmd == "signup":
        print(json.dumps(signup(a.email, a.password), indent=2)); return
    auth = login(a.email, a.password)
    token, uid = auth["access_token"], auth["user"]["id"]

    if a.cmd == "login":
        print(json.dumps({"user_id": uid, "token_tail": token[-12:]}, indent=2)); return
    if a.cmd == "consent":
        consent_upsert(token, uid)
        print(json.dumps(consent_check(token, uid), indent=2)); return
    if a.cmd == "check":
        print(json.dumps(consent_check(token, uid), indent=2)); return

if __name__ == "__main__":
    main()