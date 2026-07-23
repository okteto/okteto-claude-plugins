---
name: okteto-manifest-optimizer
description: |
  Use when the user asks to create, scaffold, write, review, or optimize an
  okteto.yaml / Okteto Manifest for a Development Environment — "make my
  okteto.yaml faster", "review this manifest for performance", "why is my dev
  environment slow to start or sync", "set up an efficient okteto.yaml" — or
  when authoring the build/dev/test sections or the .dockerignore /
  .oktetoignore / .stignore files that go with them. Do NOT use to run, deploy,
  or debug a live environment (use the okteto and okteto-debugging skills), and
  defer first-time service discovery on a repo that has no manifest yet to
  okteto-onboarding — then come back here to optimize what it drafts.
license: Apache-2.0
---

# Okteto Manifest Optimizer

This skill authors and reviews Okteto Manifests (`okteto.yaml`) that follow Okteto's [documented performance best practices](https://www.okteto.com/docs/tutorials/optimize-your-development-environment/), together with the `.dockerignore`, `.oktetoignore`, and `.stignore` files that go with them. Slow environments almost always trace to one of three causes: unpinned images that defeat node cache reuse, a bloated build or sync context, or dependencies that are re-downloaded on every start. This skill removes those.

Full field reference and worked examples for every rule below live in `${CLAUDE_PLUGIN_ROOT}/skills/okteto-manifest-optimizer/reference/okteto-manifest-fields.md`. Read it when you need the exact syntax; the rules here are enough to act.

## Operating rules

These rules prevent the mistakes that make environments slow. Apply every one to every manifest you produce.

1. **Verify against the repo — never invent.** Read the Dockerfile(s), the dependency manifest (`package.json`, `go.mod`, `pom.xml`, `requirements.txt`), and any existing `okteto.yaml` first. Every service name, image, sync path, volume, and cache dir must trace to something in the repo.
2. **Pin every image.** Never `:latest` — use a version tag or an `@sha256` digest. Wire each dev container's image to its build with `${OKTETO_BUILD_<NAME>_IMAGE}` (uppercase the build name, `-` becomes `_`: build `api` → `${OKTETO_BUILD_API_IMAGE}`, build `web-dev` → `${OKTETO_BUILD_WEB_DEV_IMAGE}`).
3. **Context and sync are the highest-impact levers.** Always ship a `.dockerignore` (exclude `*`, then `!`-include only build inputs) and a `.stignore` (sync active source only — never artifacts, dependency directories, or `.git`). Add a `.oktetoignore` when the deploy or test context is large.
4. **Persist dependencies and caches — don't re-fetch them.** Put dependency and build-cache directories in `dev.<svc>.volumes`, mirror them in `test.<name>.caches` for test containers, and use BuildKit cache mounts in the Dockerfile. See the [per-language cache map](#per-language-dependency--cache-directories).
5. **Always set `resources.requests` and `resources.limits`** on dev containers. Both are unset by default, which starves the scheduler and causes slow or `Pending` starts.
6. **Get `forward` vs `reverse` direction right.** `forward` is `localPort:remotePort` (reach a container port from `localhost`). `reverse` is `remotePort:localPort` (send from the container back to your machine, e.g. a debugger callback). Swapping them silently breaks the connection.
7. **Order the Dockerfile by change frequency and never `COPY . .`.** Base image and system packages first, dependency install next, source copy last. Copy only what each stage needs. This is what makes Okteto Smart Builds and layer caching effective.
8. **Author only — never run.** This skill writes and reviews manifests. Recommend `okteto validate` to check the result, but do not run `okteto up`, `okteto deploy`, or `okteto build` here — that is the `okteto` skill's job.

## Workflow

