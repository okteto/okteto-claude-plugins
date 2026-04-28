# Design: `okteto-onboarding` Skill

**Date:** 2026-04-28
**Status:** Approved (pending implementation plan)
**Owner:** Cody / Okteto

## Problem

The existing `okteto` skill (in `okteto-claude-plugins`) assumes the repo already has an `okteto.yaml`. Repos that don't have one need a separate, focused workflow to produce a valid manifest and confirm it works. There is no `okteto init` command — manifest creation is fully manual today, which is the highest-friction step for adopting Okteto.

This skill closes that gap: it discovers what the repo already looks like, drafts an `okteto.yaml` with the user's input, and walks a tiered validation ladder so the user finishes with confidence the manifest is correct.

## Audience

Public skill, single source of truth for both Okteto customers and Solutions Engineers. SEs use the same skill when working with a customer — keeps the experience identical and demonstrates value transparently.

## Non-goals

- Generating Helm charts or k8s manifests from scratch. If the repo has neither, Level 2/3 deploy onboarding is unavailable; we recommend Level 1 (dev-only).
- Modifying Dockerfiles or source code. The skill writes only `okteto.yaml` (plus a branch + PR in autonomous mode).
- Picking the user's Okteto context or namespace. We use whatever `okteto context show` returns; we never call `okteto context use`.
- Running `okteto destroy`. Cleanup is the user's call (matches the existing `okteto` skill).
- Re-onboarding or migrating existing manifests. If `okteto.yaml` already exists, the skill exits and points at the existing `okteto` skill.
- Sample-template scaffolding. No matching against `okteto/samples/` — those are demos, not real-world fits.

## Skill identity & placement

**Name:** `okteto-onboarding`

**Distribution:** sibling skill in the existing `okteto-claude-plugins` plugin. Single `/plugin install okteto` brings both skills. Public-only — there is no internal overlay.

```
okteto-claude-plugins/plugins/okteto/
├── .claude-plugin/plugin.json   (updated to declare both skills)
├── skills/
│   ├── okteto/SKILL.md          (existing — usage skill)
│   └── onboarding/SKILL.md      (new — this skill)
└── commands/
    └── dev-setup.md             (updated: suggest onboarding when no manifest is present)
```

The skill is a single `SKILL.md`, consistent with the existing `okteto` skill. Reference snippets (the `dev:` vs `deploy:` framing, the docker-compose mapping table, the base-image lookup) live inline in the skill body, not as separate files.

**Trigger conditions** (encoded in the skill description so it self-activates):

- The repo has **no `okteto.yaml` or `okteto.yml`** AND the user mentions Okteto, dev environments, or onboarding.
- The user invokes the skill explicitly or asks "how do I get this repo onto Okteto."
- **Not triggered** when an `okteto.yaml` already exists — that is the existing `okteto` skill's domain.

## High-level workflow

The skill walks through six phases. Phases 1–5 are identical in collaborative and autonomous modes; phase 6 differs.

### Phase 1: Discover

Scan the repo and build an internal model of services, ports, build contexts, and likely dev commands. Signals are read in priority order:

1. **`docker-compose.yml` / `compose.yaml`** — primary blueprint when present. Mapping:

   | Compose | Okteto manifest |
   |---|---|
   | `services.<name>` | `build.<name>` and (Level 2+) `deploy:` entry |
   | `build.context`, `build.dockerfile` | `build.<name>.context`, `build.<name>.dockerfile` |
   | `ports` | exposed ports on the deploy |
   | `command` | starting point for `dev.<name>.command` |
   | `volumes` (host bind mounts) | `dev.<name>.sync` candidates |
   | `depends_on` | ordering hint for deploy |
   | `environment` | carried into `dev.<name>.environment` |

2. **Existing Helm chart** — any `Chart.yaml` under `chart/`, `charts/`, `helm/`, `deploy/`. `deploy:` becomes `helm upgrade --install` against it. The skill does not generate or modify the chart.

3. **Existing k8s manifests** — `k8s/`, `manifests/`, `deploy/*.yaml` with `kind:` headers. `deploy:` becomes `kubectl apply -f ...`. The skill does not author these manifests.

