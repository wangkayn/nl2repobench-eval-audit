# Draft upstream issue

## Title

`[Evaluation correctness] testShell commands lose shell semantics in 7/104 tasks`

## Body

### Summary

At commit `781a1da1ee41fb8edb0bed22f586d69111610edf`, string commands from
`test_commands.json` are tokenized with `shlex.split()` and passed as an argv list to
`client.container.execute()`. Because no shell evaluates that argv, operators and shell-only syntax
in the released task metadata are treated as ordinary arguments.

I found 9 affected setup commands across 7/104 tasks:

- `arxiv-mcp-server`: `&&`
- `asteval`: `>`
- `boto`: `>>`
- `jinja`: two `>>` commands
- `parse`: `&`
- `tqdm`: `>` and a leading environment assignment
- `binaryalert`: shell builtin `set`

### Process-level reproduction

The linked reproducer executes the exact argv produced by `shlex.split()` and compares it with a
shell-backed runner. It uses instrumented fixture executables so it can assert whether `pip` and
`pytest` actually ran, which files were created, and which environment variables reached pytest.

Observed examples:

- `touch README.md && pip install -e .` can complete without ever invoking `pip`;
- `echo ... > asteval/version.py` exits 0 but does not create the file;
- `SETUPTOOLS_SCM_PRETEND_VERSION_FOR_TQDM=0.0.1 ...` is treated as an executable name;
- `set AWS_DEFAULT_REGION=us-east-1` cannot run as a direct executable, and the following pytest
  process has no region value.

Reproducer: https://github.com/wangkayn/nl2repobench-eval-audit

### Impact boundary

This report establishes a command-execution inconsistency and its setup side effects. I have not
yet claimed a numeric leaderboard delta. That requires paired rescoring of identical generated
workspaces under the legacy and corrected graders.

### Compatibility concern

Changing the runner can change scores relative to historical leaderboard entries. I suggest naming
and preserving the current semantics (for example, `legacy-781a1da`) while introducing a versioned
corrected grader rather than silently replacing the historical path.

### Possible remediation

1. Execute commands through an explicit shell or execute the full command sequence in one shell
   session when state must persist.
2. Record and expose every setup exit code instead of silently continuing without qualification.
3. Review `parse` (`&`) and `binaryalert` (`set`) as task-data issues separately from the generic
   runner change.
4. Add regression tests for redirection, chaining, assignments, state persistence, and setup
   failure handling.

I can submit a focused PR once the preferred compatibility/versioning behavior is agreed.
