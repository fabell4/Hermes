"""Extract release notes for a given version from CHANGELOG.md."""

import os
import re
import sys
import tempfile

version = os.environ.get("VERSION", "")
if not version:
    print("VERSION env var not set", file=sys.stderr)
    sys.exit(1)

try:
    with open("CHANGELOG.md") as fh:
        content = fh.read()
    pattern = rf"## \[{re.escape(version)}\][^\n]*\n(.*?)(?=\n## \[|\Z)"
    m = re.search(pattern, content, re.DOTALL)
    notes = m.group(1).strip() if m else ""
except Exception:
    notes = ""

out_path = os.environ.get("NOTES_FILE", os.path.join(tempfile.gettempdir(), "changelog_notes.txt"))
fd = os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as f:
    f.write(notes)
