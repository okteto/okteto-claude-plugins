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

````bash
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
````

The skill **never merges** the PR. A human reviews and merges.

## 7. Operating modes
## 8. CLI quick reference
## 9. Common mistakes to avoid
