### Real-image validation of this draft

I ran the seven affected tasks in the public `linux/amd64` images using evaluator pin
`781a1da1ee41fb8edb0bed22f586d69111610edf`. Each legacy/fixed pair started from a fresh container
with the same version-matched reference-source overlay and official workspace sanitization.

The run validates the code and metadata changes in this draft at the process boundary:

- `/bin/sh -lc` restores redirection for `asteval`, `boto`, `jinja`, and `tqdm`;
- it restores `&&` chaining for `arxiv-mcp-server` and leading environment assignment for `tqdm`;
- changing `parse` from background `&` to sequential `&&` makes both installs complete before
  pytest;
- attaching `AWS_DEFAULT_REGION` to the `binaryalert` pytest command avoids relying on shell state
  across separate container-exec calls.

The strongest controlled score-path results are `asteval` (0/227 legacy, 227/227 fixed) and
`arxiv-mcp-server` (0/23 legacy, 18/23 fixed). `jinja`, `parse`, `tqdm`, and `binaryalert` show the
expected setup/environment changes without a reference-input score delta; a malformed setup step
is not guaranteed to affect every workspace's score.

Full immutable evidence:

- [seven-task findings](https://github.com/wangkayn/nl2repobench-eval-audit/blob/334c5e0bc423e2b4abff3f8d6e0e67a788a12ab9/results/docker/full-reference-run/FINDINGS.md)
- [raw per-mode records and image/source manifest](https://github.com/wangkayn/nl2repobench-eval-audit/tree/334c5e0bc423e2b4abff3f8d6e0e67a788a12ab9/results/docker/full-reference-run)
- [Docker harness](https://github.com/wangkayn/nl2repobench-eval-audit/blob/334c5e0bc423e2b4abff3f8d6e0e67a788a12ab9/docker_ab.py)

Two unrelated findings are tracked separately so they do not block review of the runner fix:
the `boto:1.0` image lacks `pytest` ([#15](https://github.com/multimodal-art-projection/NL2RepoBench/issues/15)),
and `parse` reports 98 passed against a declared denominator of 96
([#16](https://github.com/multimodal-art-projection/NL2RepoBench/issues/16)).

This remains a reference-input evaluator A/B, not a rescore of any published model workspace. I am
leaving the PR in draft while the project decides the grader-versioning and historical-compatibility
policy.
