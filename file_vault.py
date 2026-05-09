"""
File Vault — Tiered File Storage Engine
=========================================
Manages uploaded files with 4-tier sensitivity classification:
  PUBLIC  → Visible to Admin, Internal (Local LLM), and External (Cloud LLM)
  PII     → Visible to Admin & Internal; hash/encrypt before External
  SPII    → Visible to Admin only; always masked for Internal & External
  SECRET  → Visible to Admin & Internal; redacted for External

Think Google Drive, but every file is automatically classified
and access-controlled according to CONSAT data policy.

Author: CONSAT PoC Team
Date: May 9, 2026
"""

import hashlib
import json
import os
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Storage root ────────────────────────────────────────────────
VAULT_DIR = Path(__file__).resolve().parent / "vault_storage"
VAULT_DIR.mkdir(exist_ok=True)
MANIFEST_PATH = VAULT_DIR / "manifest.json"

# ── Tier definitions ────────────────────────────────────────────
TIERS = {
    "PUBLIC": {
        "label": "Public",
        "icon": "fa-lock-open",
        "color": "#16a34a",
        "admin": "visible",
        "internal": "visible",
        "external": "visible",
        "description": "Safe to share with anyone. Example: route_id, status.",
    },
    "PII": {
        "label": "PII",
        "icon": "fa-user-shield",
        "color": "#d97706",
        "admin": "visible",
        "internal": "visible",
        "external": "hash/encrypt",
        "description": "Contains personal data (full_name, registration_plate). Hash or encrypt before external sharing.",
    },
    "SPII": {
        "label": "Sensitive PII",
        "icon": "fa-shield-halved",
        "color": "#7c3aed",
        "admin": "visible",
        "internal": "always masked",
        "external": "always masked",
        "description": "Highly sensitive personal data (personal_number, phone, email). Always masked outside Admin view.",
    },
    "SECRET": {
        "label": "Company Secret",
        "icon": "fa-ban",
        "color": "#dc2626",
        "admin": "visible",
        "internal": "visible",
        "external": "redacted",
        "description": "Proprietary business data (eco_drive_score, cost_sek). Completely redacted for external partners.",
    },
}

# ── Auto-classification heuristics ──────────────────────────────
_EXTENSION_HINTS = {
    # Likely public
    ".md": "PUBLIC", ".txt": "PUBLIC", ".csv": "PUBLIC",
    ".json": "PUBLIC", ".xml": "PUBLIC", ".html": "PUBLIC",
    ".png": "PUBLIC", ".jpg": "PUBLIC", ".jpeg": "PUBLIC",
    ".svg": "PUBLIC", ".gif": "PUBLIC",
    # Likely PII
    ".vcf": "PII", ".xlsx": "PII", ".xls": "PII",
    # Likely secret
    ".pem": "SECRET", ".key": "SECRET", ".p12": "SECRET",
    ".env": "SECRET", ".pfx": "SECRET",
}

_FILENAME_KEYWORDS = {
    "SECRET": [
        "secret", "confidential", "internal_only", "proprietary",
        "cost", "salary", "financial", "budget", "invoice",
        "firmware", "credential", "api_key", "private_key",
    ],
    "SPII": [
        "personal_number", "personnummer", "ssn", "passport",
        "medical", "health_record", "biometric",
    ],
    "PII": [
        "driver", "employee", "customer", "contact",
        "phone", "email", "address", "name_list",
        "registration", "license",
    ],
}


def auto_classify(filename: str) -> str:
    """Guess sensitivity tier from filename and extension."""
    ext = Path(filename).suffix.lower()
    name_lower = filename.lower()

    # Check filename keywords (most sensitive first)
    for tier in ("SECRET", "SPII", "PII"):
        for kw in _FILENAME_KEYWORDS[tier]:
            if kw in name_lower:
                return tier

    # Fallback to extension hint
    return _EXTENSION_HINTS.get(ext, "PUBLIC")


# ── Manifest (in-memory + JSON persistence) ────────────────────

def _load_manifest() -> List[Dict]:
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_manifest(entries: List[Dict]):
    MANIFEST_PATH.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


_manifest: List[Dict] = _load_manifest()


def _persist():
    _save_manifest(_manifest)


# ── Public API ──────────────────────────────────────────────────

def add_file(
    filename: str,
    content_bytes: bytes,
    tier: Optional[str] = None,
    tags: Optional[List[str]] = None,
    description: str = "",
) -> Dict:
    """Store a file in the vault and return its metadata record."""
    file_id = f"VF-{uuid.uuid4().hex[:12].upper()}"
    if tier is None or tier not in TIERS:
        tier = auto_classify(filename)

    # Compute content hash for deduplication / integrity
    sha256 = hashlib.sha256(content_bytes).hexdigest()

    # Store on disk
    dest_dir = VAULT_DIR / tier.lower()
    dest_dir.mkdir(exist_ok=True)
    dest_path = dest_dir / f"{file_id}_{filename}"
    dest_path.write_bytes(content_bytes)

    ext = Path(filename).suffix.lower()
    entry = {
        "file_id": file_id,
        "filename": filename,
        "tier": tier,
        "size_bytes": len(content_bytes),
        "sha256": sha256,
        "extension": ext,
        "mime_guess": _guess_mime(ext),
        "tags": tags or [],
        "description": description,
        "uploaded_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "storage_path": str(dest_path.relative_to(VAULT_DIR)),
        "download_count": 0,
        "starred": False,
    }
    _manifest.append(entry)
    _persist()
    return entry


