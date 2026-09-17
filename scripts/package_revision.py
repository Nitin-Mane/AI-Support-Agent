"""Build the corrected source package and audit its contents without credentials."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "project_outcome"
OUTPUT.mkdir(exist_ok=True)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--revision", choices=("02", "03"), default="03")
parser.add_argument("--evidence-directory", type=Path, default=ROOT / "examples/cloud_final")
args = parser.parse_args()
files = [ROOT / name for name in (
    "main.py", "config.json", "requirements.txt", "pyproject.toml", "uv.lock",
    "product_catalog.txt", "LICENSE", "README.md", "REFLECTION.md",
    "REVISION_NOTES.md", ".gitignore",
)]
for name in ("lambda", "scripts", "tests", "docs", "examples"):
    files.extend(p for p in (ROOT / name).rglob("*") if p.is_file()
                 and "__pycache__" not in p.parts and p.suffix != ".pyc")
files = sorted(set(files))
manifest = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files}
archive_path = OUTPUT / f"Nitin_Mane_AI_Support_Agent_Revision_{args.revision}.zip"

# Audit against credential strings locally. Their values are never printed.
secret_values = set()
def collect(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, str) and len(item) >= 16 and any(
                word in key.lower() for word in ("accesskey", "access_key", "secret", "token", "password")
            ):
                secret_values.add(item.encode())
            else:
                collect(item)
    elif isinstance(value, list):
        for item in value:
            collect(item)

for path in (ROOT / ".local").glob("*credentials*.json"):
    collect(json.loads(path.read_text(encoding="utf-8")))
with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for path in files:
        archive.write(path, path.relative_to(ROOT).as_posix())
    archive.writestr("FILE_MANIFEST.json", json.dumps(manifest, indent=2))
with zipfile.ZipFile(archive_path) as archive:
    names = archive.namelist()
    forbidden = [n for n in names if any(part in n.split("/") for part in (
        ".local", ".venv", ".git", "deployment", "__pycache__", ".pytest_cache", "upstream", "assignment"
    ))]
    matches = [n for n in names if any(secret in archive.read(n) for secret in secret_values)]
    mismatches = [n for n, digest in manifest.items()
                  if hashlib.sha256(archive.read(n)).hexdigest() != digest]
    crc_error = archive.testzip()
    uncompressed = sum(i.file_size for i in archive.infolist())
checksum = hashlib.sha256(archive_path.read_bytes()).hexdigest()
cloud_path = args.evidence_directory / "verification.json"
cloud = json.loads(cloud_path.read_text()) if cloud_path.exists() else {}
tests_path = args.evidence_directory / "local_tests.json"
tests = json.loads(tests_path.read_text()) if tests_path.exists() else {}
cleanup_path = args.evidence_directory / "cleanup_verification.json"
cleanup = json.loads(cleanup_path.read_text()) if cleanup_path.exists() else {}
audit = {
    "checked_utc": datetime.now(timezone.utc).isoformat(),
    "archive": archive_path.name, "entries": len(names),
    "compressed_bytes": archive_path.stat().st_size, "uncompressed_bytes": uncompressed,
    "sha256": checksum, "forbidden_entries": forbidden, "secret_matches": matches,
    "checksum_mismatches": mismatches, "crc_error": crc_error,
    "archive_integrity_pass": not (forbidden or matches or mismatches or crc_error),
    "local_tests_passed": tests.get("passed"),
    "revised_source_deployed": cloud.get("uploaded_source_matches_current", False),
    "fresh_cloud_scenarios_passed": cloud.get("scenarios_passed", 0),
    "fresh_cloud_total_scenarios": cloud.get("total_scenarios", 6),
    "fresh_agentcore_cli_passed": cloud.get("deployment_cli_evidence", {}).get("passed", False),
    "cleanup_verified": cleanup.get("cleanup_verified", False),
    "submission_ready": cloud.get("submission_ready", False)
        and tests.get("exit_code") == 0 and cleanup.get("cleanup_verified", False),
    "evidence_directory": args.evidence_directory.resolve().relative_to(ROOT).as_posix(),
    "udacity_acceptance": "Pending re-review; this package has not been submitted",
}
(OUTPUT / f"REVISION_{args.revision}_PACKAGE_AUDIT.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
(OUTPUT / f"REVISION_{args.revision}_SHA256SUMS.txt").write_text(checksum + "  " + archive_path.name + "\n", encoding="utf-8")
print(json.dumps(audit, indent=2))
assert audit["archive_integrity_pass"] and uncompressed < 500 * 1024 * 1024
