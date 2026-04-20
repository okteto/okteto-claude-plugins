---
name: okteto
description: |
  Okteto development environment agent skill. Provides CLI knowledge, workflow
  patterns, and debugging strategies for working with Okteto environments.
  Supports both collaborative (human-in-the-loop) and autonomous (CI/ticket-driven)
  workflows. Use when a project has an okteto.yaml or the user mentions Okteto.
---

# Okteto Development Environment Skill

You are an AI agent working with an Okteto-powered development environment. This skill covers two modes of operation:

1. **Collaborative** -- a developer is actively working with you
2. **Autonomous** -- you are working independently (e.g., triggered by a ticket, PR, or CI pipeline)

## Step 1: Discover the project

Read `okteto.yaml` in the project root. This is the source of truth for:
- **build**: which services have container images
- **deploy**: how services are deployed (usually Helm charts)
- **dev**: which services support development mode, their images, sync paths, and commands
- **test**: which test containers are available and how they run

Parse this file to understand the project's services, languages, and structure. Do not assume hardcoded service names -- always derive them from `okteto.yaml`.

## Step 2: Determine your operating mode

**Collaborative mode** -- a developer is in the loop and will run interactive commands. Use this when:
- A user is chatting with you in an IDE or terminal
- Someone asks you to help debug, set up, or develop a service

**Autonomous mode** -- you are operating independently end-to-end. Use this when:
- Triggered by a ticket (Jira, Linear, GitHub Issue, etc.)
- Running as part of a CI/CD pipeline
- No human is expected to intervene during execution

---

## Collaborative mode

### Environment setup

1. **Check prerequisites**: Run `okteto version` and `okteto context show`
2. **Deploy**: Run `okteto deploy --wait` to build images and deploy all services
3. **Show endpoints**: Run `okteto endpoints` to display the public URLs
4. **Guide the user** to start development on a specific service with `okteto up <service>`

### The `okteto up` rule

**`okteto up` is interactive and MUST be run by the user in their terminal.** It opens a shell inside the development container with live file sync. Never run it yourself -- not as a background task, not with `&`, not at all. Instead, tell the user:

```
Run this in your terminal: okteto up <service>
```

### Working with the developer

Once the user has `okteto up <service>` running:

- **Run diagnostics**: `okteto exec -- <command>` to execute commands in the dev container
- **Read synced files**: Use the Read tool to examine code syncing to the cluster
- **Analyze pasted output**: When the user hits an error, they can paste terminal output
- **Check logs**: `okteto logs <service>` for container logs
- **Run tests**: `okteto test <test-name>` for test containers defined in okteto.yaml

You are facilitating their workflow, not trying to observe their terminal session.

### Debugging patterns

| Situation | Action |
|-----------|--------|
| User asks to run tests | `okteto exec -- make test` or language-appropriate command |
| User pastes an error | Read relevant code, analyze, suggest fix |
| User asks "why is this failing?" | Run diagnostics via `okteto exec` |
| User makes code changes | Changes auto-sync; help them run next steps |
| User asks to run e2e tests | `okteto test <test-name>` from okteto.yaml |

---

## Autonomous mode

When operating without a developer in the loop, you own the full lifecycle: environment setup, code changes, validation, and reporting. Do not use `okteto up` -- it is interactive and requires a human. Instead, use `okteto deploy` for full environments and `okteto test` for validation.

### Workflow

1. **Understand the task**: Read the ticket/issue to understand what needs to change and the acceptance criteria.

2. **Deploy an environment**:
   - Run `okteto context show` to verify cluster connection
   - Run `okteto deploy --wait` to spin up all services
   - Run `okteto endpoints` to capture the live URLs for later validation

3. **Make code changes**: Edit the relevant source files based on the task requirements. Use the Read tool, Grep, and Glob to explore the codebase. Inspect the service directories and `okteto.yaml` to understand service structure.

4. **Rebuild and redeploy changed services**:
   - Run `okteto build <service>` to rebuild only the changed service image
   - Run `okteto deploy --wait` to redeploy with the updated image
   - Alternatively, if only one service changed, target it: `okteto build <service> && okteto deploy --wait`

5. **Validate**:
   - If `okteto.yaml` was modified, run `okteto validate` first to catch manifest errors before deploying
   - Run `okteto test <test-name>` for each test container in okteto.yaml
   - Run `okteto endpoints` and use curl or similar to smoke-test the live endpoints
   - Check `okteto logs <service> --since 5m` for errors in the changed services

6. **Iterate if tests fail**:
   - Read test output and logs to diagnose the failure
   - Fix the code, rebuild, redeploy, and re-test
   - Repeat until all tests pass

7. **Report results**: Summarize what was changed, what tests passed, and provide the live environment URL for review. Include any relevant log output or test artifacts.

