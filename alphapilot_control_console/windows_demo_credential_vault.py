"""Windows Credential Manager storage for one OKX Demo credential bundle."""

from __future__ import annotations

import ctypes
import json
import os
from ctypes import wintypes
from dataclasses import dataclass, field
from typing import Protocol


DEMO_CREDENTIAL_TARGET = "AlphaPilot/OKX/Demo/v1"
DEMO_CREDENTIAL_LABEL = "AlphaPilot OKX Demo"
CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2
ERROR_NOT_FOUND = 1168
MAX_CREDENTIAL_BLOB_BYTES = 2048


@dataclass(frozen=True)
class DemoCredentialBundle:
    apiKey: str = field(repr=False)
    secretKey: str = field(repr=False)
    passphrase: str = field(repr=False)

    def __repr__(self) -> str:
        return (
            "DemoCredentialBundle(apiKey=<redacted>, secretKey=<redacted>, "
            "passphrase=<redacted>)"
        )


class DemoCredentialVaultError(RuntimeError):
    """A redacted vault failure safe to expose as a category."""

    def __init__(self, category: str) -> None:
        self.category = str(category)
        super().__init__(self.category)


class CredentialBackend(Protocol):
    def write(self, target_name: str, blob: bytes, persistence: int) -> None: ...

    def read(self, target_name: str) -> bytes | None: ...

    def delete(self, target_name: str) -> bool: ...


class _CredentialW(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(wintypes.BYTE)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


class Win32CredentialBackend:
    """Minimal generic-credential adapter with no secret-bearing errors."""

    def __init__(self) -> None:
        try:
            self._advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        except (AttributeError, OSError) as error:
            raise DemoCredentialVaultError("vault_unsupported") from error

        credential_pointer = ctypes.POINTER(_CredentialW)
        self._advapi32.CredWriteW.argtypes = [ctypes.POINTER(_CredentialW), wintypes.DWORD]
        self._advapi32.CredWriteW.restype = wintypes.BOOL
        self._advapi32.CredReadW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(credential_pointer),
        ]
        self._advapi32.CredReadW.restype = wintypes.BOOL
        self._advapi32.CredDeleteW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
        ]
        self._advapi32.CredDeleteW.restype = wintypes.BOOL
        self._advapi32.CredFree.argtypes = [ctypes.c_void_p]
        self._advapi32.CredFree.restype = None

    def write(self, target_name: str, blob: bytes, persistence: int) -> None:
        buffer = (wintypes.BYTE * len(blob)).from_buffer_copy(blob)
        credential = _CredentialW()
        credential.Type = CRED_TYPE_GENERIC
        credential.TargetName = target_name
        credential.CredentialBlobSize = len(blob)
        credential.CredentialBlob = ctypes.cast(buffer, ctypes.POINTER(wintypes.BYTE))
        credential.Persist = persistence
        credential.UserName = DEMO_CREDENTIAL_LABEL
        if not self._advapi32.CredWriteW(ctypes.byref(credential), 0):
            raise DemoCredentialVaultError("vault_write_failed")

    def read(self, target_name: str) -> bytes | None:
        pointer = ctypes.POINTER(_CredentialW)()
        if not self._advapi32.CredReadW(
            target_name,
            CRED_TYPE_GENERIC,
            0,
            ctypes.byref(pointer),
        ):
            if ctypes.get_last_error() == ERROR_NOT_FOUND:
                return None
            raise DemoCredentialVaultError("vault_read_failed")
        try:
            credential = pointer.contents
            size = int(credential.CredentialBlobSize)
            if size <= 0:
                return b""
            return ctypes.string_at(credential.CredentialBlob, size)
        finally:
            self._advapi32.CredFree(pointer)

    def delete(self, target_name: str) -> bool:
        if self._advapi32.CredDeleteW(target_name, CRED_TYPE_GENERIC, 0):
            return True
        if ctypes.get_last_error() == ERROR_NOT_FOUND:
            return False
        raise DemoCredentialVaultError("vault_delete_failed")


class WindowsDemoCredentialVault:
    """Own the fixed Demo-only WinCred target and expose redacted metadata."""

    def __init__(
        self,
        *,
        backend: CredentialBackend | None = None,
        platform_name: str | None = None,
    ) -> None:
        self._platform_name = os.name if platform_name is None else platform_name
        self._supported = backend is not None or self._platform_name == "nt"
        self._backend = backend
        if self._backend is None and self._supported:
            self._backend = Win32CredentialBackend()

    def store(self, bundle: DemoCredentialBundle) -> None:
        backend = self._require_backend()
        values = (bundle.apiKey.strip(), bundle.secretKey.strip(), bundle.passphrase.strip())
        if not all(values):
            raise DemoCredentialVaultError("credential_incomplete")
        blob = json.dumps(
            {
                "v": 1,
                "apiKey": values[0],
                "secretKey": values[1],
                "passphrase": values[2],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(blob) > MAX_CREDENTIAL_BLOB_BYTES:
            raise DemoCredentialVaultError("credential_record_too_large")
        backend.write(DEMO_CREDENTIAL_TARGET, blob, CRED_PERSIST_LOCAL_MACHINE)

    def load(self) -> DemoCredentialBundle | None:
        blob = self._require_backend().read(DEMO_CREDENTIAL_TARGET)
        if blob is None:
            return None
        try:
            payload = json.loads(blob.decode("utf-8"))
            if not isinstance(payload, dict) or payload.get("v") != 1:
                raise ValueError("unsupported record")
            bundle = DemoCredentialBundle(
                apiKey=str(payload.get("apiKey") or "").strip(),
                secretKey=str(payload.get("secretKey") or "").strip(),
                passphrase=str(payload.get("passphrase") or "").strip(),
            )
            if not all((bundle.apiKey, bundle.secretKey, bundle.passphrase)):
                raise ValueError("incomplete record")
            return bundle
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
            raise DemoCredentialVaultError("credential_record_invalid") from error

    def delete(self) -> bool:
        return self._require_backend().delete(DEMO_CREDENTIAL_TARGET)

    def metadata(self) -> dict[str, object]:
        if not self._supported:
            return self._metadata(stored=False, status="unsupported", supported=False)
        try:
            stored = self.load() is not None
        except DemoCredentialVaultError:
            return self._metadata(stored=True, status="invalid", supported=True)
        return self._metadata(
            stored=stored,
            status="stored" if stored else "missing",
            supported=True,
        )

    def _require_backend(self) -> CredentialBackend:
        if self._backend is None:
            raise DemoCredentialVaultError("vault_unsupported")
        return self._backend

    @staticmethod
    def _metadata(*, stored: bool, status: str, supported: bool) -> dict[str, object]:
        return {
            "supported": supported,
            "stored": stored,
            "status": status,
            "targetLabel": DEMO_CREDENTIAL_LABEL,
            "persistence": "local_machine",
        }


DEMO_CREDENTIAL_VAULT = WindowsDemoCredentialVault()
