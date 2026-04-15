# Okteto Plugins for AI Agents

Teaches AI agents how to work with [Okteto](https://www.okteto.com) development environments. Works with any project that has an `okteto.yaml`.

Includes integrations for both **Claude Code** and **GitHub Copilot**.

## GitHub Copilot (VS Code)

Copy [`copilot/copilot-instructions.md`](copilot/copilot-instructions.md) into your repo as `.github/copilot-instructions.md`:

```
cp copilot/copilot-instructions.md <your-repo>/.github/copilot-instructions.md
```

GitHub Copilot reads this file automatically in VS Code agent mode. It teaches Copilot:

- How to discover services from `okteto.yaml`
- To use `okteto exec -- <command>` to run tests and diagnostics in the dev container (not `kubectl exec`)
- That `okteto up` is interactive and must be run by the developer in their terminal
- When to rebuild images with `okteto build` vs when file sync handles it

No other setup required. Works with any project that has an `okteto.yaml`.

---

## Claude Code

### Install

Add the Okteto marketplace and install the plugin:

```
/plugin marketplace add okteto/okteto-claude-plugins
/plugin install okteto
```

### What's included

- **Okteto skill** -- CLI knowledge, collaborative and autonomous workflow patterns, debugging strategies
- **`/dev-setup` command** -- One-command environment setup: checks prerequisites, deploys services, shows endpoints, guides the developer into a dev container

### Usage

#### Skill (automatic)

The Okteto skill activates automatically when a project has an `okteto.yaml`. It teaches the agent:

- How to discover services from `okteto.yaml` (no hardcoded config needed)
- When to use `okteto deploy`, `okteto build`, `okteto test`, `okteto exec`, and `okteto logs`
- That `okteto up` is interactive and must be run by the developer, never the agent
- How to operate in **collaborative mode** (developer in the loop) vs **autonomous mode** (ticket-driven, no human)

#### `/dev-setup` command

Run `/dev-setup` to have the agent walk through full environment setup:

1. Reads `okteto.yaml` to discover services
2. Checks CLI prerequisites (`okteto version`, `okteto context show`)
3. Deploys all services (`okteto deploy --wait`)
4. Shows live endpoints (`okteto endpoints`)
5. Guides you to start developing a specific service

#### Autonomous mode

For CI/CD or ticket-driven workflows where no developer is present, the skill teaches agents to:

1. Deploy a full environment with `okteto deploy --wait`
2. Make code changes based on ticket requirements
3. Rebuild and redeploy changed services with `okteto build` + `okteto deploy`
4. Validate with `okteto test` and endpoint smoke tests
5. Report results back to the ticket/PR

### Testing locally

```
claude --plugin-dir /path/to/okteto-claude-plugins/plugins/okteto
```

### Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- [Okteto CLI](https://www.okteto.com/docs/get-started/install-okteto-cli/) installed and configured
- An `okteto.yaml` in your project root
