#!/usr/bin/env python3
"""
convert_to_sonar.py

Converts mypy, vulture, radon, and semgrep reports into SonarQube's
Generic Issue Import format.

Usage:
    python convert_to_sonar.py --sonar-base-dir <path>

Output files (written to current directory):
    sonar-mypy.json
    sonar-vulture.json
    sonar-radon.json
    sonar-semgrep.json

SonarQube Generic Issue format reference:
    https://docs.sonarsource.com/sonarqube/latest/analyzing-source-code/importing-external-issues/generic-issue-import-format/
"""

import argparse
import json
import os
from pathlib import Path


def make_issue(engine_id, rule_id, severity, type_, file_path, line, message):
    """Build a single SonarQube generic issue dict."""
    return {
        "engineId": engine_id,
        "ruleId": rule_id,
        "severity": severity,  # INFO | MINOR | MAJOR | CRITICAL | BLOCKER
        "type": type_,  # BUG | VULNERABILITY | CODE_SMELL
        "primaryLocation": {
            "message": message,
            "filePath": file_path,
            "textRange": {
                "startLine": max(1, line),
                "endLine": max(1, line),
                "startColumn": 0,
                "endColumn": 1,
            },
        },
    }


def normalise_path(raw_path, base_dir):
    """
    Strip the base_dir prefix so filePath is relative to the SonarQube
    project root (sonar.projectBaseDir).
    """
    try:
        return str(Path(raw_path).resolve().relative_to(Path(base_dir).resolve()))
    except ValueError:
        # Already relative or can't relativise — return as-is
        return raw_path


def _parse_path_lineno_message(line: str) -> tuple[str, str, str] | None:
    """Parse `path:LINE: message` lines using right splits for Windows path safety."""
    head, sep, message = line.rpartition(": ")
    if not sep:
        return None

    file_path, sep, lineno = head.rpartition(":")
    if not sep or not lineno.isdigit():
        return None

    return file_path, lineno, message.strip()


def _extract_mypy_code(message: str) -> tuple[str, str | None]:
    """Return (`message_without_code`, `code_or_none`) for trailing `[error-code]`."""
    if not message.endswith("]"):
        return message.strip(), None

    code_start = message.rfind(" [")
    if code_start == -1:
        return message.strip(), None

    candidate = message[code_start + 2 : -1].strip()
    if not candidate:
        return message.strip(), None

    return message[:code_start].rstrip(), candidate


def _parse_mypy_line(
    line: str, severity_map: dict[str, str]
) -> tuple[str, int, str, str, str | None] | None:
    """Parse a mypy line into structured fields or return None if not parseable."""
    head, sep, message = line.rpartition(": ")
    if not sep:
        return None

    before_level, sep, level = head.rpartition(": ")
    if not sep:
        return None

    file_path, sep, lineno = before_level.rpartition(":")
    if not sep or not lineno.isdigit():
        return None

    level = level.strip().lower()
    if level not in severity_map:
        return None

    parsed_message, code = _extract_mypy_code(message.strip())
    return file_path, int(lineno), level, parsed_message, code


def _extract_vulture_confidence(message: str) -> int:
    """Extract confidence percentage if present; default to 80."""
    confidence = 80
    confidence_suffix = "% confidence)"
    suffix_index = message.rfind(confidence_suffix)
    if suffix_index == -1:
        return confidence

    start_index = message.rfind("(", 0, suffix_index)
    if start_index == -1:
        return confidence

    candidate = message[start_index + 1 : suffix_index].strip()
    if candidate.isdigit():
        return int(candidate)

    return confidence


# ---------------------------------------------------------------------------
# mypy
# ---------------------------------------------------------------------------
def convert_mypy(report_path, base_dir):
    """
    Parse mypy plain-text output.
    Format: path/to/file.py:LINE: error: message  [error-code]
    """
    issues = []
    if not os.path.exists(report_path):
        print(f"  [skip] mypy report not found: {report_path}")
        return issues

    severity_map = {
        "error": "MAJOR",
        "warning": "MINOR",
        "note": "INFO",
    }

    with open(report_path) as f:
        for line in f:
            parsed = _parse_mypy_line(line.rstrip(), severity_map)
            if parsed is None:
                continue

            file_path, lineno, level, message, code = parsed

            rule_id = f"mypy:{code}" if code else f"mypy:{level}"
            issues.append(
                make_issue(
                    engine_id="mypy",
                    rule_id=rule_id,
                    severity=severity_map.get(level, "MINOR"),
                    type_="CODE_SMELL",
                    file_path=normalise_path(file_path, base_dir),
                    line=lineno,
                    message=message.strip(),
                )
            )

    print(f"  mypy: {len(issues)} issues")
    return issues


# ---------------------------------------------------------------------------
# vulture
# ---------------------------------------------------------------------------
def convert_vulture(report_path, base_dir):
    """
    Parse vulture plain-text output.
    Format: path/to/file.py:LINE: unused <thing> '<name>' (<confidence>% confidence)
    """
    issues = []
    if not os.path.exists(report_path):
        print(f"  [skip] vulture report not found: {report_path}")
        return issues

    with open(report_path) as f:
        for line in f:
            parsed = _parse_path_lineno_message(line.rstrip())
            if parsed is None:
                continue
            file_path, lineno, message = parsed

            confidence = _extract_vulture_confidence(message)

            severity = "MAJOR" if confidence >= 90 else "MINOR"
            issues.append(
                make_issue(
                    engine_id="vulture",
                    rule_id="vulture:unused-code",
                    severity=severity,
                    type_="CODE_SMELL",
                    file_path=normalise_path(file_path, base_dir),
                    line=int(lineno),
                    message=message.strip(),
                )
            )

    print(f"  vulture: {len(issues)} issues")
    return issues


