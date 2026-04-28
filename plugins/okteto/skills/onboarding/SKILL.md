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
## 5. Phase 5 — Validate (tiered)
## 6. Phase 6 — Handoff or PR
## 7. Operating modes
## 8. CLI quick reference
## 9. Common mistakes to avoid
