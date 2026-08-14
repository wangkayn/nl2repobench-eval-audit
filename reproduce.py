#!/usr/bin/env python3
"""Controlled process-level A/B reproduction for NL2RepoBench command runners."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple


SIMPLE_CASES = [
    (
        "arxiv &&",
        "touch README.md && pip install -e .",
        None,
    ),
    (
        "asteval >",
        "echo \"version = '0.0.1'\" > asteval/version.py",
        "asteval/version.py",
    ),
    (
        "boto >>",
        "echo 'This is sample RST text.' >> README.rst",
        "README.rst",
    ),
    (
        "jinja LICENSE >>",
        "echo 'This is sample license text.' >> LICENSE.txt",
        "LICENSE.txt",
    ),
    (
        "jinja README >>",
        "echo 'This is sample README text.' >> README.md",
        "README.md",
    ),
    (
        "tqdm >",
        "echo \"__version__ = '0.0.1'\" > tqdm/version.py",
        "tqdm/version.py",
    ),
    (
        "tqdm env assignment",
        "SETUPTOOLS_SCM_PRETEND_VERSION_FOR_TQDM=0.0.1 pip install -e .",
        None,
    ),
]

PARSE_COMMANDS = [
    "pip install -e . & pip install -r tests/requirements.txt",
    "pytest --continue-on-collection-errors",
]

BINARYALERT_COMMANDS = [
    "set AWS_DEFAULT_REGION=us-east-1",
    "pytest --continue-on-collection-errors tests",
]


def write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def make_fixture(root: Path) -> Tuple[Path, Path, Dict[str, str]]:
    workspace = root / "workspace"
    fakebin = root / "fakebin"
    workspace.mkdir()
    fakebin.mkdir()
    for directory in ("asteval", "tqdm", "tests"):
        (workspace / directory).mkdir()
    (workspace / "tests" / "requirements.txt").write_text("# fixture\n", encoding="utf-8")
    trace = root / "trace.log"

    write_executable(
        fakebin / "touch",
        """#!/usr/bin/env python3
import pathlib
import sys

for item in sys.argv[1:]:
    try:
        pathlib.Path(item).touch()
    except (IsADirectoryError, OSError):
        pass
""",
    )
    write_executable(
        fakebin / "pip",
        """#!/usr/bin/env python3
import os
import pathlib
import sys
import time

args = " ".join(sys.argv[1:])
trace = pathlib.Path(os.environ["TRACE_FILE"])
version = os.environ.get("SETUPTOOLS_SCM_PRETEND_VERSION_FOR_TQDM", "<unset>")
with trace.open("a", encoding="utf-8") as handle:
    handle.write(f"pip argv={args!r} env={version!r}\\n")
if " & " in f" {args} ":
    with trace.open("a", encoding="utf-8") as handle:
        handle.write("literal_ampersand_seen=1\\n")
    raise SystemExit(7)
if args == "install -e .":
    delay = float(os.environ.get("EDITABLE_SLEEP", "0"))
    if delay:
        time.sleep(delay)
    pathlib.Path(os.environ["WORKSPACE_DIR"], ".editable_done").touch()
""",
    )
    write_executable(
        fakebin / "pytest",
        """#!/usr/bin/env python3
import os
import pathlib

workspace = pathlib.Path(os.environ["WORKSPACE_DIR"])
trace = pathlib.Path(os.environ["TRACE_FILE"])
ready = int((workspace / ".editable_done").exists())
region = os.environ.get("AWS_DEFAULT_REGION", "<unset>")
with trace.open("a", encoding="utf-8") as handle:
    handle.write(f"pytest_seen_editable={ready}\\n")
    handle.write(f"pytest_aws_region={region}\\n")
print("1 passed in 0.01s")
""",
    )

    env = os.environ.copy()
    env.update(
        {
            "PATH": os.pathsep.join((str(fakebin), env.get("PATH", ""))),
            "TRACE_FILE": str(trace),
            "WORKSPACE_DIR": str(workspace),
        }
    )
    return workspace, trace, env


def run_legacy(command: str, workspace: Path, env: Dict[str, str]) -> dict:
    """Mirror the official process boundary: shlex.split, then direct argv execution."""
    argv = shlex.split(command)
    try:
        result = subprocess.run(
            argv,
            cwd=str(workspace),
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        return {
            "argv": argv,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except FileNotFoundError as error:
        return {
            "argv": argv,
            "exit_code": 127,
            "stdout": "",
            "stderr": str(error),
        }


def normalize_prime_command(command: str) -> str:
    """Mirror Prime's special handling for the released binaryalert `set NAME=value`."""
    if command.startswith("set ") and "=" in command:
        name, value = command.removeprefix("set ").split("=", 1)
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            return "export {}={}".format(name, shlex.quote(value))
    return command