# ---------------------------------------------------------------------------
# radon (cyclomatic complexity)
# ---------------------------------------------------------------------------
def convert_radon(cc_report_path, base_dir):
    """
    Parse radon cc JSON output.
    Only imports functions/methods rated C or worse (MAJOR) and E/F (CRITICAL).
    """
    issues = []
    if not os.path.exists(cc_report_path):
        print(f"  [skip] radon cc report not found: {cc_report_path}")
        return issues

    with open(cc_report_path) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print("  [skip] radon report is not valid JSON")
            return issues

    rank_severity = {
        "A": None,  # skip
        "B": None,  # skip
        "C": "MAJOR",
        "D": "MAJOR",
        "E": "CRITICAL",
        "F": "CRITICAL",
    }

    for file_path, blocks in data.items():
        for block in blocks:
            rank = block.get("rank", "A")
            severity = rank_severity.get(rank)
            if severity is None:
                continue
            name = block.get("name", "unknown")
            complexity = block.get("complexity", "?")
            lineno = block.get("lineno", 1)
            block_type = block.get("type", "function")
            message = (
                f"{block_type} '{name}' has cyclomatic complexity {complexity} "
                f"(rank {rank})"
            )
            issues.append(
                make_issue(
                    engine_id="radon",
                    rule_id=f"radon:complexity-{rank}",
                    severity=severity,
                    type_="CODE_SMELL",
                    file_path=normalise_path(file_path, base_dir),
                    line=int(lineno),
                    message=message,
                )
            )

    print(f"  radon: {len(issues)} issues")
    return issues


# ---------------------------------------------------------------------------
# semgrep
# ---------------------------------------------------------------------------
def convert_semgrep(report_path, base_dir):
    """
    Parse semgrep JSON output.
    """
    issues = []
    if not os.path.exists(report_path):
        print(f"  [skip] semgrep report not found: {report_path}")
        return issues

    with open(report_path) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print("  [skip] semgrep report is not valid JSON")
            return issues

    severity_map = {
        "ERROR": "CRITICAL",
        "WARNING": "MAJOR",
        "INFO": "MINOR",
        "NOTE": "INFO",
    }

    type_map = {
        "ERROR": "VULNERABILITY",
        "WARNING": "VULNERABILITY",
        "INFO": "CODE_SMELL",
        "NOTE": "CODE_SMELL",
    }

    for result in data.get("results", []):
        raw_severity = result.get("extra", {}).get("severity", "WARNING").upper()
        file_path = result.get("path", "unknown")
        lineno = result.get("start", {}).get("line", 1)
        rule_id = result.get("check_id", "semgrep:unknown")
        message = result.get("extra", {}).get("message", "Semgrep finding").strip()

        issues.append(
            make_issue(
                engine_id="semgrep",
                rule_id=rule_id,
                severity=severity_map.get(raw_severity, "MAJOR"),
                type_=type_map.get(raw_severity, "CODE_SMELL"),
                file_path=normalise_path(file_path, base_dir),
                line=int(lineno),
                message=message,
            )
        )

    print(f"  semgrep: {len(issues)} issues")
    return issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def write_report(issues, output_path):
    payload = {"issues": issues}
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"  → written: {output_path} ({len(issues)} issues)")


def main():
    parser = argparse.ArgumentParser(
        description="Convert tool reports to SonarQube Generic Issue format"
    )
    parser.add_argument(
        "--sonar-base-dir",
        default=".",
        help="SonarQube project base directory (sonar.projectBaseDir)",
    )
    parser.add_argument("--mypy", default="mypy-report.txt", help="Path to mypy report")
    parser.add_argument(
        "--vulture", default="vulture-report.txt", help="Path to vulture report"
    )
    parser.add_argument(
        "--radon", default="radon-cc-report.json", help="Path to radon cc JSON report"
    )
    parser.add_argument(
        "--semgrep", default="semgrep-report.json", help="Path to semgrep JSON report"
    )
    parser.add_argument("--outdir", default=".", help="Directory to write output files")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    base = args.sonar_base_dir

    print("Converting reports to SonarQube Generic Issue format...")

    mypy_issues = convert_mypy(args.mypy, base)
    vulture_issues = convert_vulture(args.vulture, base)
    radon_issues = convert_radon(args.radon, base)
    semgrep_issues = convert_semgrep(args.semgrep, base)

    write_report(mypy_issues, os.path.join(args.outdir, "sonar-mypy.json"))
    write_report(vulture_issues, os.path.join(args.outdir, "sonar-vulture.json"))
    write_report(radon_issues, os.path.join(args.outdir, "sonar-radon.json"))
    write_report(semgrep_issues, os.path.join(args.outdir, "sonar-semgrep.json"))

    # SonarQube is configured to consume a single external issues file.
    combined_issues = mypy_issues + vulture_issues + radon_issues + semgrep_issues
    write_report(
        combined_issues, os.path.join(args.outdir, "sonar-external-issues.json")
    )

    print("Done.")


if __name__ == "__main__":
    main()
