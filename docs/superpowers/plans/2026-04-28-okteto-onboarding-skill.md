# okteto-onboarding Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a new `okteto-onboarding` skill in the `okteto-claude-plugins` plugin that takes a repo with no `okteto.yaml` and produces a valid one through discovery, drafting, and a tiered validation ladder.

**Architecture:** A single `SKILL.md` sibling to the existing `okteto` skill in `plugins/okteto/skills/onboarding/`. Skills are auto-discovered (no `plugin.json` change). The slash command `dev-setup` is updated to suggest the new skill when no manifest is present. Behavior is validated by invoking the skill against fixture repos with different shapes.

**Tech Stack:** Markdown (SKILL.md), the Okteto CLI (`okteto validate`, `okteto build`, `okteto deploy`), `git` for branch/commit/PR. No new code — this is a prompt-engineering / documentation deliverable.

**Spec:** `docs/superpowers/specs/2026-04-28-okteto-onboarding-skill-design.md`

**Branch:** `feat/onboarding-skill-design` (already created, spec already committed at `4ab89c6`)

---

## Notes for the executing engineer

You may not have done much skill authoring before. Two things that will surprise you:

1. **A skill is just a markdown file with YAML frontmatter.** The frontmatter `name` and `description` are how the skill surfaces in the plugin and how Claude decides whether to invoke it. The body is the prompt that's loaded when invoked. There are no "tests" in the unit-test sense — validation is behavioral: invoke the skill against a sample input and check the output.
2. **Skill content is read by Claude, not parsed.** That means the writing matters. Be concrete, give Claude decision rules and examples, and assume Claude will follow exactly what's written.

For testing in Phase C: the cleanest way to test a skill is to dispatch a subagent (using the `Agent` tool with `subagent_type: "general-purpose"`) in a fresh context, point it at a fixture directory, and feed it the new SKILL.md content as system context. Then inspect what it produced. Examples are in the test tasks.

If at any point a step contradicts the spec, stop and ask. Do not improvise.

---

## File Structure

Files this plan creates or modifies (relative to `okteto-claude-plugins/` repo root):

| Path | Action | Purpose |
|---|---|---|
| `plugins/okteto/skills/onboarding/SKILL.md` | Create | The new skill (the entire deliverable) |
| `plugins/okteto/commands/dev-setup.md` | Modify | Add a branch for missing-manifest case |
| `README.md` | Modify | Mention the new skill in the plugin index |
| `tests/fixtures/compose-only/` | Create | Behavioral test fixture |
| `tests/fixtures/chart-and-dockerfiles/` | Create | Behavioral test fixture |
| `tests/fixtures/bare/` | Create | Behavioral test fixture |

`plugin.json` and `marketplace.json` are NOT modified — skills are auto-discovered from the `skills/` directory.

---

## Phase A: Author the skill file

The skill file is one document but written in sections so each commit is a coherent slice.

### Task 1: Scaffold the skill directory and frontmatter

**Files:**
- Create: `plugins/okteto/skills/onboarding/SKILL.md`

- [ ] **Step 1: Create the directory and skeleton file**

```bash
mkdir -p plugins/okteto/skills/onboarding
```

Create `plugins/okteto/skills/onboarding/SKILL.md` with this initial content:

```markdown
---
name: okteto-onboarding
description: |
  Onboards a new repo onto Okteto. Use when a project has NO okteto.yaml/okteto.yml
  and the user mentions Okteto, dev environments, or onboarding. Discovers services
  from docker-compose, Helm charts, k8s manifests, or Dockerfiles; drafts an
  okteto.yaml; and validates it through a tiered ladder (validate → build → deploy).
  Hands off to the existing `okteto` skill once the manifest exists. Do NOT trigger
  if okteto.yaml already exists.
---

# Okteto Onboarding Skill

(skeleton — sections filled in by subsequent tasks)

## 1. Activation
## 2. Phase 1 — Discover
## 3. Phase 2 — Negotiate scope
## 4. Phases 3–4 — Draft and refine
## 5. Phase 5 — Validate (tiered)
## 6. Phase 6 — Handoff or PR
## 7. Operating modes
## 8. CLI quick reference
## 9. Common mistakes to avoid
```

- [ ] **Step 2: Verify the frontmatter structure matches the existing skill**

Run: `head -10 plugins/okteto/skills/okteto/SKILL.md`
Expected: frontmatter starts with `---`, has `name:` and `description:` fields. Confirm the new skill uses the same structure.

- [ ] **Step 3: Commit**

```bash
git add plugins/okteto/skills/onboarding/SKILL.md
git commit -m "Scaffold okteto-onboarding skill"
```

---

### Task 2: Write Section 1 — Activation

**Files:**
- Modify: `plugins/okteto/skills/onboarding/SKILL.md`

- [ ] **Step 1: Replace the Section 1 placeholder with this content**

Replace `## 1. Activation` (and the empty space after it) with:

