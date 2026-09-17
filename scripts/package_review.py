"""Build and audit a source-and-evidence archive using an explicit allowlist."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "project_outcome"
OUTPUT.mkdir(exist_ok=True)
files = [
    ROOT / name
    for name in (
        "main.py",
        "config.json",
        "requirements.txt",
        "pyproject.toml",
        "uv.lock",
        "product_catalog.txt",
        "LICENSE.txt",
        "README.md",
        "ASSIGNMENT_AND_REPOSITORY.md",
        "SUBMISSION_STATUS.md",
        "REFLECTION.md",
        ".gitignore",
    )
]
for folder in ("lambda", "scripts", "tests", "docs", "evidence"):
    files.extend(
        path
        for path in (ROOT / folder).rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
files = sorted(set(files))
manifest = {
    path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in files
}
archive_path = OUTPUT / "Nitin_Mane_AI_Support_Agent_Review_Package.zip"
with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for path in files:
        archive.write(path, path.relative_to(ROOT).as_posix())
    archive.writestr("FILE_MANIFEST.json", json.dumps(manifest, indent=2))

credentials = json.loads((ROOT / ".local/sandbox_credentials.json").read_text())
secret_values = [v.encode() for v in credentials.values() if len(v) >= 16]
with zipfile.ZipFile(archive_path) as archive:
    names = archive.namelist()
    forbidden = [
        name
        for name in names
        if any(
            part in name.split("/")
            for part in (".local", ".venv", ".git", "__pycache__", ".pytest_cache")
        )
    ]
    secret_matches = [
        name
        for name in names
        if any(value in archive.read(name) for value in secret_values)
    ]
    mismatches = [
        name
        for name, checksum in manifest.items()
        if hashlib.sha256(archive.read(name)).hexdigest() != checksum
    ]
    crc_error = archive.testzip()
    uncompressed = sum(item.file_size for item in archive.infolist())
checksum = hashlib.sha256(archive_path.read_bytes()).hexdigest()
audit = {
    "checked_utc": datetime.now(timezone.utc).isoformat(),
    "archive": archive_path.name,
    "entries": len(names),
    "compressed_bytes": archive_path.stat().st_size,
    "uncompressed_bytes": uncompressed,
    "sha256": checksum,
    "forbidden_entries": forbidden,
    "secret_matches": secret_matches,
    "checksum_mismatches": mismatches,
    "crc_error": crc_error,
    "archive_integrity_pass": not (
        forbidden or secret_matches or mismatches or crc_error
    ),
    "submission_ready": json.loads((ROOT / "evidence/verification.json").read_text())[
        "submission_ready"
    ],
}
(OUTPUT / "PACKAGE_AUDIT.json").write_text(
    json.dumps(audit, indent=2), encoding="utf-8"
)
(OUTPUT / "SHA256SUMS.txt").write_text(
    checksum + "  " + archive_path.name + "\n", encoding="utf-8"
)
print(json.dumps(audit, indent=2))
assert audit["archive_integrity_pass"] and uncompressed < 500 * 1024 * 1024
