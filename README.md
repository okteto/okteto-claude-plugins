# Okteto Plugins for AI Agents

Teaches AI agents how to work with [Okteto](https://www.okteto.com) development environments. Works with any project that has an `okteto.yaml`.

Built on the open [Agent Skills](https://agentskills.io) format, so the same skills run in **Claude Code**, **Cursor**, **OpenAI Codex**, **GitHub Copilot**, **Gemini CLI**, and [many more](https://agentskills.io/clients).

## Install

Pick the row for your agent. Every method teaches the agent the same Okteto workflows — they differ only in packaging.

| Your agent | Install | You get |
|---|---|---|
| **Claude Code** | `/plugin marketplace add okteto/okteto-claude-plugins` → `/plugin install okteto` | Both skills **+ the `/dev-setup` command** |
| **Cursor, Codex, Copilot, Gemini CLI, [& more](https://agentskills.io/clients)** | `npx skills add okteto/okteto-claude-plugins` | Both skills, installed into your agent |
| **Anything that reads `AGENTS.md`** | `cp agents/AGENTS.md <your-repo>/AGENTS.md` | One always-on instruction file |
| **GitHub Copilot (file-based)** | `cp copilot/copilot-instructions.md <your-repo>/.github/copilot-instructions.md` | One always-on instruction file |

Requires the [Okteto CLI](https://www.okteto.com/docs/get-started/install-okteto-cli/) installed and configured, and an `okteto.yaml` in your project.

### Claude Code (native plugin)

Run these two commands inside Claude Code:

```
/plugin marketplace add okteto/okteto-claude-plugins
/plugin install okteto
```

- `/plugin marketplace add okteto/okteto-claude-plugins` — tells Claude Code to trust this GitHub repo as a source of plugins. One-time registration.
- `/plugin install okteto` — installs the `okteto` plugin, wiring up its skills **and** the `/dev-setup` slash command.

After install, open any project with an `okteto.yaml` and ask Claude for help. The skill activates automatically; `/dev-setup` is available whenever you want a guided environment bring-up. This is the only method that includes the `/dev-setup` command.

### Cursor, Codex, and other skills-compatible agents (`npx skills`)

The [`skills`](https://github.com/vercel-labs/skills) CLI installs the skills into whichever agent you run it from — no Okteto-specific config required:

```
npx skills add okteto/okteto-claude-plugins
```

It auto-detects your agent (Cursor, Codex, Copilot, Gemini CLI, and [others](https://agentskills.io/clients)) and prompts you to pick skills. Useful flags:

- `--skill '*' -y` — install both skills into the detected agent without prompting
- `--copy` — copy the skill files in instead of symlinking them
- `npx skills use okteto/okteto-claude-plugins@okteto` — print a skill as a one-off prompt without installing it

Avoid `--all` — it installs into *every* known agent's directory, not just yours.

This carries the **skills only** — the `/dev-setup` slash command is exclusive to the Claude Code plugin above.

### File-based fallback (`AGENTS.md` / Copilot)

If your agent reads a plain instruction file, copy one in — zero dependency on any installer:

```
cp agents/AGENTS.md <your-repo>/AGENTS.md                                  # AGENTS.md-aware agents
cp copilot/copilot-instructions.md <your-repo>/.github/copilot-instructions.md   # GitHub Copilot
```

Both files carry the same tool-neutral Okteto guidance: discovering services from `okteto.yaml`, using `okteto exec` (not `kubectl exec`), treating `okteto up` as developer-only, when to `okteto build` vs. rely on sync, and isolating worktrees with `-n <ns>`. **Cursor** users can alternatively drop the same content at `.cursor/rules/okteto.mdc` for native rule scoping. Unlike the skills methods, these load the full instructions on every turn rather than on demand.

## What's included

- **`okteto` skill** -- CLI knowledge, collaborative and autonomous workflow patterns, debugging strategies
- **`okteto-onboarding` skill** -- Bootstraps projects that have no `okteto.yaml` yet: discovers services, drafts a manifest, validates it, then hands off to the `okteto` skill
- **`/dev-setup` command** -- One-command environment setup: checks prerequisites, deploys services, shows endpoints, guides the developer into a dev container

## Usage

### Skill (automatic)

The Okteto skill activates automatically when a project has an `okteto.yaml`. It teaches the agent:

- How to discover services from `okteto.yaml` (no hardcoded config needed)
- When to use `okteto deploy`, `okteto build`, `okteto test`, `okteto exec`, and `okteto logs`
- That `okteto up` is interactive and must be run by the developer, never the agent
- How to operate in **collaborative mode** (developer in the loop) vs **autonomous mode** (ticket-driven, no human)
- How to isolate **git worktrees**: one namespace per worktree (`okteto namespace create` + `-n <ns>` on every command) so parallel branches never overwrite each other's environments
- How to tear environments down cleanly with `okteto destroy` and when it is (and isn't) safe for an agent to do so unprompted

### `okteto-onboarding` skill (automatic)

The `okteto-onboarding` skill activates when a repo has no `okteto.yaml` and the user wants to get the project onto Okteto. It:

- Discovers services from `docker-compose.yml`, Helm charts, Kubernetes manifests, or Dockerfiles
- Drafts an `okteto.yaml` based on what it finds
- Validates the manifest through a tiered ladder: `okteto validate` → `okteto build` → `okteto deploy --wait`
- Hands off to the `okteto` skill once the manifest exists

Once the `okteto.yaml` is in place, normal `okteto` skill workflows (collaborative mode, autonomous mode, `/dev-setup`) take over.

### Cleanup and teardown

The skill covers the end of the lifecycle as well as the start. It teaches the agent:

- To run `okteto destroy` to tear down all resources created by `okteto deploy`
- To use `okteto down` (not `okteto destroy`) to exit dev mode without destroying the environment
- To treat `okteto destroy` as a destructive action: in **collaborative mode** it asks the developer to run it; in **autonomous mode** it only runs when there is an explicit cleanup policy or authorization (e.g., an ephemeral PR environment that the pipeline owns)
- To leave shared namespaces alone unless the task explicitly scopes cleanup to a namespace the agent owns
- That a namespace it created itself for an isolated worktree *is* the agent's to delete (`okteto destroy -n <ns>` then `okteto namespace delete <ns>`)

If your team wants different defaults (for example, always destroy on autonomous run success), document that in your repo's `CLAUDE.md` and the skill will pick it up.

### `/dev-setup` command (Claude Code only)

Run `/dev-setup` to have the agent walk through full environment setup:

1. Reads `okteto.yaml` to discover services
2. Checks CLI prerequisites (`okteto version`, `okteto context show`)
3. Deploys all services (`okteto deploy --wait`)
4. Shows live endpoints (`okteto endpoints`)
5. Guides you to start developing a specific service

### Autonomous mode

For CI/CD or ticket-driven workflows where no developer is present, the skill teaches agents to:

1. Deploy a full environment with `okteto deploy --wait`
2. Make code changes based on ticket requirements
3. Rebuild and redeploy changed services with `okteto build` + `okteto deploy`
4. Validate with `okteto test` and endpoint smoke tests
5. Report results back to the ticket/PR

## Testing the plugin locally

```
claude --plugin-dir /path/to/okteto-claude-plugins/plugins/okteto
```

## Requirements

- [Okteto CLI](https://www.okteto.com/docs/get-started/install-okteto-cli/) installed and configured
- An `okteto.yaml` in your project root (use the `okteto-onboarding` skill if you don't have one yet)
- A skills-compatible agent — see the [Install](#install) table