````markdown
## 1. Activation

This skill activates when **all** of the following are true:
- The project has **no** `okteto.yaml` or `okteto.yml` at the repo root
- The user is asking about Okteto, dev environments, or onboarding (e.g., "how do I get this onto Okteto", "set this repo up for Okteto", "create an Okteto manifest")

**Do NOT activate if:**
- An `okteto.yaml` or `okteto.yml` already exists at the repo root — that is the existing `okteto` skill's domain. Defer to it.
- The user is asking how to *use* Okteto with an existing manifest. Defer to the existing `okteto` skill.

**Pre-flight check.** Before starting Phase 1, run:

```bash
ls okteto.yaml okteto.yml 2>/dev/null
```

If anything is returned, stop and tell the user:
> "I see `okteto.yaml` already exists. The `okteto-onboarding` skill is for repos *without* a manifest. For working with the existing manifest, use the `okteto` skill or run `/dev-setup`."

**Two operating modes:** collaborative (default — user is in the loop) and autonomous (no human; opens a PR). See Section 7. Most of the workflow is mode-agnostic; only Phase 6 and the resolution of "ask the user" branches differ.
````

- [ ] **Step 2: Verify the file still parses as valid YAML frontmatter + markdown**

Run: `head -15 plugins/okteto/skills/onboarding/SKILL.md`
Expected: frontmatter intact, Section 1 follows.

- [ ] **Step 3: Commit**

```bash
git add plugins/okteto/skills/onboarding/SKILL.md
git commit -m "Add activation section to onboarding skill"
```

---

### Task 3: Write Section 2 — Phase 1 (Discover)

**Files:**
- Modify: `plugins/okteto/skills/onboarding/SKILL.md`

- [ ] **Step 1: Replace `## 2. Phase 1 — Discover` with this content**

````markdown
## 2. Phase 1 — Discover

Build an internal model of the repo: services, their build contexts, ports, dev commands, and any existing deploy artifacts. Read signals in priority order. **Do not write the manifest yet.**

### 2.1 Signal priority

1. **`docker-compose.yml` / `compose.yaml`** — the richest signal. If present, it is the primary blueprint. See the mapping table below.
2. **Existing Helm chart** — any `Chart.yaml` under `chart/`, `charts/`, `helm/`, or `deploy/`. If found, `deploy:` will be a `helm upgrade --install` command. **Do not generate or modify the chart.**
3. **Existing k8s manifests** — `.yaml` files with `kind:` headers under `k8s/`, `manifests/`, `deploy/`. If found, `deploy:` will be `kubectl apply -f ...`. **Do not author these manifests.**
4. **Per-service Dockerfiles** — for repos without compose, each top-level `Dockerfile` is a candidate service. Service name comes from the parent directory.
5. **Language manifests** — `package.json`, `go.mod`, `pom.xml`, `pyproject.toml`, `Gemfile`, `Cargo.toml`. Used to pick the dev image and infer the dev command.
6. **Procfile / Makefile** — secondary signals when language manifests are ambiguous.

### 2.2 Compose → Okteto mapping

When `docker-compose.yml` is present, map fields like this:

| Compose field | Okteto manifest field |
|---|---|
| `services.<name>` | `build.<name>` and (Level 2+) a `deploy:` step |
| `build.context`, `build.dockerfile` | `build.<name>.context`, `build.<name>.dockerfile` |
| `image` (no `build`) | `build.<name>.image` (skip `context`) |
| `ports` | exposed ports on the deploy |
| `command` | starting point for `dev.<name>.command` |
| `volumes` (host bind mounts only) | `dev.<name>.sync` candidates |
| `depends_on` | ordering hint for the deploy step |
| `environment` | `dev.<name>.environment` |

Ignore compose-only concepts that don't translate (`networks`, `restart`, named volumes, `extends`).

### 2.3 Dev-image picks by language manifest

| Language manifest | Default dev image |
|---|---|
| `package.json` | `okteto/node:20` (read `engines.node` if specified) |
| `go.mod` | `okteto/golang:1.22` (read the `go 1.x` line if specified) |
| `pom.xml` / `build.gradle*` | `okteto/maven:3` or `okteto/gradle:8` |
| `pyproject.toml` / `requirements.txt` | `okteto/python:3.12` |
| `Gemfile` | `okteto/ruby:3.3` |
| `Cargo.toml` | `okteto/rust:1.78` |

If the language manifest specifies a version, prefer the matching Okteto image. State the choice in an inline comment in the manifest (e.g., `# go.mod declares Go 1.22`).

### 2.4 Dev-command picks

| Signal | Dev command default |
|---|---|
| `package.json` with `scripts.dev` | `npm run dev` |
| `package.json` with `scripts.start` (no dev) | `npm start` |
| `go.mod` | `bash` (Go projects usually want a shell to `go run` manually) |
| `pom.xml` with `spring-boot-maven-plugin` | `mvn spring-boot:run` |
| `pyproject.toml` with FastAPI/Flask | `bash` (varies too much to default) |
| Procfile with a `web:` line | the value of `web:` |
| None of the above | `bash` |