def run_prime(commands: List[str], workspace: Path, env: Dict[str, str]) -> dict:
    """Mirror the current Prime adapter's persistent bash + eval execution model."""
    script_lines = [
        "set -o pipefail",
        "cd {}".format(shlex.quote(str(workspace))),
        "export PATH={}".format(shlex.quote(env["PATH"])),
        "__nl2repo_run() {",
        '  local command="$1"',
        '  eval "$command"',
        "}",
    ]
    for command in commands:
        script_lines.append(
            "__nl2repo_run {}".format(shlex.quote(normalize_prime_command(command)))
        )
    result = subprocess.run(
        ["/bin/bash", "-lc", "\n".join(script_lines)],
        cwd=str(workspace),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def read_optional(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def observe_simple(name: str, target: Optional[str], workspace: Path, trace: Path) -> dict:
    trace_text = read_optional(trace)
    observation = {"trace": trace_text}
    if name == "arxiv &&":
        observation.update(
            {
                "pip_called": "pip argv=" in (trace_text or ""),
                "literal_ampersand_file": (workspace / "&&").exists(),
                "editable_finished": (workspace / ".editable_done").exists(),
            }
        )
    if target is not None:
        observation["target_contents"] = read_optional(workspace / target)
    if name == "tqdm env assignment":
        observation["editable_finished"] = (workspace / ".editable_done").exists()
    return observation


def run_simple_cases() -> List[dict]:
    results = []
    for name, command, target in SIMPLE_CASES:
        with tempfile.TemporaryDirectory(prefix="nl2repo-legacy-") as temp:
            workspace, trace, env = make_fixture(Path(temp))
            legacy = run_legacy(command, workspace, env)
            legacy["observed"] = observe_simple(name, target, workspace, trace)
        with tempfile.TemporaryDirectory(prefix="nl2repo-prime-") as temp:
            workspace, trace, env = make_fixture(Path(temp))
            prime = run_prime([command], workspace, env)
            prime["observed"] = observe_simple(name, target, workspace, trace)
        results.append({"case": name, "command": command, "legacy": legacy, "prime": prime})
    return results


def run_parse_race() -> dict:
    with tempfile.TemporaryDirectory(prefix="nl2repo-parse-legacy-") as temp:
        workspace, trace, env = make_fixture(Path(temp))
        legacy = run_legacy(PARSE_COMMANDS[0], workspace, env)
        legacy["trace"] = read_optional(trace)
    with tempfile.TemporaryDirectory(prefix="nl2repo-parse-prime-") as temp:
        workspace, trace, env = make_fixture(Path(temp))
        env["EDITABLE_SLEEP"] = "1.0"
        prime = run_prime(PARSE_COMMANDS, workspace, env)
        prime["trace"] = read_optional(trace)
        prime["editable_finished_at_shell_exit"] = (workspace / ".editable_done").exists()
    return {"commands": PARSE_COMMANDS, "legacy": legacy, "prime": prime}


def run_binaryalert_environment() -> dict:
    with tempfile.TemporaryDirectory(prefix="nl2repo-binaryalert-legacy-") as temp:
        workspace, trace, env = make_fixture(Path(temp))
        command_results = [run_legacy(command, workspace, env) for command in BINARYALERT_COMMANDS]
        legacy = {"command_results": command_results, "trace": read_optional(trace)}
    with tempfile.TemporaryDirectory(prefix="nl2repo-binaryalert-prime-") as temp:
        workspace, trace, env = make_fixture(Path(temp))
        prime = run_prime(BINARYALERT_COMMANDS, workspace, env)
        prime["trace"] = read_optional(trace)
    return {"commands": BINARYALERT_COMMANDS, "legacy": legacy, "prime": prime}


def build_checks(report: dict) -> List[Tuple[str, bool]]:
    cases = {item["case"]: item for item in report["simple_cases"]}
    arxiv = cases["arxiv &&"]
    checks = [
        ("legacy arxiv never calls pip", not arxiv["legacy"]["observed"]["pip_called"]),
        ("legacy arxiv receives literal &&", arxiv["legacy"]["observed"]["literal_ampersand_file"]),
        ("Prime arxiv calls pip", arxiv["prime"]["observed"]["pip_called"]),
    ]
    for case_name in ("asteval >", "boto >>", "jinja LICENSE >>", "jinja README >>", "tqdm >"):
        case = cases[case_name]
        checks.append(
            ("legacy {} misses target".format(case_name), case["legacy"]["observed"]["target_contents"] is None)
        )
        checks.append(
            ("Prime {} creates target".format(case_name), case["prime"]["observed"]["target_contents"] is not None)
        )
    tqdm_env = cases["tqdm env assignment"]
    checks.extend(
        [
            ("legacy assignment is treated as executable", tqdm_env["legacy"]["exit_code"] == 127),
            (
                "Prime passes tqdm version environment to pip",
                "env='0.0.1'" in (tqdm_env["prime"]["observed"]["trace"] or ""),
            ),
            (
                "Prime parse starts pytest before editable install finishes",
                "pytest_seen_editable=0" in (report["parse_race"]["prime"]["trace"] or ""),
            ),
            (
                "legacy binaryalert loses AWS region",
                "pytest_aws_region=<unset>" in (report["binaryalert_environment"]["legacy"]["trace"] or ""),
            ),
            (
                "Prime binaryalert exports AWS region",
                "pytest_aws_region=us-east-1" in (report["binaryalert_environment"]["prime"]["trace"] or ""),
            ),
        ]
    )
    return checks


def run_audit() -> dict:
    report = {
        "upstream_commit": "781a1da1ee41fb8edb0bed22f586d69111610edf",
        "scope": {"affected_tasks": 7, "affected_commands": 9, "benchmark_tasks": 104},
        "simple_cases": run_simple_cases(),
        "parse_race": run_parse_race(),
        "binaryalert_environment": run_binaryalert_environment(),
    }
    checks = build_checks(report)
    report["assertions"] = [{"name": name, "passed": passed} for name, passed in checks]
    return report


def assert_report(report: dict) -> None:
    failed = [item["name"] for item in report["assertions"] if not item["passed"]]
    if failed:
        raise AssertionError("failed checks: {}".format(", ".join(failed)))


def print_summary(report: dict) -> None:
    passed = sum(item["passed"] for item in report["assertions"])
    total = len(report["assertions"])
    print("{}/{} assertions passed".format(passed, total))
    print("legacy: shell operators and assignments are not interpreted")
    print("prime adapter: redirection/&&/assignment cases work")
    print("prime adapter: parse still races; pytest starts before editable install completes")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", action="store_true", help="print a concise human-readable result")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = run_audit()
    assert_report(report)
    if args.summary:
        print_summary(report)
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

