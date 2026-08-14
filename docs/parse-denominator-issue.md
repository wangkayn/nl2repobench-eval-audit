### Summary

The published `parse` task declares 96 test cases, but the supplied pytest suite reports 98 passed
and 1 skipped. This is separate from the shell command issue in #13.

### Reproduction

Evaluator source pin: `781a1da1ee41fb8edb0bed22f586d69111610edf`

Base image:

```text
ghcr.io/multimodal-art-projection/nl2repobench/parse@sha256:b62739aff75c836823bf0140ae6db4d329beb74cf79cdb170ed5adb85966ee18
```

With version-matched source (`334db144c2813e9029cb890bbd49edd30f67ab9b`) and the official
workspace sanitization, the released suite reports:

```text
collected 99 items
98 passed, 1 skipped
```

The task metadata used by the scorer declares `96`. The audit therefore records `98 / 96`; the
current `min(passed / total, 1)` cap hides this discrepancy in the final rate, but the numerator,
denominator, and task weighting are internally inconsistent.

Evidence:

- [fixed runner record](https://github.com/wangkayn/nl2repobench-eval-audit/blob/main/results/docker/full-reference-run/parse--fixed.json)
- [legacy runner record](https://github.com/wangkayn/nl2repobench-eval-audit/blob/main/results/docker/full-reference-run/parse--legacy.json)
- [source and image manifest](https://github.com/wangkayn/nl2repobench-eval-audit/blob/main/results/docker/full-reference-run/source-manifest.json)

### Suggested fix

First confirm whether the intended denominator should include all collected, non-skipped tests. If
so, update it to 98 and version the task metadata. It would also help to add an image-publication
check that compares the declared count with pytest's collected/passed totals on the reference
workspace.