### 2.5 When discovery is ambiguous

If discovery leaves real ambiguity, **ask one targeted question at a time** rather than guessing. Examples:

- "I see Dockerfiles in `api/` and `web/` but no compose file. Should both be services?"
- "I found a Helm chart at `chart/` and another at `infra/helm/`. Which one is the canonical deploy?"
- "Your `package.json` doesn't have a `scripts.dev` — what command starts your dev server?"

Do **not** ask the user about everything. Only ask when a guess would be likely wrong. Trust the signals.

### 2.6 Output of Phase 1

Internally, you should now have a model like:

```
Services: [api, web, worker]
api:    Dockerfile @ ./api,    port 8080, dev cmd `bash`,        dev image `okteto/golang:1.22`
web:    Dockerfile @ ./web,    port 3000, dev cmd `npm run dev`, dev image `okteto/node:20`
worker: Dockerfile @ ./worker, no port,   dev cmd `bash`,        dev image `okteto/python:3.12`
Deploy: helm chart at ./chart
Tests: detected `go test ./...` in api, `npm test` in web
```

Show this summary to the user before moving to Phase 2.
````

- [ ] **Step 2: Verify section is in place**

Run: `grep -A 2 "Phase 1" plugins/okteto/skills/onboarding/SKILL.md | head -5`
Expected: section heading present.

- [ ] **Step 3: Commit**

```bash
git add plugins/okteto/skills/onboarding/SKILL.md
git commit -m "Add Phase 1 (discovery) to onboarding skill"
```

---

### Task 4: Write Section 3 — Phase 2 (Negotiate scope)

**Files:**
- Modify: `plugins/okteto/skills/onboarding/SKILL.md`

- [ ] **Step 1: Replace `## 3. Phase 2 — Negotiate scope` with this content**

````markdown
## 3. Phase 2 — Negotiate scope

Before drafting, frame the choice and pick a level on the adaptive ladder.

### 3.1 The framing block (always show this to the user)

> *In Okteto, `deploy:` describes how to **provision** the environment (services, images, helm charts, k8s manifests). `dev:` describes how to **live-edit** a running service — file sync, the dev image, the startup command. You can use Okteto with just `dev:` if you already have a way to deploy your stack, or have Okteto handle both.*

This same framing goes at the top of the generated `okteto.yaml` as a header comment.

### 3.2 The adaptive ladder

| Level | What it produces | Requires |
|---|---|---|
| **1 — dev-only** | `dev:` section only. User runs their own deploy externally. | Nothing extra. |
| **2 — deploy + dev** | `build:` + `deploy:` + `dev:`. `okteto deploy` brings up the stack. | A Helm chart OR k8s manifests in the repo. |
| **3 — full lifecycle** | Adds `test:` containers wired to existing test commands. | Level 2 prereqs PLUS detected tests. |

### 3.3 Recommendation logic

Recommend a level based on what Phase 1 found:

- Helm chart found AND tests detected → recommend **Level 3**
- Helm chart found AND no tests → recommend **Level 2**
- k8s manifests found (no chart) → recommend **Level 2**
- Neither chart nor k8s manifests → recommend **Level 1** (and explain why higher levels are unavailable)

Then ask the user (collaborative mode) or accept the recommendation (autonomous mode):

> "Based on what I found, I'd recommend Level [N]. Want to go with that, pick a different level, or have me explain the trade-offs?"

### 3.4 Locking the level

Once chosen, the level is **locked for the rest of the session.** Do not negotiate level mid-flight. If the draft turns out to need a different level (e.g., the chart is broken), surface that as a Phase 5 failure and re-enter Phase 2 cleanly.
````

- [ ] **Step 2: Commit**

```bash
git add plugins/okteto/skills/onboarding/SKILL.md
git commit -m "Add Phase 2 (negotiate scope) to onboarding skill"
```

---

### Task 5: Write Section 4 — Phases 3–4 (Draft and refine)

**Files:**
- Modify: `plugins/okteto/skills/onboarding/SKILL.md`

- [ ] **Step 1: Replace `## 4. Phases 3–4 — Draft and refine` with this content**

````markdown
## 4. Phases 3–4 — Draft and refine

### 4.1 Draft (Phase 3)

Write `okteto.yaml` to the repo root. The user must see the **actual file**, not just a summary.

**Required content of every draft:**

1. **Header comment block** — the framing from Section 3.1, plus a note that the file was generated by `okteto-onboarding` and the user is expected to edit it.
2. **`build:` section** (Level 2+) — one entry per service with `context` and `dockerfile`.
3. **`deploy:` section** (Level 2+) — `helm` or `kubectl` command pointing at the discovered artifact.
4. **`dev:` section** (always) — one entry per service the user wants in dev mode. Include `image`, `command`, and `sync` (`.:/usr/src/app` is a reasonable default unless compose says otherwise).
5. **`test:` section** (Level 3) — one entry per detected test command.

