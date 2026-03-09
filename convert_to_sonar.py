"""Convert tool reports into SonarQube Generic Issue format.

This script is intentionally fault-tolerant for CI:
- Missing input reports are treated as empty.
- Parse errors in one report do not fail conversion for others.
- A combined `sonar-external-issues.json` file is always written.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SEVERITIES = {"BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO"}
TYPES = {"BUG", "VULNERABILITY", "CODE_SMELL"}


MYPY_RE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+)(?::(?P<col>\d+))?:\s*error:\s*(?P<msg>.+?)(?:\s*\[(?P<code>[^\]]+)\])?$"
)
VULTURE_RE = re.compile(r"^(?P<path>.+?):(?P<line>\d+):\s*(?P<msg>.+)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert reports to SonarQube Generic Issue format")
    parser.add_argument("--sonar-base-dir", default="src")
    parser.add_argument("--mypy", default="mypy-report.txt")
    parser.add_argument("--vulture", default="vulture-report.txt")
    parser.add_argument("--radon", default="radon-cc-report.json")
    parser.add_argument("--semgrep", default="semgrep-report.json")
    parser.add_argument("--outdir", default=".")
    return parser.parse_args()


def normalize_path(path_str: str, repo_root: Path) -> str:
    p = Path(path_str)
    if p.is_absolute():
        try:
            p = p.relative_to(repo_root)
        except ValueError:
            return p.as_posix()
    return p.as_posix()


def add_issue(
    issues: list[dict[str, Any]],
    *,
    engine_id: str,
    rule_id: str,
    file_path: str,
    message: str,
    line: int,
    issue_type: str = "CODE_SMELL",
    severity: str = "MAJOR",
) -> None:
    issue_type = issue_type if issue_type in TYPES else "CODE_SMELL"
    severity = severity if severity in SEVERITIES else "MAJOR"
    line = max(1, int(line))
    issues.append(
        {
            "engineId": engine_id,
            "ruleId": rule_id,
            "type": issue_type,
            "severity": severity,
            "primaryLocation": {
                "message": message,
                "filePath": file_path,
                "textRange": {"startLine": line},
            },
        }
    )


def parse_mypy(path: Path, repo_root: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not path.exists():
        return issues

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = MYPY_RE.match(raw.strip())
        if not match:
            continue
        rule = match.group("code") or "mypy-error"
        add_issue(
            issues,
            engine_id="mypy",
            rule_id=rule,
            file_path=normalize_path(match.group("path"), repo_root),
            message=match.group("msg"),
            line=int(match.group("line")),
            issue_type="BUG",
            severity="MAJOR",
        )
    return issues


def parse_vulture(path: Path, repo_root: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not path.exists():
        return issues

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = VULTURE_RE.match(raw.strip())
        if not match:
            continue
        add_issue(
            issues,
            engine_id="vulture",
            rule_id="unused-code",
            file_path=normalize_path(match.group("path"), repo_root),
            message=match.group("msg"),
            line=int(match.group("line")),
            issue_type="CODE_SMELL",
            severity="MINOR",
        )
    return issues


def parse_radon(path: Path, repo_root: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not path.exists():
        return issues

    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return issues

    if not isinstance(data, dict):
        return issues

    for file_path, entries in data.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            rank = str(entry.get("rank", "?")).upper()
            complexity = entry.get("complexity", "?")
            obj_type = entry.get("type", "object")
            obj_name = entry.get("name", "unknown")
            line = int(entry.get("lineno", 1) or 1)
            sev = "MINOR"
            if rank in {"E", "F"}:
                sev = "CRITICAL"
            elif rank in {"C", "D"}:
                sev = "MAJOR"

            add_issue(
                issues,
                engine_id="radon",
                rule_id=f"cyclomatic-rank-{rank.lower()}",
                file_path=normalize_path(str(file_path), repo_root),
                message=(
                    f"High cyclomatic complexity: {obj_type} '{obj_name}' "
                    f"has rank {rank} (complexity={complexity})."
                ),
                line=line,
                issue_type="CODE_SMELL",
                severity=sev,
            )
    return issues


def map_semgrep_severity(value: str) -> str:
    sev = value.upper()
    if sev in {"ERROR", "HIGH", "CRITICAL"}:
        return "CRITICAL"
    if sev in {"WARNING", "MEDIUM"}:
        return "MAJOR"
    if sev in {"LOW", "INFO"}:
        return "MINOR"
    return "MAJOR"


def parse_semgrep(path: Path, repo_root: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not path.exists():
        return issues

    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return issues

    results = data.get("results", []) if isinstance(data, dict) else []
    if not isinstance(results, list):
        return issues

    for result in results:
        if not isinstance(result, dict):
            continue
        path_value = str(result.get("path", ""))
        start = result.get("start", {}) if isinstance(result.get("start", {}), dict) else {}
        line = int(start.get("line", 1) or 1)
        check_id = str(result.get("check_id", "semgrep-rule"))
        extra = result.get("extra", {}) if isinstance(result.get("extra", {}), dict) else {}
        message = str(extra.get("message", "Semgrep finding"))
        severity = map_semgrep_severity(str(extra.get("severity", "WARNING")))

        add_issue(
            issues,
            engine_id="semgrep",
            rule_id=check_id,
            file_path=normalize_path(path_value, repo_root),
            message=message,
            line=line,
            issue_type="VULNERABILITY",
            severity=severity,
        )
    return issues


def write_report(path: Path, issues: list[dict[str, Any]]) -> None:
    payload = {"issues": issues}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    issues_by_tool = {
        "mypy": parse_mypy(Path(args.mypy), repo_root),
        "vulture": parse_vulture(Path(args.vulture), repo_root),
        "radon": parse_radon(Path(args.radon), repo_root),
        "semgrep": parse_semgrep(Path(args.semgrep), repo_root),
    }

    for tool, issues in issues_by_tool.items():
        write_report(outdir / f"sonar-{tool}-issues.json", issues)

    combined: list[dict[str, Any]] = []
    for tool_issues in issues_by_tool.values():
        combined.extend(tool_issues)

    write_report(outdir / "sonar-external-issues.json", combined)
    print(
        "Generated Sonar issue reports:",
        ", ".join(f"{tool}={len(issues)}" for tool, issues in issues_by_tool.items()),
        f"total={len(combined)}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
