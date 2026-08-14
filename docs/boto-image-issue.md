### Summary

The published `boto:1.0` grading image cannot execute its declared pytest command because the
image has no `pytest` executable. This is independent of the shell-semantics bug in #13.

### Reproduction

Evaluator source pin: `781a1da1ee41fb8edb0bed22f586d69111610edf`

Base image:

```text
ghcr.io/multimodal-art-projection/nl2repobench/boto@sha256:6a70abf3ae8807746d708ce0ab1de72e46f7b14e3f91d68c542a112523468c24
```

I overlaid the version-matched boto3 source (`69f915b4cf1961db9395db23e10c7210ad7a6814`),
applied the same workspace sanitization as the official post-processor, and ran each mode in a
fresh `linux/amd64` container.

`pip install -e .` succeeds, but the next released command cannot start:

```text
$ pytest --continue-on-collection-errors tests
/bin/sh: 1: pytest: not found
```

The direct-exec legacy path reports the equivalent OCI error:

```text
exec: "pytest": executable file not found in $PATH
```

Both paths therefore produce 0/1014 without collecting a test. Full argv, output, image identity,
and exit-code records are available in the audit repository:

- [fixed runner record](https://github.com/wangkayn/nl2repobench-eval-audit/blob/main/results/docker/full-reference-run/boto--fixed.json)
- [legacy runner record](https://github.com/wangkayn/nl2repobench-eval-audit/blob/main/results/docker/full-reference-run/boto--legacy.json)
- [source and image manifest](https://github.com/wangkayn/nl2repobench-eval-audit/blob/main/results/docker/full-reference-run/source-manifest.json)

### Suggested fix

Install a pinned test dependency set in the task image (at minimum `pytest`), validate that the
released pytest command starts during image publication, and version the corrected image so the
old digest remains available for historical reproduction.
