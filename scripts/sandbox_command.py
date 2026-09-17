"""Run a command with the project sandbox credentials without changing AWS profiles."""

import json
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
credentials = json.loads((root / ".local/sandbox_credentials.json").read_text())
env = os.environ.copy()
env.update({key.upper(): value for key, value in credentials.items()})
env.update(
    AWS_DEFAULT_REGION="us-east-1",
    AWS_REGION="us-east-1",
    PYTHONUTF8="1",
    PYTHONIOENCODING="utf-8",
    AGENTCORE_SUPPRESS_RECOMMENDATION="1",
)
arguments = sys.argv[1:]
workdir = root
if arguments[:1] == ["--deployment"]:
    workdir = root / "deployment"
    arguments = arguments[1:]
sys.exit(subprocess.call(arguments, cwd=workdir, env=env))
