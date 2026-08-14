#!/usr/bin/env python3
"""Run NL2RepoBench's seven shell-sensitive tasks in real Docker images.

This is an evaluator-path experiment, not a model rescore unless a generated
workspace is supplied separately.  Each mode starts from a fresh copy of the
same pinned public image.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


REGISTRY = "ghcr.io/multimodal-art-projection/nl2repobench"
OFFICIAL_COMMIT = "781a1da1ee41fb8edb0bed22f586d69111610edf"

TASKS: dict[str, dict[str, Any]] = {
    "arxiv-mcp-server": {
        "total": 23,
        "legacy": [
            "touch README.md && pip install -e .",
            "pytest --continue-on-collection-errors tests",
        ],
        "fixed": [
            "touch README.md && pip install -e .",
            "pytest --continue-on-collection-errors tests",
        ],
        "probe_paths": ["README.md", "&&", "pip", "install"],
    },
    "asteval": {
        "total": 227,
        "legacy": [
            "echo \"version = '0.0.1'\" > asteval/version.py",
            "pip install -e .",
            "pytest --continue-on-collection-errors tests",
        ],
        "fixed": [
            "echo \"version = '0.0.1'\" > asteval/version.py",
            "pip install -e .",
            "pytest --continue-on-collection-errors tests",
        ],
        "probe_paths": ["asteval/version.py"],
    },
    "boto": {
        "total": 1014,
        "legacy": [
            "echo 'This is sample RST text.' >> README.rst",
            "pip install  -e .",
            "pytest --continue-on-collection-errors tests",
        ],
        "fixed": [
            "echo 'This is sample RST text.' >> README.rst",
            "pip install  -e .",
            "pytest --continue-on-collection-errors tests",
        ],
        "probe_paths": ["README.rst"],
    },
    "jinja": {
        "total": 911,
        "legacy": [
            "echo 'This is sample license text.' >> LICENSE.txt",
            "echo 'This is sample README text.' >> README.md",
            "pip install  -e .",
            "pytest --continue-on-collection-errors tests",
        ],
        "fixed": [
            "echo 'This is sample license text.' >> LICENSE.txt",
            "echo 'This is sample README text.' >> README.md",
            "pip install  -e .",
            "pytest --continue-on-collection-errors tests",
        ],
        "probe_paths": ["LICENSE.txt", "README.md"],
    },
    "parse": {
        "total": 96,
        "legacy": [
            "pip install -e . & pip install -r tests/requirements.txt",
            "pytest --continue-on-collection-errors",
        ],
        "fixed": [
            "pip install -e . && pip install -r tests/requirements.txt",
            "pytest --continue-on-collection-errors",
        ],
        "probe_paths": ["setup.py", "tests/requirements.txt"],
    },
    "tqdm": {
        "total": 139,
        "legacy": [
            "echo \"__version__ = '0.0.1'\" > tqdm/version.py",
            "SETUPTOOLS_SCM_PRETEND_VERSION_FOR_TQDM=0.0.1 pip install -e .",
            "pytest --continue-on-collection-errors tests",
        ],
        "fixed": [
            "echo \"__version__ = '0.0.1'\" > tqdm/version.py",
            "SETUPTOOLS_SCM_PRETEND_VERSION_FOR_TQDM=0.0.1 pip install -e .",
            "pytest --continue-on-collection-errors tests",
        ],
        "probe_paths": ["tqdm/version.py"],
    },
    "binaryalert": {
        "total": 77,
        "legacy": [
            "set AWS_DEFAULT_REGION=us-east-1",
            "pytest --continue-on-collection-errors tests",
        ],
        "fixed": [
            "AWS_DEFAULT_REGION=us-east-1 pytest --continue-on-collection-errors tests",
        ],
        "probe_paths": [],
    },
}


def host_run(
    argv: list[str], timeout: int = 900, check: bool = False
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        argv,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if check and completed.returncode:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {shlex.join(argv)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def docker(*args: str, timeout: int = 900, check: bool = False) -> subprocess.CompletedProcess[str]:
    return host_run(["docker", *args], timeout=timeout, check=check)


def process_record(argv: list[str]) -> dict[str, Any]:
    completed = host_run(argv, timeout=60)
    home = str(Path.home())
    return {
        "args": argv,
        "returncode": completed.returncode,
        "stdout": completed.stdout.replace(home, "$HOME"),
        "stderr": completed.stderr.replace(home, "$HOME"),
    }


def collect_environment(image_template: str, workspace_kind: str) -> dict[str, Any]:
    return {
        "timestamp": dt.datetime.now().astimezone().isoformat(),
        "host_platform": platform.platform(),
        "host_machine": platform.machine(),
        "python": sys.version,
        "docker_version": process_record(["docker", "version"]),
        "colima_status": process_record(["colima", "status"]),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "image_template": image_template,
        "workspace_kind": workspace_kind,
    }


def image_metadata(image: str) -> dict[str, Any]:
    inspected = docker("image", "inspect", image, check=True)
    raw = json.loads(inspected.stdout)[0]
    repo_digests = raw.get("RepoDigests") or []
    return {
        "reference": image,
        "id": raw.get("Id"),
        "repo_digests": repo_digests,
        "architecture": raw.get("Architecture"),
        "os": raw.get("Os"),
        "size": raw.get("Size"),
    }


def inspect_paths(container: str, paths: list[str]) -> dict[str, Any]:
    if not paths:
        return {}
    code = (
        "import hashlib,json,os,sys; "
        "paths=json.loads(sys.argv[1]); out={}; "
        "exec(\"for p in paths:\\n"
        " q='/workspace/'+p\\n"
        " d={'exists':os.path.lexists(q)}\\n"
        " if d['exists']:\\n"
        "  st=os.lstat(q); d.update(size=st.st_size,mode=oct(st.st_mode & 0o777),"
        "is_file=os.path.isfile(q),is_dir=os.path.isdir(q))\\n"
        "  if os.path.isfile(q):\\n"
        "   b=open(q,'rb').read(); d['sha256']=hashlib.sha256(b).hexdigest(); "
        "d['preview']=b[:4096].decode('utf-8','replace')\\n"
        " out[p]=d\"); print(json.dumps(out,sort_keys=True))"
    )
    result = docker(
        "exec", container, "python", "-c", code, json.dumps(paths), timeout=60
    )
    if result.returncode:
        return {"probe_error": result.stderr or result.stdout}
    return json.loads(result.stdout)


def parse_pytest(commands: list[dict[str, Any]], total: int) -> dict[str, Any]:
    counts = {"passed": 0, "failed": 0, "errors": 0, "total": total}
    for item in commands:
        if "pytest" not in item["command"].lower():
            continue
        output = item["stdout"] + "\n" + item["stderr"]
        for line in output.splitlines():
            match = re.search(r"(\d+) passed", line)
            if match:
                counts["passed"] += int(match.group(1))
            match = re.search(r"(\d+) failed", line)
            if match:
                counts["failed"] += int(match.group(1))
            match = re.search(r"(\d+) error", line)
            if match:
                counts["errors"] += int(match.group(1))
    counts["success_rate"] = min(counts["passed"] / total, 1) if total else 0
    return counts


def run_one(
    task: str, mode: str, output_dir: Path, image_template: str
) -> dict[str, Any]:
    spec = TASKS[task]
    image = image_template.format(task=task)
    safe_task = re.sub(r"[^a-zA-Z0-9_.-]", "-", task)
    container = f"nl2repo-ab-{safe_task}-{mode}-{os.getpid()}"
    result: dict[str, Any] = {
        "task": task,
        "mode": mode,
        "image": image_metadata(image),
        "official_commit": OFFICIAL_COMMIT,
        "runner": "shlex.split + direct exec" if mode == "legacy" else "/bin/sh -lc",
        "commands": [],
    }

    docker("rm", "-f", container, timeout=60)
    try:
        docker(
            "create",
            "--platform",
            "linux/amd64",
            "--name",
            container,
            "--workdir",
            "/workspace",
            image,
            "tail",
            "-f",
            "/dev/null",
            timeout=120,
            check=True,
        )
        docker("start", container, timeout=120, check=True)
        result["before"] = inspect_paths(container, spec["probe_paths"])

        for index, command in enumerate(spec[mode], start=1):
            argv = shlex.split(command) if mode == "legacy" else ["/bin/sh", "-lc", command]
            started = time.monotonic()
            try:
                completed = docker(
                    "exec", "--workdir", "/workspace", container, *argv, timeout=1800
                )
                command_result = {
                    "index": index,
                    "command": command,
                    "argv": argv,
                    "exit_code": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                    "duration_seconds": round(time.monotonic() - started, 3),
                    "timed_out": False,
                }
            except subprocess.TimeoutExpired as exc:
                command_result = {
                    "index": index,
                    "command": command,
                    "argv": argv,
                    "exit_code": None,
                    "stdout": exc.stdout or "",
                    "stderr": exc.stderr or "",
                    "duration_seconds": round(time.monotonic() - started, 3),
                    "timed_out": True,
                }
            result["commands"].append(command_result)
            print(
                f"[{task}/{mode}] {index}/{len(spec[mode])} "
                f"exit={command_result['exit_code']} time={command_result['duration_seconds']}s",
                flush=True,
            )

        result["after"] = inspect_paths(container, spec["probe_paths"])
        result["pytest"] = parse_pytest(result["commands"], spec["total"])
    finally:
        removed = docker("rm", "-f", container, timeout=120)
        result["cleanup_exit_code"] = removed.returncode

    path = output_dir / f"{safe_task}--{mode}.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def write_summary(
    results: list[dict[str, Any]], output_dir: Path, workspace_kind: str
) -> None:
    lines = [
        "# Real-image legacy/fixed A/B summary",
        "",
        f"Official source pin: `{OFFICIAL_COMMIT}`",
        "",
        f"Workspace input: {workspace_kind}.",
        "",
        "This proves evaluator-path effects,",
        "but is not a model rescore because no generated model workspace was available locally.",
        "",
        "| Task | Mode | Command exits | Passed / denominator | Rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for result in results:
        exits = ", ".join(
            "timeout" if cmd["timed_out"] else str(cmd["exit_code"])
            for cmd in result["commands"]
        )
        pytest = result["pytest"]
        lines.append(
            f"| {result['task']} | {result['mode']} | {exits} | "
            f"{pytest['passed']} / {pytest['total']} | {pytest['success_rate']:.4f} |"
        )
    (output_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", nargs="+", choices=TASKS, default=list(TASKS))
    parser.add_argument("--modes", nargs="+", choices=["legacy", "fixed"], default=["legacy", "fixed"])
    parser.add_argument("--pull", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--image-template",
        default=f"{REGISTRY}/{{task}}:1.0",
        help="Docker image template containing a {task} placeholder",
    )
    parser.add_argument(
        "--workspace-kind",
        default="base image only",
        help="Human-readable description recorded with the run",
    )
    args = parser.parse_args()

    stamp = dt.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S%z")
    output_dir = args.output or Path("results") / "docker" / stamp
    output_dir.mkdir(parents=True, exist_ok=True)

    environment = collect_environment(args.image_template, args.workspace_kind)
    (output_dir / "environment.json").write_text(
        json.dumps(environment, indent=2, default=str), encoding="utf-8"
    )

    if args.pull:
        for task in args.tasks:
            image = f"{REGISTRY}/{task}:1.0"
            print(f"[pull] {image}", flush=True)
            docker("pull", "--platform", "linux/amd64", image, timeout=3600, check=True)

    results = []
    for task in args.tasks:
        for mode in args.modes:
            results.append(run_one(task, mode, output_dir, args.image_template))
            write_summary(results, output_dir, args.workspace_kind)
    print(f"Results: {output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
