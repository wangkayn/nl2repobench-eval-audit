# Public post draft

I audited NL2RepoBench's evaluation command runner and found that 9 setup commands across 7/104
tasks are executed without the shell semantics present in the released task metadata.

The root cause is small but consequential: `shlex.split()` tokenizes a command; it does not evaluate
shell operators. Tokens such as `&&`, `>`, `>>`, and `&` are passed as ordinary argv to the first
program. Some affected setup commands still exit 0, so the failure can be silent.

I built a cross-platform A/B reproducer, pinned the upstream commit, documented the affected tasks,
and proposed a versioned repair that preserves historical comparability.

- Reproducer: https://github.com/wangkayn/nl2repobench-eval-audit
- Upstream issue: `ISSUE_URL_TO_BE_ADDED`
- Patch/PR: `PR_URL_TO_BE_ADDED`

Important scope note: the command-execution effect is reproduced. A numeric leaderboard impact is
not claimed until the same generated workspaces are rescored under both grader versions.
