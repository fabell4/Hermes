"""Create or update a GitHub release via the API."""

import json
import os
import subprocess
import sys
import tempfile

tag = os.environ["TAG"]
version = os.environ["VERSION"]
gh_user = os.environ["GH_USERNAME"]
gh_pat = os.environ["GH_PAT"]
_tmpdir = tempfile.gettempdir()
notes_file = os.environ.get("NOTES_FILE", os.path.join(_tmpdir, "changelog_notes.txt"))
payload_file = os.environ.get("PAYLOAD_FILE", os.path.join(_tmpdir, "gh_release_payload.json"))
response_file = os.environ.get("RESPONSE_FILE", os.path.join(_tmpdir, "gh_response.json"))

is_pre = any(x in tag for x in ("alpha", "beta", "rc"))

try:
    with open(notes_file) as fh:
        notes = fh.read().strip()
except Exception:
    notes = ""

docker_line = f"**Docker image:** `docker pull ghcr.io/{gh_user}/hermes:{version}`"
body = f"{notes}\n\n---\n\n{docker_line}" if notes else docker_line

payload = {"tag_name": tag, "name": tag, "prerelease": is_pre, "body": body}

fd = os.open(payload_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as f:
    json.dump(payload, f)

base_url = f"https://api.github.com/repos/{gh_user}/hermes/releases"
headers = [
    "-H",
    f"Authorization: Bearer {gh_pat}",
    "-H",
    "Content-Type: application/json",
]

r = subprocess.run(
    [
        "curl",
        "-s",
        "-o",
        response_file,
        "-w",
        "%{http_code}",
        "-X",
        "POST",
        *headers,
        base_url,
        "-d",
        f"@{payload_file}",
    ],
    capture_output=True,
    text=True,
)
code = r.stdout.strip()

if code == "422":
    r2 = subprocess.run(
        ["curl", "-fsSL", *headers, f"{base_url}/tags/{tag}"],
        capture_output=True,
        text=True,
    )
    release_id = json.loads(r2.stdout)["id"]
    subprocess.run(
        [
            "curl",
            "-fsSL",
            "-X",
            "PATCH",
            *headers,
            f"{base_url}/{release_id}",
            "-d",
            f"@{payload_file}",
        ],
        check=True,
    )
elif code not in ("200", "201"):
    print(f"GitHub release API returned HTTP {code}", file=sys.stderr)
    sys.exit(1)
