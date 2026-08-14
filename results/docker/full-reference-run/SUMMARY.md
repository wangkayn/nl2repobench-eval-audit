# Real-image legacy/fixed A/B summary

Official source pin: `781a1da1ee41fb8edb0bed22f586d69111610edf`

Workspace input: upstream reference source overlay; official sanitization applied.

This proves evaluator-path effects,
but is not a model rescore because no generated model workspace was available locally.

| Task | Mode | Command exits | Passed / denominator | Rate |
|---|---:|---:|---:|---:|
| arxiv-mcp-server | legacy | 1, 1 | 0 / 23 | 0.0000 |
| arxiv-mcp-server | fixed | 0, 1 | 18 / 23 | 0.7826 |
| asteval | legacy | 0, 0, 1 | 0 / 227 | 0.0000 |
| asteval | fixed | 0, 0, 0 | 227 / 227 | 1.0000 |
| boto | legacy | 0, 0, 127 | 0 / 1014 | 0.0000 |
| boto | fixed | 0, 0, 127 | 0 / 1014 | 0.0000 |
| jinja | legacy | 0, 0, 0, 0 | 911 / 911 | 1.0000 |
| jinja | fixed | 0, 0, 0, 0 | 911 / 911 | 1.0000 |
| parse | legacy | 1, 0 | 98 / 96 | 1.0000 |
| parse | fixed | 0, 0 | 98 / 96 | 1.0000 |
| tqdm | legacy | 0, 127, 1 | 133 / 139 | 0.9568 |
| tqdm | fixed | 0, 0, 1 | 133 / 139 | 0.9568 |
| binaryalert | legacy | 127, 1 | 70 / 77 | 0.9091 |
| binaryalert | fixed | 1 | 70 / 77 | 0.9091 |
