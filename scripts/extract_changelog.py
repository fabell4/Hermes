"""Extract release notes for a given version from CHANGELOG.md."""

import os
import re
import sys

version = os.environ.get("VERSION", "")
if not version:
    print("VERSION env var not set", file=sys.stderr)
    sys.exit(1)

try:
    content = open("CHANGELOG.md").read()
    pattern = rf"## \[{re.escape(version)}\][^\n]*\n(.*?)(?=\n## \[|\Z)"
    m = re.search(pattern, content, re.DOTALL)
    notes = m.group(1).strip() if m else ""
except Exception:
    notes = ""

with open("/tmp/changelog_notes.txt", "w") as f:
    f.write(notes)
