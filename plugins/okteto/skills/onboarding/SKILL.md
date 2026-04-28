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
## 3. Phase 2 — Negotiate scope
## 4. Phases 3–4 — Draft and refine
## 5. Phase 5 — Validate (tiered)
## 6. Phase 6 — Handoff or PR
## 7. Operating modes
## 8. CLI quick reference
## 9. Common mistakes to avoid
