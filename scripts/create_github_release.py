"""Create or update a GitHub release via the API."""

import json
import os
import subprocess
import sys

tag = os.environ["TAG"]
version = os.environ["VERSION"]
gh_user = os.environ["GH_USERNAME"]
gh_pat = os.environ["GH_PAT"]
notes_file = os.environ.get("NOTES_FILE", "/tmp/changelog_notes.txt")
payload_file = os.environ.get("PAYLOAD_FILE", "/tmp/gh_release_payload.json")
response_file = os.environ.get("RESPONSE_FILE", "/tmp/gh_response.json")

is_pre = any(x in tag for x in ("alpha", "beta", "rc"))

try:
    notes = open(notes_file).read().strip()
except Exception:
    notes = ""

docker_line = f"**Docker image:** `docker pull ghcr.io/{gh_user}/hermes:{version}`"
body = f"{notes}\n\n---\n\n{docker_line}" if notes else docker_line

payload = {"tag_name": tag, "name": tag, "prerelease": is_pre, "body": body}

with open(payload_file, "w") as f:
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