**Inline comments are required on every non-obvious choice.** Examples:

```yaml
build:
  api:
    context: ./api
    dockerfile: Dockerfile  # using the existing Dockerfile

dev:
  api:
    image: okteto/golang:1.22  # go.mod declares Go 1.22
    command: bash               # Go services usually want a shell to `go run` manually
    sync:
      - .:/usr/src/app          # full-repo sync; tighten this if you have large generated dirs
```

### 4.2 Refine (Phase 4)

Show the file to the user. In collaborative mode, ask:

> "Here's the draft. Want me to change anything before we validate? Common edits: adjust sync paths to exclude `node_modules`/`vendor`/`target`, change the dev image version, add an env var, or swap the deploy command."

Common edit patterns:

| User says | Edit |
|---|---|
| "exclude `node_modules`" | Change `sync` to a list with `!node_modules` ignore patterns or use a more specific path |
| "use Go 1.21 instead" | Update `image:` to `okteto/golang:1.21` |
| "I need this env var" | Add to `dev.<svc>.environment:` |
| "use my values file" | Update `deploy:` helm command with `-f values.staging.yaml` |

**Iteration is cheap — keep editing until the user is satisfied.** Do not move to Phase 5 until they say "looks good" or equivalent.

In autonomous mode, skip the ask and move directly to Phase 5. Edits will be requested via the PR review.
````

- [ ] **Step 2: Commit**

```bash
git add plugins/okteto/skills/onboarding/SKILL.md
git commit -m "Add Phases 3-4 (draft and refine) to onboarding skill"
```

---

### Task 6: Write Section 5 — Phase 5 (Validate)

**Files:**
- Modify: `plugins/okteto/skills/onboarding/SKILL.md`

- [ ] **Step 1: Replace `## 5. Phase 5 — Validate (tiered)` with this content**

````markdown
## 5. Phase 5 — Validate (tiered)

Climb the validation ladder as far as the environment supports. Tier 1 is mandatory; Tiers 2 and 3 are opt-in.

### 5.1 Tier 1 — `okteto validate` (always)

Run:
```bash
okteto validate
```

**What it catches:** YAML syntax, schema violations, missing required fields.
**What it does NOT catch:** wrong sync paths, missing services in `deploy:`, broken Helm refs, images that fail to build.

If it fails, treat as a Phase 4 issue and fix before continuing.

The skill **does not finish without Tier 1 passing.**

### 5.2 Tier 2 — `okteto build` (offered if Dockerfiles or `build:` exist)

Pre-check: run `okteto context show`. If it errors or returns no context, **skip Tier 2** and inform the user:

> "Skipping the build check — no Okteto context. The manifest is syntactically valid but I haven't proven the Dockerfiles build."

Otherwise, ask:

> "I can run `okteto build` to prove every Dockerfile resolves and pushes. This takes a few minutes per service. Skip / build one service / build all?"

Default to **build all**. If the user has many services (≥ 4) and is in a hurry, offer narrowing.

Run:
```bash
okteto build
```
or
```bash
okteto build <service>
```

### 5.3 Tier 3 — `okteto deploy --wait` (offered if Tier 2 passed and user has a context)

Note: there is **no `okteto deploy --dry-run`** flag. Full deploy is the only Tier 3 option.

Ask:

> "I can do a full deploy to verify the manifest works end-to-end. This will create resources in your namespace `<ns>`. After it succeeds, I'll show you the endpoints. You can `okteto destroy` after if you want. Proceed?"

Run:
```bash
okteto deploy --wait
okteto endpoints
```

**On success:** print endpoints. **Do not** run `okteto destroy` automatically — that's the user's call.

### 5.4 On failure at any tier

1. **Surface the raw CLI error verbatim.** Do not paraphrase.
2. **Diagnose the likely cause** based on the manifest section involved (e.g., a Helm error → `deploy:`; a build error → `build:` or the Dockerfile).
3. **Propose a concrete edit to the manifest.** Show the diff, not "you should change X."
4. After the user approves the fix, **re-run only the failing tier** (not the whole ladder).

### 5.5 Final summary

Once the ladder is climbed (or stopped), summarize:

> "✅ `okteto validate` passed
> ✅ `okteto build` passed for all services
> ⏭️ `okteto deploy` skipped (you opted out)
> Next: run `/dev-setup` or invoke the `okteto` skill to deploy and start developing."

If tiers were skipped due to environment (no context), say so:

> "⚠️ Skipped Tiers 2 and 3 (no Okteto context). The manifest is syntactically valid but not deploy-tested."
````

- [ ] **Step 2: Commit**