4. **Per-service Dockerfiles** — for repos without compose, each top-level `Dockerfile` is a candidate service. Service name is inferred from the parent directory.

5. **Language manifests** — `package.json`, `go.mod`, `pom.xml`, `pyproject.toml`, `Gemfile`, `Cargo.toml` — used to pick the dev image (e.g., `okteto/golang:1.22`, `okteto/node:20`) and infer the dev command (`npm run dev`, `go run .`, `mvn spring-boot:run`).

6. **Procfile / Makefile** — secondary signals when language manifests are ambiguous.

When discovery is ambiguous (multiple services, no compose, no chart), the skill asks targeted questions rather than guessing — e.g., "I see Dockerfiles in `api/` and `web/` but no compose file. Should both be services? Which one do you typically run in dev mode?"

### Phase 2: Negotiate scope

Before asking the user how far to go, the skill emits a short framing block — both spoken to the user and written as a header comment in the manifest:

> *In Okteto, `deploy:` describes how to **provision** the environment (services, images, helm charts, k8s manifests). `dev:` describes how to **live-edit** a running service — file sync, the dev image, the startup command. You can use Okteto with just `dev:` if you already have a way to deploy your stack, or have Okteto handle both.*

The skill then proposes a level on the adaptive ladder, picking the most natural fit from discovery:

- **Level 1 — dev-only.** User already has `deploy:` covered (existing chart or external infra); we just give them sync. Smallest manifest.
- **Level 2 — deploy + dev.** User wants `okteto deploy` to bring up the stack. Requires a chart or k8s manifests in the repo (see non-goals).
- **Level 3 — full lifecycle.** Adds `test:` containers wired to the existing test commands (`go test ./...`, `npm test`, `mvn test`, etc.).

The skill recommends a level based on what was found (e.g., "I see a Helm chart at `chart/` — Level 2 is the natural fit") and lets the user pick. The chosen level is locked at the start of phase 3, not negotiated mid-flight.

### Phase 3: Draft

Write `okteto.yaml` to the repo. The user sees the actual file, not just a summary. Comments inline explain non-obvious choices (e.g., why a particular sync path was chosen, why a particular base image). The framing block from phase 2 lives at the top of the file.

The draft is a pure function of (discovered model + chosen level + user answers). No template matching against `okteto/samples/`.

### Phase 4: Refine

Iterate on the draft based on user feedback. Common edits:

- Change dev image (e.g., user wants a specific Go or Node version).
- Adjust sync paths (exclude `node_modules`, `vendor`, `target`, `.git`).
- Add an environment variable or secret reference.
- Swap the deploy command (e.g., use a specific helm values file).

### Phase 5: Validate (tiered)

The skill always runs Tier 1 and offers each higher tier with a clear cost/benefit before climbing.

**Tier 1 — Always: `okteto validate`**
- Catches: YAML syntax, schema violations, missing required fields.
- Cost: subsecond, no cluster needed, no auth needed.
- Floor — the skill does not finish without this passing.

**Tier 2 — Offered if Dockerfiles or `build:` entries exist: `okteto build`**
- Catches: bad build contexts, broken Dockerfile references, missing files in the build context, image push permissions.
- Cost: minutes per service, requires `okteto context show` to return a context.
- Default: build all services. If the user has many services, the skill offers narrowing to one.
- Prompt: *"I can run `okteto build` to prove every Dockerfile resolves and pushes. This takes a few minutes per service. Skip / build one service / build all?"*

**Tier 3 — Offered if Tier 2 passed (or skipped) AND user has a context: `okteto deploy --wait` + `okteto endpoints`**
- Catches: bad Helm references, missing values, broken `kubectl apply`, services that crash on startup, missing endpoints.
- Cost: longer (full deploy), creates real cluster resources.
- Note: there is no `okteto deploy --dry-run` — full deploy is the only option above Tier 2.
- Prompt: *"I can do a full deploy to verify the manifest works end-to-end. This will create resources in your namespace `<ns>`. After it succeeds, I'll show you the endpoints. You can `okteto destroy` after if you want. Proceed?"*
- On success: prints endpoints and stops. The skill does **not** run `okteto destroy` automatically.

