import base64
import binascii
import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock

from app.config import settings


SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_KEY_LENGTH = 32
PASSWORD_HASH_PREFIX = "scrypt"


class AuthenticationNotConfiguredError(RuntimeError):
    """Raised when administrator credentials are absent or malformed."""


class InvalidCredentialsError(PermissionError):
    """Raised when administrator credentials do not match."""


class LoginRateLimitError(RuntimeError):
    """Raised when a client exceeds the bounded login-attempt window."""


@dataclass(frozen=True)
class AdminSession:
    username: str
    expires_at: float


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived_key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_KEY_LENGTH,
    )
    return ":".join(
        (
            PASSWORD_HASH_PREFIX,
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            _encode(salt),
            _encode(derived_key),
        )
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        salt, expected_key = _parse_password_hash(encoded_hash)
        actual_key = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
            dklen=len(expected_key),
        )
    except (binascii.Error, ValueError, TypeError):
        return False
    return hmac.compare_digest(actual_key, expected_key)


class AuthService:
    """Owns administrator credential checks and opaque in-memory sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, AdminSession] = {}
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def login(self, username: str, password: str, client_key: str) -> tuple[str, AdminSession]:
        configured_username = settings.admin_username
        configured_hash = settings.admin_password_hash
        if (
            not configured_username
            or not configured_hash
            or not is_supported_password_hash(configured_hash)
        ):
            raise AuthenticationNotConfiguredError

        self._record_login_attempt(client_key)
        password_matches = verify_password(password, configured_hash)
        username_matches = hmac.compare_digest(
            username.encode("utf-8"),
            configured_username.encode("utf-8"),
        )
        if not (username_matches and password_matches):
            raise InvalidCredentialsError

        token = secrets.token_urlsafe(32)
        session = AdminSession(
            username=configured_username,
            expires_at=time.time() + settings.auth_session_ttl_seconds,
        )
        with self._lock:
            self._attempts.pop(client_key, None)
            self._purge_expired_sessions()
            self._sessions[_token_digest(token)] = session
        return token, session

    def get_session(self, token: str | None) -> AdminSession | None:
        if not token:
            return None
        digest = _token_digest(token)
        with self._lock:
            session = self._sessions.get(digest)
            if not session:
                return None
            if session.expires_at <= time.time():
                self._sessions.pop(digest, None)
                return None
            return session

    def logout(self, token: str | None) -> None:
        if token:
            with self._lock:
                self._sessions.pop(_token_digest(token), None)

    def _record_login_attempt(self, client_key: str) -> None:
        with self._lock:
            attempts = self._active_attempts(client_key)
            if len(attempts) >= settings.auth_login_max_attempts:
                raise LoginRateLimitError
            attempts.append(time.monotonic())

    def _active_attempts(self, client_key: str) -> deque[float]:
        attempts = self._attempts[client_key]
        cutoff = time.monotonic() - settings.auth_login_window_seconds
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()
        return attempts

    def _purge_expired_sessions(self) -> None:
        now = time.time()
        expired = [
            digest
            for digest, session in self._sessions.items()
            if session.expires_at <= now
        ]
        for digest in expired:
            self._sessions.pop(digest, None)


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def is_supported_password_hash(encoded_hash: str) -> bool:
    try:
        _parse_password_hash(encoded_hash)
    except (binascii.Error, ValueError, TypeError):
        return False
    return True


def _parse_password_hash(encoded_hash: str) -> tuple[bytes, bytes]:
    prefix, n, r, p, encoded_salt, encoded_key = encoded_hash.split(":", 5)
    if (
        prefix != PASSWORD_HASH_PREFIX
        or int(n) != SCRYPT_N
        or int(r) != SCRYPT_R
        or int(p) != SCRYPT_P
    ):
        raise ValueError("unsupported password hash parameters")
    salt = _decode(encoded_salt)
    key = _decode(encoded_key)
    if len(salt) != 16 or len(key) != SCRYPT_KEY_LENGTH:
        raise ValueError("invalid password hash length")
    return salt, key