8. **Clean up**: Follow the rules in the [Cleanup and teardown](#cleanup-and-teardown) section below. Do not destroy without explicit authorization or a predefined cleanup policy.

### Autonomous example

```
Trigger: Jira ticket "PROJ-123: Add rate limiting to /api/rentals endpoint"

Agent actions:
  1. Read ticket for requirements and acceptance criteria
  2. okteto deploy --wait              -> full environment running
  3. Read okteto.yaml, explore api/ directory
  4. Edit api/handlers/rentals.go      -> implement rate limiting
  5. Edit api/handlers/rentals_test.go  -> add unit tests
  6. okteto build api                  -> rebuild the api service image
  7. okteto deploy --wait              -> redeploy with changes
  8. okteto test e2e                   -> run e2e test suite
  9. okteto logs api --since 5m        -> check for runtime errors
  10. curl the live endpoint to verify rate limiting behavior
  11. Commit changes, open PR
  12. Report back to PROJ-123: changes made, tests passing, PR link, live URL
```

---

## Cleanup and teardown

Tearing down an environment is as important as standing one up. Get the command right, and get the authorization right.

### Pick the right command

| Command | What it does | When to use |
|---------|--------------|-------------|
| `okteto down` | Exits dev mode for one service; restores the original deployment. **Does not destroy the environment.** | The developer is done iterating on a service but wants the environment to keep running. |
| `okteto destroy` | Tears down every resource created by `okteto deploy` in the current namespace. **Destructive.** | The environment is no longer needed and teardown is authorized. |
| `okteto namespace delete <name>` | Deletes an entire namespace and everything in it. **Very destructive.** | Only with explicit user instruction — never as cleanup from a task. |

A common mistake is reaching for `okteto destroy` when the user only wanted to exit dev mode. If in doubt, `okteto down` is the safe choice.

### Collaborative mode

Do not run `okteto destroy` yourself. Surface it as a suggestion and let the developer run it:

```
You're done with this environment. To tear it down, run:
  okteto destroy
```

`okteto down` is fine for the agent to run when the developer has clearly finished with a service.

### Autonomous mode

Run `okteto destroy` only when one of these is true:

- The task explicitly authorizes cleanup (e.g., "destroy the environment when the PR is merged")
- There is a predefined cleanup policy documented in the repo's `CLAUDE.md` or the ticket
- The environment is ephemeral and owned by the pipeline (e.g., a per-run preview environment)

If none of those apply, leave the environment running and note in the report that it is still up, with the command the caller would use to tear it down. It is always safer to leave a running environment than to destroy one that someone else depended on.

### Never do this

- Delete a namespace you did not create
- Destroy a shared or named environment (e.g., `staging`, `dev`) without explicit instruction
- Treat `okteto destroy` as a recovery step when something goes wrong — diagnose first

---

## Discovering dev commands

Look at the `dev` section of `okteto.yaml` for each service. The `command` field tells you how the service starts:

- If `command: bash` -- the service needs manual build/start (check for Makefile, package.json, pom.xml in the service directory)
- If `command: yarn start` or `command: mvn spring-boot:run` -- the service auto-starts in dev mode
- Check for `Makefile`, `package.json`, `pom.xml`, or `go.mod` in the service directory to determine available commands

## CLI quick reference

| Command | Collaborative | Autonomous | Purpose |
|---------|:---:|:---:|---------|
| `okteto deploy --wait` | Agent | Agent | Build images and deploy all services |
| `okteto build <service>` | Agent | Agent | Build and push a single service image |
| `okteto up <service>` | **User only** | **Never** | Start interactive dev container |
| `okteto down` | Agent/User | N/A | Stop dev mode, restore deployment |
| `okteto exec -- <cmd>` | Agent | N/A | Run command in active dev container |
| `okteto logs <service>` | Agent | Agent | View container logs |
| `okteto endpoints` | Agent | Agent | List public URLs |
| `okteto test <name>` | Agent | Agent | Run a test container from okteto.yaml |
| `okteto destroy` | User | With policy | Tear down all resources |
| `okteto doctor` | Agent | Agent | Generate a diagnostic bundle |
| `okteto status` | Agent | N/A | Check file sync progress |
| `okteto validate` | Agent | Agent | Validate okteto.yaml manifest syntax |
| `okteto context show` | Agent | Agent | Verify cluster and namespace |

## Common mistakes to avoid

- **Running `okteto up` in autonomous mode**: There is no human to interact with the shell. Use `okteto deploy` + `okteto build` + `okteto test` instead.
- **Running `okteto up` as the agent in collaborative mode**: It is interactive. Always tell the user to run it.
- **Forgetting to deploy first**: Run `okteto deploy` before any validation or testing.
- **Not specifying the service**: With multiple services, always specify which one.
- **Using kubectl/helm directly**: Always use `okteto deploy` so Okteto can track resources.
- **Building Docker images locally**: Use `okteto build` to leverage the Okteto Build Service.
- **Hardcoding service names**: Always read `okteto.yaml` to discover services.
- **Destroying without authorization**: In autonomous mode, do not run `okteto destroy` unless there is an explicit cleanup policy or instruction.