def list_files(
    tier: Optional[str] = None,
    search: Optional[str] = None,
    view: str = "admin",
) -> List[Dict]:
    """Return file list, optionally filtered. `view` controls masking."""
    results = list(_manifest)
    if tier:
        results = [f for f in results if f["tier"] == tier]
    if search:
        q = search.lower()
        results = [
            f for f in results
            if q in f["filename"].lower()
            or q in f.get("description", "").lower()
            or any(q in t.lower() for t in f.get("tags", []))
        ]

    if view == "admin":
        return results

    masked = []
    for f in results:
        entry = dict(f)
        t = entry["tier"]
        if view == "internal":
            if t == "SPII":
                entry["filename"] = _mask_string(entry["filename"])
                entry["description"] = "[MASKED]"
                entry["tags"] = ["[MASKED]"]
        elif view == "external":
            if t == "SPII":
                entry["filename"] = _mask_string(entry["filename"])
                entry["description"] = "[MASKED]"
                entry["tags"] = ["[MASKED]"]
            elif t == "PII":
                entry["filename"] = _hash_string(entry["filename"])
                entry["description"] = f"[HASH:{hashlib.sha256(entry['description'].encode()).hexdigest()[:12]}]"
            elif t == "SECRET":
                entry["filename"] = "[REDACTED]"
                entry["description"] = "[REDACTED]"
                entry["tags"] = ["[REDACTED]"]
                entry["size_bytes"] = 0
        masked.append(entry)
    return masked


def get_file(file_id: str) -> Optional[Dict]:
    for f in _manifest:
        if f["file_id"] == file_id:
            return f
    return None


def update_file(file_id: str, tier: Optional[str] = None,
                tags: Optional[List[str]] = None,
                description: Optional[str] = None,
                starred: Optional[bool] = None) -> Optional[Dict]:
    for f in _manifest:
        if f["file_id"] == file_id:
            if tier and tier in TIERS:
                # Move physical file
                old_path = VAULT_DIR / f["storage_path"]
                new_dir = VAULT_DIR / tier.lower()
                new_dir.mkdir(exist_ok=True)
                new_path = new_dir / f"{file_id}_{f['filename']}"
                if old_path.exists():
                    shutil.move(str(old_path), str(new_path))
                f["tier"] = tier
                f["storage_path"] = str(new_path.relative_to(VAULT_DIR))
            if tags is not None:
                f["tags"] = tags
            if description is not None:
                f["description"] = description
            if starred is not None:
                f["starred"] = starred
            f["updated_at"] = datetime.utcnow().isoformat() + "Z"
            _persist()
            return f
    return None


def delete_file(file_id: str) -> bool:
    global _manifest
    for i, f in enumerate(_manifest):
        if f["file_id"] == file_id:
            # Remove physical file
            path = VAULT_DIR / f["storage_path"]
            if path.exists():
                path.unlink()
            _manifest.pop(i)
            _persist()
            return True
    return False


def get_file_bytes(file_id: str) -> Optional[bytes]:
    entry = get_file(file_id)
    if not entry:
        return None
    path = VAULT_DIR / entry["storage_path"]
    if path.exists():
        return path.read_bytes()
    return None


def get_vault_stats() -> Dict:
    total = len(_manifest)
    by_tier = {}
    total_size = 0
    for t in TIERS:
        count = sum(1 for f in _manifest if f["tier"] == t)
        size = sum(f["size_bytes"] for f in _manifest if f["tier"] == t)
        by_tier[t] = {"count": count, "size_bytes": size}
        total_size += size
    return {
        "total_files": total,
        "total_size_bytes": total_size,
        "by_tier": by_tier,
        "starred_count": sum(1 for f in _manifest if f.get("starred")),
    }


# ── Helpers ─────────────────────────────────────────────────────

def _guess_mime(ext: str) -> str:
    mimes = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".csv": "text/csv",
        ".json": "application/json",
        ".xml": "application/xml",
        ".html": "text/html",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pem": "application/x-pem-file",
        ".key": "application/x-pem-file",
        ".env": "text/plain",
        ".zip": "application/zip",
    }
    return mimes.get(ext, "application/octet-stream")


def _mask_string(s: str) -> str:
    if len(s) <= 4:
        return "****"
    return s[:2] + "*" * (len(s) - 4) + s[-2:]


def _hash_string(s: str) -> str:
    return f"HASH:{hashlib.sha256(s.encode()).hexdigest()[:16]}"
