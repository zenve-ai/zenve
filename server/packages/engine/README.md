# zenve-engine

Run executor for Zenve. Discovers agents in a `.zenve/` repo, snapshots GitHub state, runs all agents in parallel via the adapter registry, and commits results back.

This package is a dependency of [`zenve-cli`](https://pypi.org/project/zenve-cli/) and [`zenve-runtime`](https://pypi.org/project/zenve-runtime/). You normally don't install it directly.

## Public API

```python
from zenve_engine import run, snapshot, RunReport, Snapshot

report = run(
    project_dir=Path("/path/to/repo"),
    run_id="run_abc123",
    github_token=token,
    repo="org/name",
)
```

See the [Zenve repository](https://github.com/zenve-ai/zenve) for the full design.

## License

MIT
