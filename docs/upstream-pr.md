## Summary

Candidate implementation for #13. String entries from `test_commands.json` are shell programs,
but the current runner tokenizes them with `shlex.split()` and passes the resulting argv directly
to `container.execute()`. This draft executes string commands through `/bin/sh -lc` while
preserving direct execution for callers that already pass an argv list.

## Changes

- execute string commands as `[/bin/sh, -lc, command]`;
- leave explicit list commands unchanged;
- change `parse` installation ordering from background `&` to conditional sequential `&&`;
- apply `AWS_DEFAULT_REGION` directly to the `binaryalert` pytest process;
- add Docker-independent regression tests for both runner modes and the two task-data corrections.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s tests -p 'test_command_runner_regression.py' -v
```

Four regression tests pass without requiring a Docker daemon. The independent process-level A/B
reproducer is available at https://github.com/wangkayn/nl2repobench-eval-audit.

### Real-image validation

The draft was also exercised against all seven public `linux/amd64` task images. Each legacy/fixed
pair used a fresh container with the same version-matched reference-source overlay and official
workspace sanitization.

The two clearest reference-input score-path changes are:

- `asteval`: 0/227 legacy, 227/227 fixed;
- `arxiv-mcp-server`: 0/23 legacy, 18/23 fixed.

The remaining tasks show the expected file, process, installation, or environment changes even
where the reference-input score is unchanged. Exact image digests, source commits, argv,
stdout/stderr, exit codes, timings, and file hashes are recorded in the
[real-image findings](https://github.com/wangkayn/nl2repobench-eval-audit/blob/334c5e0bc423e2b4abff3f8d6e0e67a788a12ab9/results/docker/full-reference-run/FINDINGS.md)
and [raw artifacts](https://github.com/wangkayn/nl2repobench-eval-audit/tree/334c5e0bc423e2b4abff3f8d6e0e67a788a12ab9/results/docker/full-reference-run).

Two independent findings are tracked separately: the `boto:1.0` image lacks `pytest` (#15), and
the `parse` suite reports 98 passed against a declared denominator of 96 (#16).

## Compatibility note

This intentionally changes grading semantics and may change scores relative to historical runs.
The PR is opened as a draft so the project can first decide whether the corrected behavior should
be gated behind a named grader version or accompanied by an explicit legacy mode. It does not claim
a numeric leaderboard delta; the real-image experiment uses controlled reference source, and paired
rescoring of the original generated workspaces remains separate work.
