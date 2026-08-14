# Real-image seven-task legacy/fixed A/B

Date: 2026-08-14 (Asia/Shanghai)

## Method

- Evaluator source pin: `781a1da1ee41fb8edb0bed22f586d69111610edf`.
- Runtime: Docker Engine 29.5.2 on a `linux/amd64` Colima guest (4 CPUs, 8 GiB RAM).
- Base images: the seven public `ghcr.io/multimodal-art-projection/nl2repobench/<task>:1.0` images. Exact repository digests are recorded in `source-manifest.json`.
- Workspace: version-matched upstream reference source, sanitized like the official post-processor (candidate package metadata and root `tests/` removed), then copied over the official hidden-test image.
- Isolation: a fresh container was created for every task/mode pair and removed afterward.
- Legacy runner: `shlex.split(command)` followed by direct exec.
- Fixed runner: `/bin/sh -lc command`, plus the command-data fixes for `parse` (`&` to `&&`) and `binaryalert` (region assignment attached to pytest).

This is a real evaluator-path A/B. It is **not** a rescore of a submitted model workspace because that workspace was not available locally.

## Results

| Task | Legacy command exits | Fixed command exits | Legacy passed | Fixed passed | Observed effect |
|---|---:|---:|---:|---:|---|
| arxiv-mcp-server | `1, 1` | `0, 1` | 0/23 | 18/23 | Legacy passes `&& pip install -e .` to `touch`; `-e` is rejected and installation never runs. Fixed installs the package and makes 18 tests runnable. |
| asteval | `0, 0, 1` | `0, 0, 0` | 0/227 | 227/227 | Legacy `echo` prints the literal `>` and path but creates no file. Fixed creates `asteval/version.py`; all tests pass. |
| boto | `0, 0, 127` | `0, 0, 127` | 0/1014 | 0/1014 | Legacy does not append to `README.rst`; fixed does. Independently, the official image has no `pytest` executable, so neither mode can run tests. |
| jinja | `0, 0, 0, 0` | `0, 0, 0, 0` | 911/911 | 911/911 | Legacy performs neither append; fixed changes both file hashes and appends the expected text. The reference workspace passes in both modes. |
| parse | `1, 0` | `0, 0` | 98/96 | 98/96 | Legacy pip rejects literal `&` as an invalid requirement. Fixed performs the editable install and requirements install sequentially. Tests import from `/workspace` and pass anyway. The official denominator is 96 although pytest reports 98 passed. |
| tqdm | `0, 127, 1` | `0, 0, 1` | 133/139 | 133/139 | Legacy does not overwrite `version.py`, then tries to execute `SETUPTOOLS_SCM_PRETEND_VERSION_FOR_TQDM=0.0.1` as a program. Fixed overwrites the file and installs successfully. Both runs hit the same emulated-CPU Keras timeout. |
| binaryalert | `127, 1` | `1` | 70/77 | 70/77 | Legacy tries to execute `set` as an external program. Fixed applies `AWS_DEFAULT_REGION` to pytest. The same seven unrelated reference-suite failures remain in both modes. |

## What the run establishes

1. All seven tasks have a real command-execution defect under the pinned evaluator, not merely a theoretical quoting concern.
2. The defect can be score-changing: the reference A/B changes `asteval` from 0/227 to 227/227 and `arxiv-mcp-server` from 0/23 to 18/23.
3. A malformed setup command does not guarantee a score delta for every workspace. Importing directly from `/workspace`, pre-existing files, or unrelated image failures can mask the defect.
4. Two additional benchmark-data issues were observed: `boto:1.0` lacks a runnable `pytest`, and `parse/test_case_count.txt` says 96 while the supplied suite reports 98 passed.

Raw argv, stdout, stderr, timings, file hashes, image identities, and cleanup status are stored in the per-mode JSON files in this directory.
