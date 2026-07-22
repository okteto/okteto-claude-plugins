---
name: okteto-debugging
description: |
  Use when the user describes a broken or unhealthy Okteto environment. Triggers on phrases like:
  "service is crashing", "service keeps restarting", "service won't start", "environment is broken",
  "deployment is failing", "pods are stuck", "pods are not ready", "pods are pending",
  "CrashLoopBackOff", "OOMKilled", "ImagePullBackOff", "Evicted",
  "what's wrong with my service", "debug my environment", "why won't it start",
  "something's wrong", "logs show errors", "service isn't responding",
  "my code changes aren't showing up", "file sync is stuck".
  Also triggers if the user pastes kubectl or okteto output showing unhealthy pod states.
license: Apache-2.0
---

# Okteto Environment Debugger

This skill triages broken Okteto environments. When a service is misbehaving, run through the triage algorithm below, apply the matching playbook, and emit a structured diagnosis. Do not guess — always let the command output drive the conclusion.

Diagnostics are **read-only**: `kubectl get`, `kubectl describe`, `kubectl logs`, and `kubectl get events` are fine here. Never mutate the cluster with raw `kubectl`/`helm` — fixes go through `okteto build` and `okteto deploy` (see the `okteto` skill for lifecycle operations, worktree isolation, and teardown rules).

## Triage algorithm

Run these steps in order. Stop at the first step that identifies the failure.

### Step 1: Verify connectivity and pin the namespace

```bash
okteto context show
```

If this fails, the user is disconnected from the cluster. Stop and help them reconnect (`okteto context use <url>`) before proceeding.

The JSON output includes the active `namespace`. Capture it — every command below targets it explicitly as `$ns`:

```bash
ns=$(okteto context show | jq -r .namespace)
```

If you are working in an isolated worktree namespace (see the `okteto` skill), use that namespace instead — the environment you need to debug lives there, not in the context's default.

**kubectl must target the same cluster and namespace as Okteto.** kubectl reads its own kubeconfig, which can point at a different namespace — or a different cluster entirely — than the Okteto context, especially when multiple agents or worktrees are active on the same machine. Run `okteto kubeconfig` to download credentials for the cluster selected via `okteto context`, and pass `-n "$ns"` on every kubectl command. If `kubectl get pods -n "$ns"` errors or shows pods that don't match the services in `okteto.yaml`, fix the kubeconfig before trusting any diagnostic output.

### Step 2: Discover services

```bash
cat okteto.yaml
```

Parse the `deploy` and `dev` sections for canonical service names. Never hardcode service names — always derive them from `okteto.yaml`.

### Step 3: Snapshot pod states

```bash
kubectl get pods -n "$ns"
```

This is the master triage signal. Map each pod to one of these states and apply the matching playbook below:

| Pod state | Playbook |
|---|---|
| `CrashLoopBackOff` | [Crash loop](#crash-loop-crashloopbackoff) |
| `OOMKilled` | [OOM kill](#oom-kill-oomkilled) |
| `ImagePullBackOff` / `ErrImagePull` | [Image pull failure](#image-pull-failure) |
| `Pending` (> 60s) | [Unschedulable](#pending--unschedulable) |
| `Running` but not serving / health checks failing | [Runtime error](#runtime-error-running-but-unhealthy) |
| No pods exist / deploy never completed | [Deploy failure](#deploy-failure) |
| All pods `Running` and `Ready` | [Sync / dev mode issue](#sync--dev-mode-issue) |

If the user named a specific service, filter to that service's pods only. If no service was named, check all pods.

---

## Playbooks

### Crash loop (CrashLoopBackOff)

The container starts, crashes, and Kubernetes keeps restarting it.

```bash
# Get logs from the previous (crashed) container instance
kubectl logs <pod-name> --previous -n "$ns"

# If that fails (first crash, no previous), get current logs
kubectl logs <pod-name> -n "$ns"

# Check exit code and liveness/readiness probe config
kubectl describe pod <pod-name> -n "$ns"
```

**Look for:**
- Exit code in `kubectl describe pod` — `Exit Code: 1` is an app error; `Exit Code: 137` is OOM (see OOM playbook); `Exit Code: 126/127` means the entrypoint command wasn't found
- The last lines of `--previous` logs — the final error before crash is usually the root cause
- Liveness probe failures in `kubectl describe pod` events section — misconfigured health check paths or timeouts

**Common root causes:**
- Missing or wrong environment variable (`fatal: required env var FOO not set`)
- Can't connect to a dependency (database, message queue) that isn't ready yet
- Port mismatch between app and probe configuration
- Command/entrypoint not found (wrong base image or typo in okteto.yaml `command`)

---

### OOM kill (OOMKilled)

The container exceeded its memory limit and was killed by Kubernetes.

```bash
kubectl describe pod <pod-name> -n "$ns"
```

**Look for:**
- `OOMKilled` in the `Last State` section
- `limits.memory` value under `Containers` → `Limits`
- Compare limit to how much memory the service actually needs

**Fix pattern:**
Increase the memory limit in the service's Helm values or `okteto.yaml`. Show the user the exact current limit and suggest a reasonable increase (typically 2×). Do not suggest removing limits entirely.

---

### Image pull failure

Kubernetes can't pull the container image.

```bash
kubectl describe pod <pod-name> -n "$ns"
```

**Look for:**
- `Failed to pull image` in the Events section
- The exact image reference Kubernetes tried to pull (registry, repo, tag)
- `ImagePullBackOff` vs `ErrImagePull` — both mean the same thing, different retry states

**Common root causes:**
- Image doesn't exist (typo in tag, or `okteto build` was never run for this service)
- Image exists but is in a private registry with no pull credentials
- Tag was deleted or overwritten after a bad push

**Fix pattern:**
If the image should have been built by Okteto, run `okteto build <service>`. If the image is external, verify the tag exists. If credentials are the issue, help the user create an image pull secret.

---

### Pending / unschedulable

The pod has been accepted by Kubernetes but hasn't been scheduled onto a node.

```bash
kubectl describe pod <pod-name> -n "$ns"

# Also check recent namespace events for quota / resource pressure
kubectl get events -n "$ns" --sort-by=.lastTimestamp | tail -20
```

**Look for in `kubectl describe pod` → Events:**
- `Insufficient cpu` or `Insufficient memory` — node has no room; check resource requests
- `0/N nodes are available` — no node matches the scheduling constraints
- `node(s) had untolerated taint` — pod needs a toleration for a taint on the nodes
- `node(s) didn't match node affinity/selector` — nodeSelector or affinity rules are too strict
- Resource quota exceeded — check `kubectl describe resourcequota -n "$ns"`

**Fix pattern:**
Match the error to the constraint. For resource requests, lower the request or ask the user to scale the node pool. For taints/selectors, show the current constraint and suggest removing or correcting it.

---

### Runtime error (Running but unhealthy)

Pods are `Running` but the service isn't responding, health checks are failing, or the user sees errors in requests.

```bash
# Get recent application logs
okteto logs <service> --since 10m -n "$ns"

# If that's not enough context
okteto logs <service> --tail 200 -n "$ns"
```

**Look for:**
- Stack traces or `panic:` lines — note the source file and line number
- Connection refused / timeout errors to dependencies — service is up but a downstream is not
- HTTP 5xx errors logged by a middleware or proxy
- "address already in use" — port conflict inside the container

**Fix pattern:**
Quote the most relevant 5–10 lines of the stack trace or error. Identify the source file if named. Suggest the specific fix — a code change, a missing env var, or a dependent service that needs to be started.

---

### Deploy failure

The pods never appeared — `okteto deploy` failed before creating them.

```bash
# Check if the manifest is valid first
okteto validate

# Check deploy logs if validate passes
okteto logs --deploy -n "$ns"
```

**Look for:**
- `okteto validate` errors — YAML syntax, schema violations, missing required fields
- Helm template rendering errors in deploy logs
- Image build failures (Dockerfile errors, build context too large)

**Fix pattern:**
If `okteto validate` catches it, show the exact error and line. If it's a Helm error, show the template path. If it's a build error, show the Dockerfile stage that failed.

---

### Sync / dev mode issue

All pods are `Running` and `Ready`, but the developer's code changes aren't being reflected in the dev container.

`okteto status` reports the file-synchronization state of the active dev container. It only works while an `okteto up <service>` session is running — if there isn't one, there is nothing syncing; tell the user to start it.

```bash
okteto status -n "$ns"

# If the summary isn't enough, get syncthing troubleshooting links
okteto status --info -n "$ns"
```

**Look for:**
- `Sync status: error` or `Sync status: paused`
- File counts that aren't progressing
- A path in the sync output that doesn't match the actual source directory

The richest signal is the `okteto up` terminal itself — sync errors and conflict warnings surface there first, and you cannot see that session. Ask the user to paste its output.

**Fix pattern:**
Check the `sync` paths in `okteto.yaml` against the actual directory structure. If paths are correct, try `okteto down` followed by `okteto up <service>` (the user must run `okteto up` interactively — never run it yourself). If sync is stuck, `okteto doctor` will generate a diagnostic bundle.

---

## Output format

Always emit one block per unhealthy service:

```
## Diagnosis: <service-name>
**Root cause:** <one sentence>
**Evidence:**
<relevant excerpt from logs or describe output — 5 to 20 lines, no more>
**Fix:**
<exact command to run or code change to make>
**Confidence:** High / Medium / Low
```

Use **Low** confidence when:
- The container has only crashed once (no `--previous` logs available)
- The error message is ambiguous or missing
- Multiple possible root causes match the evidence

If all pods are healthy, report:
```
All services are Running and Ready. No obvious failures detected.

If you're still seeing issues, run `okteto doctor` to generate a full diagnostic bundle.
```

---

## Common gotchas

- **kubectl and okteto can disagree** — kubectl uses its own kubeconfig context, which may point at a different namespace or cluster than the Okteto context. If kubectl output doesn't match what `okteto` commands report, run `okteto kubeconfig` and re-check with `-n "$ns"` before drawing any conclusion.
- **`kubectl logs --previous` fails on first crash** — the container must have restarted at least once. Fall back to `kubectl logs` (current instance) or describe events.
- **Exit code 137 = OOM, not app error** — if you see `exit code: 137` in a CrashLoopBackOff, treat it as [OOM kill](#oom-kill-oomkilled), not a crash loop.
- **`Pending` pods don't have logs** — skip `kubectl logs` entirely and go straight to `kubectl describe pod` + `kubectl get events`.
- **`okteto logs` vs `kubectl logs`** — prefer `okteto logs` for application output; use `kubectl logs` when you need `--previous` or when the pod name is needed for `describe`.
- **Never run `okteto destroy`** as part of debugging — diagnose first. Only suggest teardown if the environment is unrecoverable and the user explicitly asks.
- **Never run `okteto up`** — it is interactive. If the fix requires re-entering dev mode, tell the user to run `okteto up <service>` in their terminal.
