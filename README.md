# A Shell Is Not `shlex`

[![reproduce](https://github.com/wangkayn/nl2repobench-eval-audit/actions/workflows/reproduce.yml/badge.svg)](https://github.com/wangkayn/nl2repobench-eval-audit/actions/workflows/reproduce.yml)

An independent, process-level audit of command execution in
[NL2RepoBench](https://github.com/multimodal-art-projection/NL2RepoBench).

## Finding

At pinned upstream commit
[`781a1da`](https://github.com/multimodal-art-projection/NL2RepoBench/commit/781a1da1ee41fb8edb0bed22f586d69111610edf),
the official post-processor passes each string command through `shlex.split()` and then invokes
`container.execute()` with the resulting argument vector. No shell interprets the command.

That distinction affects 9 setup commands across 7 of the benchmark's 104 tasks:

| Task | Construct | Observed legacy behavior |
|---|---|---|
| `arxiv-mcp-server` | `&&` | `pip install -e .` is never invoked |
| `asteval` | `>` | `asteval/version.py` is not created |
| `boto` | `>>` | `README.rst` is not updated |
| `jinja` | two `>>` commands | `LICENSE.txt` and `README.md` are not updated |
| `parse` | `&` | `&` and the second `pip` command become arguments to the first `pip` process |
| `tqdm` | `>` and a leading assignment | `version.py` is not created; the assignment is treated as an executable name |
| `binaryalert` | shell builtin `set` | no executable named `set` exists; the region is absent during pytest |

Several of these failures are silent: `echo` prints the would-be redirection tokens and exits 0,
while the target file remains absent. The official scoring loop continues to later commands.

## Controlled A/B reproduction

The reproducer executes real local processes using two command runners:

1. **Legacy official semantics:** `subprocess.run(shlex.split(command))`, equivalent at the
   process boundary to passing the same argv list to `docker exec`.
2. **Prime adapter semantics:** a persistent `bash -lc` script using `eval "$command"`, matching
   the independent adapter merged in
   [PrimeIntellect-ai/prime-envs#325](https://github.com/PrimeIntellect-ai/prime-envs/pull/325).

Instrumented `pip`, `pytest`, and `touch` fixture executables record which programs actually run,
which environment variables they receive, and whether pytest starts before setup finishes. They do
not install packages or require network access.

Upstream tracking:

- [Issue #13: command strings lose shell semantics](https://github.com/multimodal-art-projection/NL2RepoBench/issues/13)
- [Draft PR #14: candidate shell-backed runner and task corrections](https://github.com/multimodal-art-projection/NL2RepoBench/pull/14)

Run:

```bash
python3 reproduce.py --summary
python3 -m unittest -v
```

Expected summary:

```text
18/18 assertions passed
legacy: shell operators and assignments are not interpreted
prime adapter: redirection/&&/assignment cases work
prime adapter: parse still races; pytest starts before editable install completes
```

## Real-image seven-task A/B

A second reproducer runs the pinned legacy evaluator and the corrected runner against the seven
public `linux/amd64` task images. For a meaningful test path, it overlays version-matched upstream
reference source after applying the official workspace sanitization steps. Every task/mode pair
uses a fresh container.

```bash
python3 prepare_candidate_images.py \
  --sources /path/to/version-matched-sources

python3 docker_ab.py \
  --image-template 'nl2repo-audit/{task}:candidate' \
  --workspace-kind 'upstream reference source overlay; official sanitization applied'
```

The completed run, including exact image digests, source commits, argv, stdout/stderr, file hashes,
and command timings, is in
[`results/docker/full-reference-run`](results/docker/full-reference-run). Its largest score-path
delta is `asteval`: legacy cannot collect tests (0/227), while the corrected path passes 227/227.
`arxiv-mcp-server` changes from 0/23 to 18/23 with the selected reference commit.

The run also exposes two independent data/image problems: the published `boto:1.0` image has no
`pytest` executable ([upstream #15](https://github.com/multimodal-art-projection/NL2RepoBench/issues/15)),
and the `parse` suite reports 98 passed against a declared denominator of 96
([upstream #16](https://github.com/multimodal-art-projection/NL2RepoBench/issues/16)).

## What this establishes

- The official runner does not preserve the shell semantics present in the released task commands.
- The independent Prime adapter avoids the `shlex.split()` failure for redirection, `&&`, leading
  assignment, and `binaryalert` environment persistence.
- Prime's adapter still honors the released `parse` command literally, so its background editable
  install can race with pytest.

## What this does **not** yet establish

This repository does not claim a numeric change to a published leaderboard. The real-image run uses
reference source to isolate the evaluator path, not a submitted model workspace. A defensible
leaderboard impact still requires rescoring the exact same generated workspaces under both the
pinned legacy grader and a versioned corrected grader. Until that paired experiment is complete,
the result quantifies evaluator effects on controlled reference inputs, not a leaderboard correction.

## Proposed remediation

The benchmark should not silently overwrite historical semantics. A versioned repair can provide:

- `legacy-781a1da`: exact current execution for reproduction of historical results;
- `corrected-shell-v1`: explicit shell execution with per-command logs and exit codes;
- task-data corrections for `parse` (`&` versus the intended ordering operator) and
  `binaryalert` (`set` versus `export`), reviewed separately;
- score reports that name the grader version.

See [`docs/upstream-issue.md`](docs/upstream-issue.md) and
[`docs/upstream-pr.md`](docs/upstream-pr.md) for the submitted report and patch rationale. The
real-image follow-ups are preserved in [`docs/real-image-issue-update.md`](docs/real-image-issue-update.md)
and [`docs/real-image-pr-update.md`](docs/real-image-pr-update.md).

## Scope and attribution

This is an independent audit. It is not affiliated with the NL2RepoBench authors or Prime Intellect.
The repository contains an original reproducer and short command excerpts needed to demonstrate the
behavior; it does not redistribute benchmark images, hidden tests, generated repositories, or
reference solutions.
