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

## Compatibility note

This intentionally changes grading semantics and may change scores relative to historical runs.
The PR is opened as a draft so the project can first decide whether the corrected behavior should
be gated behind a named grader version or accompanied by an explicit legacy mode. It does not claim
a numeric leaderboard delta; paired rescoring remains separate work.