1. **Discover the stack.** Identify each service, its language/build tool, its Dockerfile, and its source layout from the repo (rule 1). If there is no manifest at all and the services are unknown, hand off to `okteto-onboarding` first, then optimize its draft.
2. **Author `build` → `deploy` → `dev` → `test`.** See [Manifest shape](#manifest-shape). Apply the [best-practice levers](#best-practice-levers) as you write each section.
3. **Write the ignore files** (`.dockerignore`, `.stignore`, and `.oktetoignore` if needed). These are quick wins; see the reference for copy-paste templates.
4. **Run the [pre-return review checklist](#pre-return-review-checklist)** and recommend `okteto validate` before the user deploys.

## Manifest shape

| Section | Purpose | Optimization focus |
|---|---|---|
| `build` | Images Okteto builds for each service | Pin bases, order layers, cache mounts, a `target` per stage for a `-dev` image |
| `deploy` | How the stack is provisioned (Helm/manifests/commands) | Wire images with `${OKTETO_BUILD_<NAME>_IMAGE}` |
| `dev.<svc>` | Live-edit config: `image`, `command`, `sync`, `forward`/`reverse`, `volumes`, `resources` | Sync source only; persist deps in `volumes`; set `resources`; correct port direction |
| `test.<name>` | Test containers run via Remote Execution | `caches` for dependency/build dirs; pin `image` |

## Best-practice levers

Fourteen practices from the source doc, grouped. One-line reminders here; full examples in the reference file.

**Images & build**

| # | Practice | Do this |
|---|---|---|
| 1 | Pin images | Version tag or `@sha256`; never `:latest` |
| 2 | Okteto Smart Builds | Let identical builds be skipped from cache; don't defeat it with churny layers |
| 3 | Order layers by change frequency | Base + system packages first, deps next, source last |
| 4 | Avoid `COPY . .` | Copy only build inputs (`COPY package.json .`, then `COPY src/ src/`) |
| 5 | Avoid recursive ops | `RUN chown -R` → `COPY --chown=user:group` |
| 6 | BuildKit cache mounts | `RUN --mount=type=cache,target=<dep-or-build-cache>` |

**Context & sync (highest impact)**

| # | Practice | Do this |
|---|---|---|
| 7 | `.dockerignore` | Exclude `*`, then `!`-include only build inputs |
| 8 | `.oktetoignore` | gitignore syntax with `[deploy]` / `[test]` sections |
| 9 | `.stignore` | Sync active source only; never artifacts, deps, or `.git` |
| 10 | Precopy source into dev image | Multi-stage: a `-dev` build `target` that already contains the source |

**Data & environment**

| # | Practice | Do this |
|---|---|---|
| 11 | Volume Snapshots over seed scripts | Preload databases from a snapshot instead of slow seed scripts |
| 12 | Okteto Divert | When full isolation isn't required, route into a shared environment |

**Dev container & tests**

| # | Practice | Do this |
|---|---|---|
| 13 | `dev.<svc>.volumes` | Persist dep/cache dirs across `okteto up` sessions |
| 14 | `test.<name>.caches` | Cache dep/build dirs across test runs |

Also enforce, from the Okteto Manifest reference: `resources.requests` **and** `resources.limits` on every dev container, and correct `forward`/`reverse` direction (Operating rules 5–6).

### Per-language dependency & cache directories

Persist these in `dev.<svc>.volumes` and `test.<name>.caches`, and mount them as BuildKit caches:

| Stack | Dependency / cache directories |
|---|---|
| Node.js | `node_modules`, `~/.npm` (or `.yarn/cache`) |
| Go | `/go/pkg/mod`, `/root/.cache/go-build` |
| Java / Maven | `/root/.m2` |
| Python | `~/.cache/pip`, the virtualenv / `.venv` |

## Pre-return review checklist

Do not hand back a manifest until all nine pass. Report each result.

1. **No `:latest`** anywhere in `build` or `dev` images — every image is a version tag or `@sha256` digest.
2. **`dev.<svc>.image` is wired via `${OKTETO_BUILD_<NAME>_IMAGE}`** (not a hardcoded tag) when the service is built by Okteto.
3. **`sync` is scoped to source**, and a **`.stignore` excludes** artifacts, dependency directories, and `.git`.
4. **Dependency/build directories are in `dev.<svc>.volumes`** (see the cache map) so they survive restarts.
5. **`resources.requests` and `resources.limits` are both present** on each dev container.
6. **`forward` (`local:remote`) and `reverse` (`remote:local`) point the right way.**
7. **A `.dockerignore` scopes the build context** — excludes `*`, then `!`-includes only build inputs.
8. **`test.<name>.caches` is set** for every test container (where tests exist).
9. **Dockerfiles are layer-ordered and free of `COPY . .`** and recursive `RUN chown -R`.

## Related skills

- **`okteto-onboarding`** — discovers services and drafts a first `okteto.yaml` on a repo that has none. Use it before this skill when the services are unknown; then optimize its output here.
- **`okteto`** — deploying, developing, and iterating in a live environment (`okteto deploy`, `okteto up`, `okteto exec`). This skill hands the finished manifest to it.
- **`okteto-debugging`** — triaging a broken or unhealthy environment (`CrashLoopBackOff`, `OOMKilled`, stuck sync). Use it when the problem is runtime failure, not manifest performance.
