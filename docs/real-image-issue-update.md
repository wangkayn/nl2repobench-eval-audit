### Real-image validation update

I have now run the seven affected tasks through both execution paths in the real public
`linux/amd64` images, pinned to evaluator commit
`781a1da1ee41fb8edb0bed22f586d69111610edf`.

Method: overlay version-matched upstream reference source, apply the official post-processor's
workspace sanitization, and start a fresh container for every task/mode pair. The fixed mode uses
`/bin/sh -lc`; it also applies the proposed `parse` ordering and `binaryalert` environment-command
corrections.

| Task | Legacy | Fixed | Direct observation |
|---|---:|---:|---|
| `arxiv-mcp-server` | 0/23 | 18/23 | Legacy `touch` receives the remaining tokens and `pip install -e .` never runs. |
| `asteval` | 0/227 | 227/227 | Legacy `echo` exits 0 without creating `asteval/version.py`; fixed creates it. |
| `boto` | 0/1014 | 0/1014 | Redirection is fixed, but the published image independently lacks `pytest` ([#15](https://github.com/multimodal-art-projection/NL2RepoBench/issues/15)). |
| `jinja` | 911/911 | 911/911 | Legacy performs neither append; fixed changes both target file hashes. The reference suite passes either way. |
| `parse` | 98/96 | 98/96 | Legacy pip rejects literal `&`; fixed installs sequentially. The released denominator is independently inconsistent ([#16](https://github.com/multimodal-art-projection/NL2RepoBench/issues/16)). |
| `tqdm` | 133/139 | 133/139 | Legacy creates no redirected file and treats the leading assignment as an executable; fixed setup succeeds. Both runs hit the same Keras timeout under emulation. |
| `binaryalert` | 70/77 | 70/77 | Legacy cannot execute shell builtin `set`; fixed applies the region to pytest. The same seven reference-suite failures remain. |

The immutable run artifacts include exact base-image digests, source commits, argv, stdout/stderr,
exit codes, timings, and before/after file hashes:

- [findings at audit commit `334c5e0`](https://github.com/wangkayn/nl2repobench-eval-audit/blob/334c5e0bc423e2b4abff3f8d6e0e67a788a12ab9/results/docker/full-reference-run/FINDINGS.md)
- [raw run directory](https://github.com/wangkayn/nl2repobench-eval-audit/tree/334c5e0bc423e2b4abff3f8d6e0e67a788a12ab9/results/docker/full-reference-run)
- [reproduction harness](https://github.com/wangkayn/nl2repobench-eval-audit/blob/334c5e0bc423e2b4abff3f8d6e0e67a788a12ab9/docker_ab.py)

This confirms real evaluator-path failures and shows that at least two are score-changing on the
controlled reference input. It is **not** a leaderboard rescore: the generated workspaces used for
published model submissions were not available. Historical comparability still calls for a named
legacy grader plus a versioned corrected grader, rather than silently rewriting old scores.
