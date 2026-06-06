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
- To isolate git worktrees with a namespace per worktree (`-n <ns>`)

No other setup required. Works with any project that has an `okteto.yaml`.

---

## Claude Code

### Install

Run these two commands inside Claude Code:

```
/plugin marketplace add okteto/okteto-claude-plugins
/plugin install okteto
```

What each command does:

- `/plugin marketplace add okteto/okteto-claude-plugins` — tells Claude Code "trust this GitHub repo as a source of plugins." Claude Code reads `marketplace.json` from it. One-time registration.
- `/plugin install okteto` — says "from the marketplaces I know about, install the plugin named `okteto`." Claude Code pulls the `plugins/okteto/` folder locally and wires up its skills and commands.

After install, open any project with an `okteto.yaml` and ask Claude for help. The skill activates automatically; `/dev-setup` is available as a slash command whenever you want a guided environment bring-up.

### What's included

- **`okteto` skill** -- CLI knowledge, collaborative and autonomous workflow patterns, debugging strategies
- **`okteto-onboarding` skill** -- Bootstraps projects that have no `okteto.yaml` yet: discovers services, drafts a manifest, validates it, then hands off to the `okteto` skill
- **`/dev-setup` command** -- One-command environment setup: checks prerequisites, deploys services, shows endpoints, guides the developer into a dev container

### Usage

#### Skill (automatic)

The Okteto skill activates automatically when a project has an `okteto.yaml`. It teaches the agent:

- How to discover services from `okteto.yaml` (no hardcoded config needed)
- When to use `okteto deploy`, `okteto build`, `okteto test`, `okteto exec`, and `okteto logs`
- That `okteto up` is interactive and must be run by the developer, never the agent
- How to operate in **collaborative mode** (developer in the loop) vs **autonomous mode** (ticket-driven, no human)
- How to isolate **git worktrees**: one namespace per worktree (`okteto namespace create` + `-n <ns>` on every command) so parallel branches never overwrite each other's environments
- How to tear environments down cleanly with `okteto destroy` and when it is (and isn't) safe for an agent to do so unprompted

#### `okteto-onboarding` skill (automatic)

The `okteto-onboarding` skill activates when a repo has no `okteto.yaml` and the user wants to get the project onto Okteto. It:

- Discovers services from `docker-compose.yml`, Helm charts, Kubernetes manifests, or Dockerfiles
- Drafts an `okteto.yaml` based on what it finds
- Validates the manifest through a tiered ladder: `okteto validate` → `okteto build` → `okteto deploy --wait`
- Hands off to the `okteto` skill once the manifest exists

Once the `okteto.yaml` is in place, normal `okteto` skill workflows (collaborative mode, autonomous mode, `/dev-setup`) take over.

#### Cleanup and teardown

The skill covers the end of the lifecycle as well as the start. It teaches the agent:

- To run `okteto destroy` to tear down all resources created by `okteto deploy`
- To use `okteto down` (not `okteto destroy`) to exit dev mode without destroying the environment
- To treat `okteto destroy` as a destructive action: in **collaborative mode** it asks the developer to run it; in **autonomous mode** it only runs when there is an explicit cleanup policy or authorization (e.g., an ephemeral PR environment that the pipeline owns)
- To leave shared namespaces alone unless the task explicitly scopes cleanup to a namespace the agent owns
- That a namespace it created itself for an isolated worktree *is* the agent's to delete (`okteto destroy -n <ns>` then `okteto namespace delete <ns>`)

If your team wants different defaults (for example, always destroy on autonomous run success), document that in your repo's `CLAUDE.md` and the skill will pick it up.

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
