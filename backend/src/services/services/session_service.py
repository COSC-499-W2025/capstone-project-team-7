from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Callable, Optional, Tuple

from auth.consent_validator import ConsentError, ConsentRecord, ConsentValidator, ExternalServiceError
from auth.session import Session


NotifyFn = Callable[[str, str], None]


class SessionService:
    """Handle session persistence and consent refresh logic."""

    def __init__(self, reporter: Optional[NotifyFn] = None) -> None:
        self._report = reporter

    def load_session(self, path: Path) -> Optional[Session]:
        if not path:
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            user_id = data.get("user_id")
            email = data.get("email")
            token = data.get("access_token", "")
            refresh_token = data.get("refresh_token")
            if user_id and email:
                return Session(
                    user_id=user_id,
                    email=email,
                    access_token=token,
                    refresh_token=refresh_token,
                )
        except FileNotFoundError:
            return None
        except PermissionError as exc:
            self._notify(f"Permission denied while reading saved session data: {exc}", "warning")
        except OSError as exc:
            self._notify(f"Unable to read saved session data ({path}): {exc}", "warning")
        except json.JSONDecodeError as exc:
            self._notify(
                f"Saved session data is corrupted ({exc}). Sign in again to refresh it.",
                "warning",
            )
        return None

    def persist_session(self, path: Path, session: Session) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "user_id": session.user_id,
                "email": session.email,
                "access_token": getattr(session, "access_token", ""),
                "refresh_token": getattr(session, "refresh_token", None),
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
        except (PermissionError, OSError) as exc:
            tone = "error" if isinstance(exc, PermissionError) else "error"
            self._notify(f"Unable to save session data to {path}: {exc}", tone)

    def clear_session(self, path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except PermissionError as exc:
            self._notify(
                f"Permission denied while removing stored session data: {exc}",
                "warning",
            )
        except OSError as exc:
            self._notify(
                f"Unable to remove stored session data ({path}): {exc}",
                "warning",
            )

    def refresh_consent(
        self,
        validator: ConsentValidator,
        user_id: str,
    ) -> Tuple[Optional[ConsentRecord], Optional[str]]:
        try:
            record = validator.check_required_consent(user_id)
            return record, None
        except ConsentError:
            return None, "Required consent has not been granted yet."
        except ExternalServiceError:
            return None, "External services consent is pending."
        except Exception as exc:  # pragma: no cover - defensive fallback
            return None, f"Unable to verify consent: {exc}"

    def needs_refresh(self, session: Session, leeway_seconds: int = 60) -> bool:
        return self._token_expired(session.access_token, leeway_seconds)

    @staticmethod
    def _token_expired(token: str, leeway_seconds: int) -> bool:
        if not token:
            return True
        try:
            payload_segment = token.split(".")[1]
            padding = "=" * (-len(payload_segment) % 4)
            decoded = base64.urlsafe_b64decode(payload_segment + padding)
            payload = json.loads(decoded.decode("utf-8"))
            exp = payload.get("exp")
            if exp is None:
                return False
            return int(exp) <= int(time.time()) + leeway_seconds
        except Exception:
            return False

    def _notify(self, message: str, tone: str) -> None:
        if self._report:
            self._report(message, tone)