```bash
git add plugins/okteto/skills/onboarding/SKILL.md
git commit -m "Add Phase 5 (validation ladder) to onboarding skill"
```

---

### Task 7: Write Section 6 — Phase 6 (Handoff or PR)

**Files:**
- Modify: `plugins/okteto/skills/onboarding/SKILL.md`

- [ ] **Step 1: Replace `## 6. Phase 6 — Handoff or PR` with this content**

````markdown
## 6. Phase 6 — Handoff or PR

### 6.1 Collaborative mode: handoff

Point the user at the next step:

> "The manifest is in place. To bring up your environment, you can:
> - Run `/dev-setup` for a guided deploy + dev mode
> - Or invoke the `okteto` skill in any future session — it'll pick up the manifest you just created
>
> If you change the manifest, re-run `okteto validate` (or come back to me)."

State which validation tiers were run and which were skipped (see Section 5.5).

**Do NOT delete the manifest, run `okteto destroy`, or push to a remote.** The work product is the file on disk.

### 6.2 Autonomous mode: PR

Create a branch, commit the manifest, push, and open a PR. The PR is the human review gate.

```bash
git checkout -b okteto/onboarding
git add okteto.yaml
git commit -m "Add Okteto manifest

Generated by okteto-onboarding skill.
Discovered services: <list>
Scope level: <N>
Validation: <tiers passed>"
git push -u origin okteto/onboarding
gh pr create --title "Add Okteto manifest" --body "$(cat <<'EOF'
## Summary
This PR adds an Okteto manifest generated by the `okteto-onboarding` skill.

## Discovered services
<bulleted list of services with their Dockerfiles and dev commands>

## Scope level
Level <N> — <one-sentence rationale>

## Validation
- [<x or space>] `okteto validate` passed
- [<x or space>] `okteto build` ran for all services
- [<x or space>] `okteto deploy --wait` succeeded with endpoints

## Decisions to confirm
- [ ] Dev image picks (e.g., `okteto/golang:1.22`) match your toolchain
- [ ] Sync paths exclude appropriate generated dirs (node_modules, vendor, target)
- [ ] Helm/kubectl deploy command matches your usual workflow

🤖 Generated by the okteto-onboarding skill
EOF
)"
```

The skill **never merges** the PR. A human reviews and merges.
````

- [ ] **Step 2: Commit**

```bash
git add plugins/okteto/skills/onboarding/SKILL.md
git commit -m "Add Phase 6 (handoff and PR) to onboarding skill"
```

---

### Task 8: Write Section 7, 8, 9 — Operating modes, CLI ref, common mistakes

**Files:**
- Modify: `plugins/okteto/skills/onboarding/SKILL.md`

- [ ] **Step 1: Replace the remaining placeholder sections with this content**

````markdown
## 7. Operating modes

### 7.1 Collaborative (default)

A user is in the loop. Each phase that needs a decision asks a question. Defaults are presented but not auto-selected.

### 7.2 Autonomous (opt-in)

No human is expected to intervene. Inferred from context the same way the existing `okteto` skill does — for example, when invoked from a CI pipeline or a ticket-driven session.

In autonomous mode:
- **Scope level** → highest level the discovery *supports*. Level 2 requires a chart or k8s manifests; Level 3 additionally requires detected tests. With no chart and no manifests, stay at Level 1 even if tests are present.
- **Validation tier** → Tier 1 always; Tier 2 if `okteto context show` succeeds; Tier 3 only if the trigger explicitly authorizes a deploy (label, env var, or explicit instruction).
- **Discovery ambiguities** → pick the most conservative interpretation and note it in the PR description.
- **Phase 6** → always opens a PR (Section 6.2), never hands off.

## 8. CLI quick reference

| Command | When | Purpose |
|---|---|---|
| `okteto validate` | Phase 5 Tier 1 (always) | Check manifest syntax/schema |
| `okteto context show` | Phase 5 pre-checks | Verify cluster connection before Tiers 2/3 |
| `okteto build [<service>]` | Phase 5 Tier 2 | Prove Dockerfiles resolve and push |
| `okteto deploy --wait` | Phase 5 Tier 3 | Full end-to-end validation |
| `okteto endpoints` | Phase 5 Tier 3 | Print URLs after a successful deploy |

**Never** run `okteto up` from this skill — it's interactive and belongs to the existing `okteto` skill / the user. **Never** run `okteto destroy` — leave that to the user.

## 9. Common mistakes to avoid

- **Triggering when an `okteto.yaml` already exists.** Always do the pre-flight check from Section 1.
- **Generating a Helm chart or k8s manifests.** This skill does not author deploy artifacts. If the user has neither chart nor manifests, recommend Level 1 and stop.
- **Skipping the framing block.** The `dev:` vs `deploy:` framing in Section 3.1 must be shown to the user *and* written into the manifest as a header comment.
- **Climbing the validation ladder without checking `okteto context show` first.** Tiers 2 and 3 require a working context.
- **Paraphrasing CLI errors on validation failure.** Show the raw output; the user (or the next agent) needs to see exactly what Okteto said.
- **Asking the user about everything.** Trust the signals from Phase 1. Only ask when discovery is genuinely ambiguous.
- **Merging the PR in autonomous mode.** The PR is the human gate. Never merge.
- **Recommending `okteto/samples/` templates.** Those are demos. Build the manifest from discovered facts, not templates.
````

