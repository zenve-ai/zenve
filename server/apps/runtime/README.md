# zenve-runtime

Local FastAPI daemon (port 8001) that owns Zenve workspaces, runs, and the scheduler. The [`zenve` CLI](https://pypi.org/project/zenve-cli/) auto-starts this daemon and talks to it over HTTP.

You normally don't install this directly — `pip install zenve-cli` or `uv tool install zenve-cli` pulls it in.

## Run standalone

```bash
runtime-start
curl localhost:8001/healthz
```

See the [Zenve repository](https://github.com/zenve-ai/zenve) for the full design.

## License

MIT