**On failure at any tier:**
1. Surface the raw CLI error verbatim — do not paraphrase.
2. Diagnose the likely cause based on the manifest section involved.
3. Propose a concrete edit to the manifest.
4. After the user approves the fix, re-run only the failing tier (not the whole ladder).

**Skipped tiers due to environment** (no `okteto context show`): the skill notes which tiers were skipped in the final summary, so the user knows the manifest is "syntactically valid but not deploy-tested" rather than "verified end-to-end."

### Phase 6: Handoff (collaborative) or PR (autonomous)

**Collaborative mode:** point the user at the existing `okteto` skill and `/dev-setup` for next steps. State which validation tiers passed and which were skipped.

**Autonomous mode:** open a PR with the manifest. The PR is the human review gate; the skill never merges.

- Branch: `okteto/onboarding`
- PR title: `Add Okteto manifest`
- PR body: discovered services + chosen scope level + validation results + a checklist of decisions the human reviewer should sanity-check (e.g., *"I picked `okteto/golang:1.22` — confirm this matches your Go version"*).

## Operating modes

**Collaborative (default).** Each phase asks the user when the choice is non-obvious. The skill never makes a decision the user cannot see.

**Autonomous (opt-in).** Used when the skill is operating without a human in the loop — e.g., invoked from a ticket-driven session, a CI pipeline, or any context where no developer is expected to intervene. The agent infers this from context the same way the existing `okteto` skill does (no mechanical trigger). Behavior:

1. Phases 1–5 run identically, but every "ask the user" branch resolves with a documented default:
   - Scope level → highest level the discovery *supports*. Level 2 requires a chart or k8s manifests; Level 3 additionally requires detected tests. With no chart and no manifests, the skill stays at Level 1 even if tests are present.
   - Validation tier → Tier 1 always; Tier 2 if `okteto context show` succeeds; Tier 3 only if the trigger explicitly authorizes a deploy (label, env var, or explicit instruction).
   - Discovery ambiguities → most conservative interpretation, noted in the PR description.
2. Phase 6 opens a PR rather than handing off.

## Interface with the existing `okteto` skill

The two skills are complementary:

- **`okteto-onboarding`** runs when there is no manifest. It produces one and exits.
- **`okteto`** runs when there is a manifest. It uses it to deploy, develop, test.

After onboarding succeeds, the existing `okteto` skill takes over for `okteto deploy`, `okteto up`, `okteto test`. The `/dev-setup` slash command is updated to detect a missing manifest and suggest invoking `okteto-onboarding` first.

## Risks & open questions

- **Helm chart authorship boundary.** A meaningful share of repos have neither compose nor a chart. Those users can only reach Level 1, which may feel anticlimactic. We accept this trade-off because authoring Helm charts is a separate skill problem (and a much harder one).
- **Base-image selection.** Picking the wrong `okteto/<lang>:<version>` is a common Tier 1-passing-but-Tier-2-failing case. The PR review checklist (autonomous mode) and the inline manifest comments (collaborative mode) are how we mitigate this. We may want to revisit if it shows up as a frequent failure.
- **Repos with non-trivial monorepos.** The discovery rules assume one Dockerfile per service. Multi-stage builds, shared base images, and bazel-style monorepos are not handled specifically; the skill will ask targeted questions in those cases.

## Success criteria

- A new repo with a `docker-compose.yml` and a Dockerfile produces a passing `okteto validate` and a working `okteto up <service>` flow without the user editing the manifest by hand.
- A new repo with a Helm chart and Dockerfiles produces a passing `okteto deploy --wait` end-to-end (Tier 3) at the user's discretion.
- A new repo with neither chart nor compose can still produce a Level 1 manifest that lets the user run `okteto up` against an externally-managed deploy.
- An autonomous run on a typical repo produces a reviewable PR that a human can approve in under five minutes.