- [ ] **Step 2: Read the full file end-to-end and verify all sections are filled in**

Run: `wc -l plugins/okteto/skills/onboarding/SKILL.md`
Expected: ~250–350 lines.

Run: `grep -n "^## " plugins/okteto/skills/onboarding/SKILL.md`
Expected: 9 section headings (Activation, Phase 1, Phase 2, Phases 3–4, Phase 5, Phase 6, Operating modes, CLI quick reference, Common mistakes).

Confirm there are no leftover `(skeleton — sections filled in by subsequent tasks)` lines or empty section bodies.

- [ ] **Step 3: Commit**

```bash
git add plugins/okteto/skills/onboarding/SKILL.md
git commit -m "Add operating modes, CLI ref, and common mistakes sections"
```

---

## Phase B: Wire into the plugin

### Task 9: Update dev-setup command to handle missing manifest

**Files:**
- Modify: `plugins/okteto/commands/dev-setup.md`

- [ ] **Step 1: Read the existing file**

Read `plugins/okteto/commands/dev-setup.md` end-to-end. The current step 1 says: *"Discover the project: Read `okteto.yaml`..."*. We add a missing-manifest branch ahead of step 1.

- [ ] **Step 2: Replace step 1 with this content**

Find the line:
```
1. **Discover the project**: Read `okteto.yaml` in the project root to understand services, build targets, and dev configurations.
```

And replace it with:

```
1. **Check for the manifest**:
   - Run `ls okteto.yaml okteto.yml 2>/dev/null` to verify a manifest exists
   - If neither file exists, stop and tell the user:
     > "There's no `okteto.yaml` in this repo. The `okteto-onboarding` skill walks you through creating one. Want me to invoke it?"
   - Do not proceed with the rest of `dev-setup` until a manifest is in place

2. **Discover the project**: Read `okteto.yaml` in the project root to understand services, build targets, and dev configurations.
```

Renumber the subsequent steps accordingly (3, 4, 5, 6, 7, 8 instead of 2, 3, 4, 5, 6, 7).

- [ ] **Step 3: Verify the file still reads coherently**

Run: `cat plugins/okteto/commands/dev-setup.md | head -20`
Expected: step 1 is the manifest check; step 2 is "Discover the project."

- [ ] **Step 4: Commit**

```bash
git add plugins/okteto/commands/dev-setup.md
git commit -m "Add missing-manifest branch to dev-setup command"
```

---

### Task 10: Update README to document the new skill

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Read the existing README**

Read `README.md` end-to-end and locate the section that lists or describes the `okteto` skill.

- [ ] **Step 2: Add a description of the new skill**

Add a paragraph (or table row, matching the existing style) describing `okteto-onboarding`:

```markdown
### `okteto-onboarding`

Activates when a repo has no `okteto.yaml` and the user wants to get the project onto Okteto. Discovers services from `docker-compose.yml`, Helm charts, k8s manifests, or Dockerfiles; drafts an `okteto.yaml`; and validates it through a tiered ladder (`okteto validate` → `okteto build` → `okteto deploy --wait`). Hands off to the `okteto` skill once the manifest exists.
```

Place it adjacent to the existing skill description so both are findable together.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "Document okteto-onboarding skill in README"
```

---

## Phase C: Validate behaviorally

These tasks invoke the skill against fixture repos and inspect the produced manifest. We use the `Agent` tool with `subagent_type: "general-purpose"` because each test needs a fresh context.

### Task 11: Build the test fixtures

**Files:**
- Create: `tests/fixtures/compose-only/docker-compose.yml`
- Create: `tests/fixtures/compose-only/api/Dockerfile`
- Create: `tests/fixtures/compose-only/api/main.go`
- Create: `tests/fixtures/compose-only/api/go.mod`
- Create: `tests/fixtures/chart-and-dockerfiles/chart/Chart.yaml`
- Create: `tests/fixtures/chart-and-dockerfiles/chart/values.yaml`
- Create: `tests/fixtures/chart-and-dockerfiles/api/Dockerfile`
- Create: `tests/fixtures/chart-and-dockerfiles/api/package.json`
- Create: `tests/fixtures/chart-and-dockerfiles/web/Dockerfile`
- Create: `tests/fixtures/chart-and-dockerfiles/web/package.json`
- Create: `tests/fixtures/bare/main.py`
- Create: `tests/fixtures/bare/pyproject.toml`

- [ ] **Step 1: Create the `compose-only` fixture**

```bash
mkdir -p tests/fixtures/compose-only/api
```

`tests/fixtures/compose-only/docker-compose.yml`:
```yaml
services:
  api:
    build:
      context: ./api
    ports:
      - "8080:8080"
    environment:
      DEBUG: "true"
