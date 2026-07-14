---
name: okteto-preview
description: |
  Okteto Preview Environment skill. Use when someone wants a live, shareable
  environment for a branch or pull request — "deploy a preview for this PR",
  "give me a URL for branch X", posting a preview link back to a PR or thread —
  or when setting up PR preview automation in CI (GitHub Actions or GitLab).
  Use alongside the `okteto` skill: for editing, syncing, and iterating on code,
  defer to that skill's dev environments. Requires an Okteto context; previews
  are an Okteto Platform feature.
license: Apache-2.0
---

# Okteto Preview Environments Skill

A **Preview Environment** is a live, production-like instance of the application deployed from a **git branch**, usually tied to the lifecycle of a pull request. Okteto deploys it into a dedicated namespace named after the preview and gives you shareable URLs, so reviewers, PMs, and stakeholders can click through real functionality without any local setup.

## Operating rules

1. **Previews deploy from the pushed branch, not your working tree.** `okteto preview deploy` clones the repository at `--branch` and deploys that. Local uncommitted changes never reach a preview — commit and push first.
2. **Always name the preview explicitly** (e.g. `pr-1234`). Redeploying with the same name updates the same preview; omitting the name generates a random one that CI and cleanup jobs can never find again.
3. **Use a preview to share, a namespace to work.** Iterating on code belongs in a dev environment (`okteto` skill). A preview is the artifact you hand to reviewers — it has no file sync and no dev containers of yours attached.
4. **Never destroy a preview you did not create.** Same doctrine as the `okteto` skill's cleanup rules: a preview you created for your own task is yours to destroy; shared/global previews and CI-owned previews are not (see [Cleanup and teardown](#cleanup-and-teardown)).
5. **In CI, the pipeline owns the lifecycle.** Deploy on PR open/update, destroy on PR close — via `okteto/deploy-preview` and `okteto/destroy-preview` (GitHub) or `okteto preview deploy`/`destroy` jobs (GitLab).

## Preview vs. namespace: which environment does this task need?

Both give you an isolated, deployed copy of the application. They answer different questions:

| | Dev environment (namespace) | Preview Environment |
|---|---|---|
| Deploys from | Your local working tree (`okteto deploy`) | A pushed git branch (server-side clone) |
| Lifecycle | Yours — lives as long as the work does | A pull request — created on open, destroyed on close |
| Audience | You / the agent doing the work | Reviewers, PMs, stakeholders, the PR thread |
| File sync / `okteto up` | Yes — iterate live | No — redeploy by pushing to the branch |
| Where it shows up | Namespaces in the Okteto dashboard | Previews section of the dashboard, with repo/branch/PR links |
| Created by | `okteto namespace create` + `okteto deploy` | `okteto preview deploy` (CLI or CI) |

Decision guide:

- **"Fix this, test this, debug this"** → dev environment in a namespace. Follow the `okteto` skill.
- **"Give me / the team a link to see branch X or PR Y"** → preview environment.
- **Ticket-to-PR flows use both**: do the work in a namespace dev environment, push the branch, open the PR — then deploy a preview *from the pushed branch* and post its URL on the PR. The namespace is your workbench; the preview is the deliverable reviewers click.

---

## Deploying a preview

Previews deploy the code Okteto clones from the repository — so push first:

```bash
git push -u origin <branch>
okteto preview deploy pr-1234 --branch <branch> --wait
```

