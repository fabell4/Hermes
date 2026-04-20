#!/usr/bin/env python3
"""
convert_to_sonar.py

Converts vulture, radon, and semgrep reports into SonarQube's
Generic Issue Import format.

NOTE: mypy is intentionally excluded here. It is handled natively by
SonarQube via sonar.python.mypy.reportPaths in sonar-project.properties,
which uses built-in rule definitions that SonarLint recognises for
"Show in IDE". Using the generic external format for mypy produces
external_mypy:* rule keys that SonarLint cannot resolve.

Usage:
    python convert_to_sonar.py --sonar-base-dir <path>

Output files (written to current directory):
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


def _map_to_new_format(severity: str, type_: str) -> tuple:
    """
    Map old-format severity + type to new SonarQube format fields.
    Returns (software_quality, impact_severity, clean_code_attribute).
    """
    quality_map = {
        "BUG": "RELIABILITY",
        "VULNERABILITY": "SECURITY",
        "CODE_SMELL": "MAINTAINABILITY",
    }
    clean_code_map = {
        "BUG": "LOGICAL",
        "VULNERABILITY": "TRUSTWORTHY",
        "CODE_SMELL": "CONVENTIONAL",
    }
    impact_map = {
        "INFO": "LOW",
        "MINOR": "LOW",
        "MAJOR": "MEDIUM",
        "CRITICAL": "HIGH",
        "BLOCKER": "HIGH",
    }
    return (
        quality_map.get(type_, "MAINTAINABILITY"),
        impact_map.get(severity, "MEDIUM"),
        clean_code_map.get(type_, "CONVENTIONAL"),
    )


def make_issue(engine_id, rule_id, severity, type_, file_path, line, message):
    """
    Build a (rule_definition, issue) pair in the new SonarQube Generic Issue
    Import format.  The rule carries engineId / cleanCodeAttribute / impacts;
    the issue carries only ruleId and primaryLocation.
    """
    software_quality, impact_severity, clean_code_attr = _map_to_new_format(
        severity, type_
    )
    rule = {
        "id": rule_id,
        "name": rule_id,
        "engineId": engine_id,
        "cleanCodeAttribute": clean_code_attr,
        "impacts": [
            {"softwareQuality": software_quality, "severity": impact_severity}
        ],
    }
    issue = {
        "ruleId": rule_id,
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
    return rule, issue


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
# vulture
# ---------------------------------------------------------------------------
def convert_vulture(report_path, base_dir):
    """
    Parse vulture plain-text output.
    Format: path/to/file.py:LINE: unused <thing> '<name>' (<confidence>% confidence)
    """
    pairs = []
    if not os.path.exists(report_path):
        print(f"  [skip] vulture report not found: {report_path}")
        return pairs

    with open(report_path, encoding="utf-8") as f:
        for line in f:
            parsed = _parse_path_lineno_message(line.rstrip())
            if parsed is None:
                continue
            file_path, lineno, message = parsed

            confidence = _extract_vulture_confidence(message)

            severity = "MAJOR" if confidence >= 90 else "MINOR"
            pairs.append(
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

    print(f"  vulture: {len(pairs)} issues")
    return pairs


# ---------------------------------------------------------------------------
# radon (cyclomatic complexity)
# ---------------------------------------------------------------------------
def convert_radon(cc_report_path, base_dir):
    """
    Parse radon cc JSON output.
    Only imports functions/methods rated C or worse (MAJOR) and E/F (CRITICAL).
    """
    pairs = []
    if not os.path.exists(cc_report_path):
        print(f"  [skip] radon cc report not found: {cc_report_path}")
        return pairs

    with open(cc_report_path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print("  [skip] radon report is not valid JSON")
            return pairs

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
            pairs.append(
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

    print(f"  radon: {len(pairs)} issues")
    return pairs


# ---------------------------------------------------------------------------
# semgrep
# ---------------------------------------------------------------------------
def convert_semgrep(report_path, base_dir):
    """
    Parse semgrep JSON output.
    """
    pairs = []
    if not os.path.exists(report_path):
        print(f"  [skip] semgrep report not found: {report_path}")
        return pairs

    with open(report_path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print("  [skip] semgrep report is not valid JSON")
            return pairs

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

        pairs.append(
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

    print(f"  semgrep: {len(pairs)} issues")
    return pairs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def write_report(pairs, output_path):
    """Write the SonarQube Generic Issue payload to *output_path*."""
    seen_rules: dict = {}
    issues = []
    for rule, issue in pairs:
        if rule["id"] not in seen_rules:
            seen_rules[rule["id"]] = rule
        issues.append(issue)
    payload = {"rules": list(seen_rules.values()), "issues": issues}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"  → written: {output_path} ({len(issues)} issues)")


def main():
    """Entry point: parse CLI args and run conversions."""
    parser = argparse.ArgumentParser(
        description="Convert tool reports to SonarQube Generic Issue format"
    )
    parser.add_argument(
        "--sonar-base-dir",
        default=".",
        help="SonarQube project base directory (sonar.projectBaseDir)",
    )
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

    write_report(
        convert_vulture(args.vulture, base),
        os.path.join(args.outdir, "sonar-vulture.json"),
    )
    write_report(
        convert_radon(args.radon, base), os.path.join(args.outdir, "sonar-radon.json")
    )
    write_report(
        convert_semgrep(args.semgrep, base),
        os.path.join(args.outdir, "sonar-semgrep.json"),
    )

    print("Done.")


if __name__ == "__main__":
    main()