```

`tests/fixtures/compose-only/api/Dockerfile`:
```dockerfile
FROM golang:1.22
WORKDIR /app
COPY . .
RUN go build -o api .
CMD ["./api"]
```

`tests/fixtures/compose-only/api/go.mod`:
```
module example.com/api

go 1.22
```

`tests/fixtures/compose-only/api/main.go`:
```go
package main

import "fmt"

func main() {
    fmt.Println("api up")
}
```

- [ ] **Step 2: Create the `chart-and-dockerfiles` fixture**

```bash
mkdir -p tests/fixtures/chart-and-dockerfiles/{chart,api,web}
```

`tests/fixtures/chart-and-dockerfiles/chart/Chart.yaml`:
```yaml
apiVersion: v2
name: example
description: Example chart
type: application
version: 0.1.0
appVersion: "1.0"
```

`tests/fixtures/chart-and-dockerfiles/chart/values.yaml`:
```yaml
api:
  image: api
web:
  image: web
```

`tests/fixtures/chart-and-dockerfiles/api/Dockerfile`:
```dockerfile
FROM node:20
WORKDIR /app
COPY . .
RUN npm ci
CMD ["node", "server.js"]
```

`tests/fixtures/chart-and-dockerfiles/api/package.json`:
```json
{
  "name": "api",
  "version": "1.0.0",
  "scripts": {
    "dev": "node --watch server.js",
    "test": "node --test"
  },
  "engines": {
    "node": "20"
  }
}
```

`tests/fixtures/chart-and-dockerfiles/web/Dockerfile`:
```dockerfile
FROM node:20
WORKDIR /app
COPY . .
RUN npm ci
CMD ["npm", "start"]
```

`tests/fixtures/chart-and-dockerfiles/web/package.json`:
```json
{
  "name": "web",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "test": "vitest"
  },
  "engines": {
    "node": "20"
  }
}
```

- [ ] **Step 3: Create the `bare` fixture**

```bash
mkdir -p tests/fixtures/bare
```

`tests/fixtures/bare/pyproject.toml`:
```toml
[project]
name = "bare"
version = "0.1.0"
requires-python = ">=3.12"
```

`tests/fixtures/bare/main.py`:
```python
print("bare app")
```

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/
git commit -m "Add behavioral test fixtures for onboarding skill"
```

---

### Task 12: Test against the compose-only fixture

- [ ] **Step 1: Dispatch a subagent to invoke the skill**

Use the `Agent` tool with `subagent_type: "general-purpose"` and this prompt:

> You are testing a skill in development. The skill content is in `plugins/okteto/skills/onboarding/SKILL.md` (read it). Then `cd` to `tests/fixtures/compose-only/` and follow the skill exactly as a Claude session would: do Phase 1 discovery, Phase 2 scope negotiation (assume user picks the recommended level), Phases 3–4 (write `okteto.yaml`), Phase 5 Tier 1 only (run `okteto validate`). Do **not** ask any clarifying questions — make the conservative pick where the skill says "ask the user" (this simulates autonomous mode without opening a PR). Report what was produced and whether `okteto validate` passed. Do not commit anything.

- [ ] **Step 2: Inspect the produced manifest**