Key flags (see the [quick reference](#cli-quick-reference) for the full list):

- **`--scope personal|global`** — defaults to **`global`**: accessible to all members of the organization. Use `personal` for experiments only you (and people you explicitly share with) should see. Don't assume personal is the default — it isn't. Sharing a personal preview with specific people happens on its dashboard page (`/previews/<name>`), not through the CLI, and only the owner or an admin can share it.
- **`--branch <branch>`** — defaults to the current branch of the checkout you run from.
- **`--repository <url>`** — defaults to the current repo's remote URL. Pass it explicitly when deploying a repo you don't have checked out.
- **`--var KEY=VALUE`** — injects a variable into the manifest's deploy commands. Repeat the flag for multiple variables.
- **`--sourceUrl <pr-url>`** — the HTTPS URL of the pull/merge request; links the PR in the dashboard's Previews list.
- **`--timeout`** — defaults to `5m0s`. Raise it for large stacks (`-t 15m`).
- **`--file`** — path to the Okteto Manifest if it isn't at the default location.

### Naming previews

The preview name becomes the namespace name, so it must be lowercase alphanumeric and `-`, at most 63 characters. Conventions:

- **PR-keyed** (GitHub): `pr-<number>` — stable across pushes to the PR, easy for the cleanup job to find.
- **Branch-keyed** (GitLab): `review-<branch-slug>` — e.g. `review-$CI_COMMIT_REF_SLUG`, one preview per branch.

If you omit the name, the CLI generates a random one (and for `--scope personal`, appends your lowercased username). Fine for a quick manual experiment; wrong everywhere else — a redeploy creates a *second* preview instead of updating the first.

---

## Capturing endpoints and posting the URL back

After a successful deploy, capture the endpoints:

```bash
okteto preview endpoints pr-1234            # JSON (default) — parse programmatically
okteto preview endpoints pr-1234 -o md      # Markdown — made for pasting into a PR comment
```

The dashboard page for a preview lives at `https://<your-okteto-url>/previews/<name>`.

**Posting to the PR with `gh`** (when you deployed the preview yourself, outside CI):

```bash
gh pr comment 1234 --body "$(cat <<EOF
Preview environment ready — [dashboard](https://<your-okteto-url>/previews/pr-1234)

$(okteto preview endpoints pr-1234 -o md)
EOF
)"
```

**Posting to a thread** (Slack, ticket, chat): same content — the endpoints from `-o md` plus the dashboard link. The whole point of a preview is that anyone in the thread can click the same URL.

**In CI you usually don't need to post at all**: the `okteto/deploy-preview` GitHub Action posts the URL and endpoints as a PR comment automatically when the `GITHUB_TOKEN` env var is set. Don't add a second `gh pr comment` step on top of it.

---

## Previews in CI

### GitHub Actions: `okteto/deploy-preview`

The canonical pair of workflows — deploy on PR open/update, destroy on close:

```yaml
# .github/workflows/preview.yaml
on:
  pull_request:
    branches:
      - main

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: false   # never true — cancelling an in-progress deploy leaves the preview inconsistent

jobs:
  preview:
    runs-on: ubuntu-latest
    steps:
      - name: Context
        uses: okteto/context@latest
        with:
          url: ${{ secrets.OKTETO_CONTEXT }}
          token: ${{ secrets.OKTETO_TOKEN }}

      - name: Deploy preview environment
        uses: okteto/deploy-preview@latest
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}   # enables the automatic PR comment with the URL
        with:
          name: pr-${{ github.event.number }}
          timeout: 15m
```

```yaml
# .github/workflows/preview-closed.yaml
on:
  pull_request:
    types:
      - closed

jobs:
  closed:
    runs-on: ubuntu-latest
    steps:
      - name: Context
        uses: okteto/context@latest
        with:
          url: ${{ secrets.OKTETO_CONTEXT }}
          token: ${{ secrets.OKTETO_TOKEN }}

      - name: Destroy preview environment
        uses: okteto/destroy-preview@latest
        with:
          name: pr-${{ github.event.number }}   # must match the deploy workflow's name exactly
```

Repository secrets required: `OKTETO_CONTEXT` (the URL of the Okteto instance, e.g. `https://okteto.example.com`) and `OKTETO_TOKEN` (an Okteto Admin Access Token). `GITHUB_TOKEN` is populated by GitHub automatically.

`okteto/deploy-preview` inputs: `name` (required), `scope` (default `global`), `variables` (comma-separated `VAR1=VAL1,VAR2=VAL2`), `file`, `branch` (defaults to the branch that triggered the action), `timeout`, `log-level`, `dependencies`, `labels` (comma-separated).

### GitLab CI/CD

Same shape with the CLI directly (image `ghcr.io/okteto/okteto:latest`): a `review` job runs `okteto preview deploy review-$CI_COMMIT_REF_SLUG --branch $CI_COMMIT_REF_NAME --repository $CI_PROJECT_URL`, and a `stop-review` job runs `okteto preview destroy review-$CI_COMMIT_REF_SLUG` when the branch is deleted or the MR merges. Pass the preview URL via the job's `environment.url` so reviewers can open it from GitLab.

---

## Inspecting, sleeping, and waking previews

```bash
okteto preview list                    # status and scope of your previews (-o json|yaml)
okteto preview list --label team-a     # filter by label
okteto preview sleep pr-1234           # scale it down to save resources (owner or admin only)
okteto preview wake pr-1234            # bring a sleeping preview back
```

Sleeping keeps the preview and its configuration; waking restores it. Prefer `sleep` over `destroy` when the goal is saving resources on a preview someone may still need. Admins can also mark a preview **Persistent** in the dashboard, which exempts it from automatic sleep and garbage collection — that's a dashboard action, not a CLI one.

Applications can detect they're running in a preview via the `OKTETO_IS_PREVIEW_ENVIRONMENT=true` environment variable — useful when the task is "make the app behave differently in previews".

---

## Cleanup and teardown

`okteto preview destroy <name>` runs any `destroy` commands in the Okteto Manifest, then removes the preview and its namespace. It is destructive — the same authorization doctrine as the `okteto` skill applies:

| Situation | May the agent destroy it? |
|---|---|
| Preview the agent created this session for its own task | **Yes** — yours to tear down when the work is done and the URL is no longer needed |
| CI-owned preview (e.g. `pr-<number>` managed by workflows) | **No** — the close-PR workflow owns teardown. Destroying it mid-review breaks the link reviewers are using |
| Global preview created by someone else | **Never** without explicit instruction |
| Someone else's personal preview | **Never** — and only admins or the owner could anyway |

- In **collaborative mode**, surface the command and let the developer run it: "To tear down the preview, run: `okteto preview destroy pr-1234`".
- In **autonomous mode**, a preview you created this session is yours to destroy once the task no longer needs it — the same "you created it, you own its teardown" rule as the `okteto` skill's worktree namespaces. One caveat: if you posted its URL to a PR or thread, reviewers may still be using it — leave it running (or `okteto preview sleep <name>`) and report the teardown command instead. For any preview you did **not** create, destroy only with explicit authorization, a documented cleanup policy, or pipeline ownership of this run.
- **Don't use `destroy` as a retry.** A failed or stale preview is fixed by redeploying with the same name — `okteto preview deploy <name>` updates in place.

---

## CLI quick reference

| Command | Collaborative | Autonomous | Purpose |
|---------|:---:|:---:|---------|
| `okteto preview deploy <name>` | Agent | Agent | Deploy a preview from a pushed branch |
| `okteto preview endpoints <name>` | Agent | Agent | List preview URLs (`-o json` default, `-o md` for PR comments) |
| `okteto preview list` | Agent | Agent | Status and scope of your previews |
| `okteto preview sleep <name>` | Agent (own) | Agent (own) | Scale down a preview you own |
| `okteto preview wake <name>` | Agent | Agent | Wake a sleeping preview |
| `okteto preview destroy <name>` | User (or self-created) | Self-created / with policy | Tear down a preview and its namespace |

`okteto preview deploy` flags: `-b/--branch` (default: current branch), `--repository` (default: current repo), `-s/--scope personal|global` (default: `global`), `-v/--var KEY=VALUE` (repeatable), `--sourceUrl <pr-url>`, `-t/--timeout` (default `5m0s`), `-w/--wait` (default `true`), `-f/--file`, `--label` (repeatable), `--dependencies`.

## Common mistakes to avoid

- **Expecting local changes in the preview.** Previews deploy from the pushed branch. Commit and push before `okteto preview deploy`, and push again to update it.
- **Omitting the preview name in CI.** A nameless deploy gets a random name, so every run creates a new preview and the cleanup job orphans them all. Key the name to the PR (`pr-<number>`) or branch slug.
- **Mismatched names between deploy and destroy workflows.** The destroy job must use the exact same name expression as the deploy job, or previews leak.
- **Assuming `--scope` defaults to `personal`.** The default is `global` — visible to the whole organization. Say `--scope personal` when the work isn't ready to share.
- **Using a preview as a dev environment.** No file sync, no `okteto up`. To iterate on code, use a namespace dev environment (`okteto` skill) and keep the preview for reviewers.
- **Running `okteto endpoints` instead of `okteto preview endpoints <name>`.** The former targets the active namespace of your context, not the preview.
- **Setting `cancel-in-progress: true` on the preview workflow.** Cancelling an in-progress deploy leaves the preview inconsistent and leaks resources. Queue per-PR with `cancel-in-progress: false`.
- **Double-posting the URL in CI.** With `GITHUB_TOKEN` set, `okteto/deploy-preview` already comments on the PR. Add your own `gh pr comment` only when deploying from outside CI.
- **Destroying a preview you don't own.** CI-owned, shared/global, or someone else's previews are off-limits without explicit instruction — same rule as `okteto destroy` in the `okteto` skill.
- **Destroying to "fix" a broken preview.** Redeploy with the same name instead; it updates in place.
