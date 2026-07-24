from __future__ import annotations

import ctypes
import json
import os
import sys
from ctypes import wintypes
from pathlib import Path
from typing import Any


class SecretStoreError(RuntimeError):
    """Raised when a production secret cannot be protected or recovered."""


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def _blob_from_bytes(value: bytes) -> tuple[_DataBlob, Any]:
    buffer = ctypes.create_string_buffer(value, len(value))
    blob = _DataBlob(
        len(value),
        ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)),
    )
    return blob, buffer


def _protect_windows(value: bytes, description: str) -> bytes:
    source, source_buffer = _blob_from_bytes(value)
    output = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    ok = crypt32.CryptProtectData(
        ctypes.byref(source),
        description,
        None,
        None,
        None,
        0x01,
        ctypes.byref(output),
    )
    _ = source_buffer
    if not ok:
        raise SecretStoreError(f"Windows DPAPI encryption failed: {ctypes.GetLastError()}")
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        kernel32.LocalFree(output.pbData)


def _unprotect_windows(value: bytes) -> bytes:
    source, source_buffer = _blob_from_bytes(value)
    output = _DataBlob()
    description = wintypes.LPWSTR()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(source),
        ctypes.byref(description),
        None,
        None,
        None,
        0x01,
        ctypes.byref(output),
    )
    _ = source_buffer
    if not ok:
        raise SecretStoreError(f"Windows DPAPI decryption failed: {ctypes.GetLastError()}")
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        kernel32.LocalFree(output.pbData)


def safe_secret_id(value: str) -> str:
    normalized = "".join(char for char in value.lower() if char.isalnum() or char in "-_.")
    if not normalized or normalized in {".", ".."}:
        raise ValueError("Secret identifier is invalid.")
    return normalized


class SecureSecretStore:
    """Current-user secret storage.

    Windows values are encrypted with DPAPI and cannot be decrypted by another
    Windows account. Other platforms intentionally support environment-only
    secrets so plaintext credentials are never written as a fallback.
    """

    def __init__(self, root: Path | str):
        self.root = Path(root).resolve()
        self.index_path = self.root / "index.json"

    @property
    def persistent_storage_available(self) -> bool:
        return sys.platform == "win32"

    def initialize(self) -> dict[str, Any]:
        self.root.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self._write_index({"schema": "temple-ai-studio.secure-secrets.v1", "items": []})
        return self.status()

    def put(self, secret_id: str, value: str, environment_name: str | None = None) -> dict[str, Any]:
        if not value:
            raise ValueError("Secret value cannot be empty.")
        secret_id = safe_secret_id(secret_id)
        if not self.persistent_storage_available:
            raise SecretStoreError(
                "Persistent secret storage is unavailable on this platform. "
                "Use an environment variable instead."
            )
        self.initialize()
        target = self.root / f"{secret_id}.dpapi"
        target.write_bytes(_protect_windows(value.encode("utf-8"), f"Temple AI Studio:{secret_id}"))
        index = self._read_index()
        items = [item for item in index["items"] if item["id"] != secret_id]
        items.append(
            {
                "id": secret_id,
                "storage": "windows-dpapi-current-user",
                "environmentName": environment_name,
                "fileName": target.name,
            }
        )
        index["items"] = sorted(items, key=lambda item: item["id"])
        self._write_index(index)
        return {
            "id": secret_id,
            "stored": True,
            "storage": "windows-dpapi-current-user",
            "environmentName": environment_name,
        }

    def get(self, secret_id: str, environment_name: str | None = None) -> str | None:
        secret_id = safe_secret_id(secret_id)
        if environment_name and os.environ.get(environment_name):
            return os.environ[environment_name]
        target = self.root / f"{secret_id}.dpapi"
        if not target.exists():
            return None
        if not self.persistent_storage_available:
            raise SecretStoreError("This secret is protected by Windows DPAPI.")
        return _unprotect_windows(target.read_bytes()).decode("utf-8")

    def has(self, secret_id: str, environment_name: str | None = None) -> bool:
        return bool(self.get(secret_id, environment_name))

    def delete(self, secret_id: str) -> dict[str, Any]:
        secret_id = safe_secret_id(secret_id)
        target = self.root / f"{secret_id}.dpapi"
        existed = target.exists()
        if existed:
            target.unlink()
        index = self._read_index()
        index["items"] = [item for item in index.get("items", []) if item.get("id") != secret_id]
        self._write_index(index)
        return {"id": secret_id, "deleted": existed}

    def status(self) -> dict[str, Any]:
        index = self._read_index()
        return {
            "schema": "temple-ai-studio.secure-secrets-status.v1",
            "persistentStorageAvailable": self.persistent_storage_available,
            "storage": "windows-dpapi-current-user" if self.persistent_storage_available else "environment-only",
            "items": [
                {
                    "id": item.get("id"),
                    "configured": (self.root / item.get("fileName", "")).exists()
                    or bool(os.environ.get(item.get("environmentName", ""))),
                    "environmentName": item.get("environmentName"),
                }
                for item in index.get("items", [])
            ],
        }

    def _read_index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {"schema": "temple-ai-studio.secure-secrets.v1", "items": []}
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def _write_index(self, payload: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.index_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.index_path)
