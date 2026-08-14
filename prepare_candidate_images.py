#!/usr/bin/env python3
"""Build valid-workspace overlays on the seven official benchmark images."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


REGISTRY = "ghcr.io/multimodal-art-projection/nl2repobench"
PACKAGE_FILES = [
    "setup.py",
    "pyproject.toml",
    "setup.cfg",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-test.txt",
    "tox.ini",
    "pytest.ini",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
    "environment.yml",
    "conda-env.yaml",
    "manifest.in",
    "MANIFEST.in",
]
SOURCES = {
    "arxiv-mcp-server": "arxiv-mcp-server",
    "asteval": "asteval",
    "boto": "boto",
    "jinja": "jinja",
    "parse": "parse",
    "tqdm": "tqdm",
    "binaryalert": "binaryalert",
}
SOURCE_REPOSITORIES = {
    "arxiv-mcp-server": "https://github.com/blazickjp/arxiv-mcp-server",
    "asteval": "https://github.com/lmfit/asteval",
    "boto": "https://github.com/boto/boto3",
    "jinja": "https://github.com/pallets/jinja",
    "parse": "https://github.com/r1chardj0n3s/parse",
    "tqdm": "https://github.com/tqdm/tqdm",
    "binaryalert": "https://github.com/airbnb/binaryalert",
}


def run(argv: list[str], cwd: Path | None = None) -> str:
    completed = subprocess.run(
        argv, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    if completed.returncode:
        raise RuntimeError(f"command failed ({completed.returncode}): {argv}\n{completed.stdout}")
    return completed.stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--tasks", nargs="+", choices=SOURCES, default=list(SOURCES))
    parser.add_argument("--contexts", type=Path, default=Path("build-contexts"))
    parser.add_argument(
        "--record-existing",
        action="store_true",
        help="Record source/image identities without rebuilding contexts or images",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    dockerfile = repo_root / "infra" / "candidate.Dockerfile"
    args.contexts.mkdir(parents=True, exist_ok=True)
    manifest_path = args.contexts / "manifest.json"
    manifest: dict[str, dict[str, str]] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    for task in args.tasks:
        source = (args.sources / SOURCES[task]).resolve()
        context = (args.contexts / task).resolve()
        workspace = context / "workspace"
        commit = run(["git", "rev-parse", "HEAD"], cwd=source).strip()
        base = f"{REGISTRY}/{task}:1.0"
        target = f"nl2repo-audit/{task}:candidate"
        if not args.record_existing:
            if context.exists():
                shutil.rmtree(context)
            workspace.mkdir(parents=True)

            rsync = ["rsync", "-a", "--exclude=/.git", "--exclude=/tests"]
            rsync.extend(f"--exclude={name}" for name in PACKAGE_FILES)
            rsync.extend([f"{source}/", f"{workspace}/"])
            run(rsync)

            print(f"[build] {task}: {commit} -> {target}", flush=True)
            output = run(
                [
                    "docker",
                    "build",
                    "--platform",
                    "linux/amd64",
                    "--build-arg",
                    f"BASE_IMAGE={base}",
                    "--file",
                    str(dockerfile),
                    "--tag",
                    target,
                    str(context),
                ]
            )
            print(output, end="", flush=True)

        base_info = json.loads(run(["docker", "image", "inspect", base]))[0]
        target_info = json.loads(run(["docker", "image", "inspect", target]))[0]
        manifest[task] = {
            "source_repository": SOURCE_REPOSITORIES[task],
            "commit": commit,
            "base": base,
            "base_id": base_info["Id"],
            "base_repo_digests": base_info.get("RepoDigests") or [],
            "image": target,
            "image_id": target_info["Id"],
        }

    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
