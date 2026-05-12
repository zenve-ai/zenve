# zenve-adapters

Base types and registry for Zenve agent adapters.

An adapter is the subprocess wrapper that actually runs an agent — Claude Code, opencode, or any other agent runtime. The adapter receives a `RunContext` (agent dir, run id, message, tools, env, event callback) and returns a `RunResult`.

This package is a dependency of [`zenve-engine`](https://pypi.org/project/zenve-engine/) and [`zenve-cli`](https://pypi.org/project/zenve-cli/). You normally don't install it directly.

See the [Zenve repository](https://github.com/zenve-ai/zenve) for documentation.

## License

MIT