Read `tests/fixtures/compose-only/okteto.yaml`. Verify:
- The framing comment block is at the top
- `dev:` section exists with one entry for `api`
- The dev image is `okteto/golang:1.22` (since `go.mod` declares 1.22)
- Sync path is set
- The level chosen is **Level 1** (since there's no chart or k8s manifests)

- [ ] **Step 3: Run validation manually**

```bash
cd tests/fixtures/compose-only && okteto validate
```
Expected: passes.

- [ ] **Step 4: Commit the produced manifest as a snapshot**

```bash
git add tests/fixtures/compose-only/okteto.yaml
git commit -m "Snapshot generated manifest for compose-only fixture"
```

If the produced manifest has issues (wrong image, missing comment, fails validate), do **not** commit — instead, edit the skill (`plugins/okteto/skills/onboarding/SKILL.md`) to fix the issue, commit the skill fix, and re-run this task from Step 1.

---

### Task 13: Test against the chart-and-dockerfiles fixture

- [ ] **Step 1: Dispatch a subagent**

Same prompt template as Task 12, but `cd` to `tests/fixtures/chart-and-dockerfiles/`.

- [ ] **Step 2: Inspect the produced manifest**

Read `tests/fixtures/chart-and-dockerfiles/okteto.yaml`. Verify:
- Two services in `build:` and `dev:` (api, web)
- `deploy:` is a `helm upgrade --install` command pointing at `./chart`
- Dev images are `okteto/node:20` for both (matching `engines.node`)
- Dev commands are `npm run dev` for both (since both have `scripts.dev`)
- Level chosen is **Level 3** (chart + tests detected) — there should be a `test:` section

- [ ] **Step 3: Run validation manually**

```bash
cd tests/fixtures/chart-and-dockerfiles && okteto validate
```
Expected: passes.

- [ ] **Step 4: Commit the snapshot**

```bash
git add tests/fixtures/chart-and-dockerfiles/okteto.yaml
git commit -m "Snapshot generated manifest for chart-and-dockerfiles fixture"
```

If issues, fix the skill first (as in Task 12 Step 4), commit, then re-run.

---

### Task 14: Test against the bare fixture

- [ ] **Step 1: Dispatch a subagent**

Same prompt template, `cd` to `tests/fixtures/bare/`.

- [ ] **Step 2: Inspect the produced manifest**

Read `tests/fixtures/bare/okteto.yaml`. Verify:
- Level chosen is **Level 1** (no chart, no compose, no Dockerfile)
- The skill correctly explains why higher levels are unavailable
- Dev image is `okteto/python:3.12` (matching `pyproject.toml`)
- The skill probably had to ask "what command starts your dev server?" — in the simulated autonomous run, the conservative pick is `bash`

- [ ] **Step 3: Run validation manually**

```bash
cd tests/fixtures/bare && okteto validate
```
Expected: passes.

- [ ] **Step 4: Commit the snapshot**

```bash
git add tests/fixtures/bare/okteto.yaml
git commit -m "Snapshot generated manifest for bare fixture"
```

---

## Phase D: Finalize

### Task 15: Self-review the skill against the spec

- [ ] **Step 1: Re-read the spec and the skill side by side**

Open both files. For each numbered section in the skill, confirm it implements the corresponding spec section. List any gaps.

```bash
diff <(grep "^##" docs/superpowers/specs/2026-04-28-okteto-onboarding-skill-design.md) <(grep "^##" plugins/okteto/skills/onboarding/SKILL.md)
```

- [ ] **Step 2: Placeholder scan**

```bash
grep -nE "TBD|TODO|FIXME|XXX|\\?\\?\\?" plugins/okteto/skills/onboarding/SKILL.md
```
Expected: no matches.

- [ ] **Step 3: Internal consistency check**

Verify the same vocabulary is used consistently:
- "Level 1 / Level 2 / Level 3" (not "minimal / standard / full")
- "Tier 1 / Tier 2 / Tier 3" for validation
- "Phase 1 ... Phase 6" for the workflow

```bash
grep -nE "^##" plugins/okteto/skills/onboarding/SKILL.md
grep -nE "Level [123]|Tier [123]|Phase [1-6]" plugins/okteto/skills/onboarding/SKILL.md | head -20
```

- [ ] **Step 4: Fix anything found, commit if changes were made**

```bash
git add plugins/okteto/skills/onboarding/SKILL.md
git commit -m "Skill self-review fixes"
```

(Skip the commit if there were no findings.)

---

### Task 16: Push the branch and open a PR

- [ ] **Step 1: Push the branch**

```bash
git push -u origin feat/onboarding-skill-design
```

- [ ] **Step 2: Open a PR**

```bash
gh pr create --title "Add okteto-onboarding skill" --body "$(cat <<'EOF'
## Summary
- New skill `okteto-onboarding` that walks a repo with no `okteto.yaml` through discovery, drafting, and tiered validation
- Sibling to the existing `okteto` skill in the same plugin (auto-discovered)
- Updates `/dev-setup` to suggest invoking the new skill when no manifest is present
- Adds behavioral test fixtures and snapshot manifests under `tests/fixtures/`

## Spec
[docs/superpowers/specs/2026-04-28-okteto-onboarding-skill-design.md](./docs/superpowers/specs/2026-04-28-okteto-onboarding-skill-design.md)

## Test plan
- [x] Generated manifest for compose-only fixture passes `okteto validate`
- [x] Generated manifest for chart-and-dockerfiles fixture passes `okteto validate`
- [x] Generated manifest for bare fixture passes `okteto validate`
- [ ] Reviewer to spot-check the inline comments in each generated manifest for clarity
- [ ] Reviewer to confirm the framing block (dev: vs deploy:) is the right level of explanation

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: Return the PR URL to the user**

Capture the URL from `gh pr create` output and show it to the user. Done.

---

## Self-review checklist (executed by writing-plans, not the engineer)

Run after this plan is saved.

1. **Spec coverage:** every spec section maps to at least one task. ✓
2. **Placeholder scan:** no TBD/TODO/FIXME in the plan. ✓
3. **Type consistency:** "Level 1/2/3", "Tier 1/2/3", "Phase 1–6" used identically across spec and plan. ✓
4. **File paths:** every task lists exact paths. ✓
5. **Commands:** every command is exact, with expected output where relevant. ✓
