# Okteto Development Environment

This project uses [Okteto](https://www.okteto.com) for cloud development environments. When a developer asks you to make a change, test something, or interact with the running environment, use the instructions below.

## Step 1: Discover the project

Read `okteto.yaml` in the project root. This is the source of truth for:

- **build**: which services have container images
- **deploy**: how services are deployed to the cluster
- **dev**: which services support development mode, their sync paths, and startup commands
- **test**: which test containers are available and their commands

Always derive service names from `okteto.yaml`. Never hardcode them.

## Step 2: Discover how to run commands for each service

Look at the `dev` section of `okteto.yaml` for each service. The `command` field tells you how the service starts inside the dev container:

- `command: bash` — the service needs manual build/start steps; check the service directory for a `Makefile`, `package.json`, `pom.xml`, or `go.mod` to find available commands
- `command: yarn start` or `command: mvn spring-boot:run` — the service auto-starts in dev mode; use the same runner for tests (`yarn test`, `mvn test`, etc.)

When a developer asks you to run tests or build a service and you're not sure what command to use, check these files in the service directory before guessing.

## Step 3: Running commands in the dev environment

When a developer has `okteto up <service>` running in their terminal, use `okteto exec` to run commands inside the dev container:

```
okteto exec -- <command>
```

Examples:
- `okteto exec -- go test ./...`
- `okteto exec -- npm test`
- `okteto exec -- make test`
- `okteto exec -- curl localhost:8080/health`

**Do not use `kubectl exec` or try to open a shell directly into a pod.** `okteto exec` is the correct way to run commands in the development container — it handles cluster authentication, namespace selection, and dev container routing automatically. Direct `kubectl exec` calls will not reach the right container and will confuse the session.

## The `okteto up` rule

`okteto up <service>` is **interactive** — it starts a live shell inside the dev container with automatic file sync. You must never run it yourself (not in the terminal, not in the background). It will hang waiting for input.

Instead, tell the developer:

> Run this in your terminal: `okteto up <service>`

Once they confirm it's running, you can use `okteto exec` freely.

## Common workflows

### Setting up the environment

1. Run `okteto version` to confirm the CLI is installed
2. Run `okteto context show` to confirm the cluster connection
3. Run `okteto deploy --wait` to build images and deploy all services
4. Run `okteto endpoints` to show the live URLs
5. Ask which service the developer wants to work on, then tell them to run `okteto up <service>` in their terminal

### Making a change and testing it in Okteto

1. Read the relevant source files and make the requested change
2. If the developer has `okteto up <service>` running, file changes sync automatically — no rebuild needed for interpreted languages
3. Run `okteto exec -- <test command>` to validate the change in the live container
4. Share the output with the developer

If you're unsure whether `okteto up` is running, ask the developer before using `okteto exec`.

### Rebuilding after a change that requires a new image

For changes that affect compiled binaries, new dependencies, or the Dockerfile itself:

1. `okteto build <service>` — rebuilds and pushes the service image using the Okteto Build Service
2. `okteto deploy --wait` — redeploys with the updated image

Do not build Docker images locally. Use `okteto build` to leverage the remote build service.

### Changing `okteto.yaml`

If you modify `okteto.yaml`, always run `okteto validate` before deploying:

1. `okteto validate` — checks the manifest for syntax and schema errors
2. Fix any errors before continuing
3. `okteto deploy --wait` — deploy with the updated manifest

Never deploy a modified `okteto.yaml` without validating first — a bad manifest will fail mid-deploy and leave the environment in a broken state.

### Checking what's wrong

| Situation | What to do |
|-----------|------------|
| Service not responding | `okteto logs <service>` |
| Need to inspect state | `okteto exec -- <diagnostic command>` |
| Tests failing | Read test output, fix code, re-run with `okteto exec` |
| Environment looks stale | `okteto deploy --wait` to redeploy |
| Persistent unexplained failure | `okteto doctor` — generates a diagnostic bundle to share with Okteto support |

## Autonomous mode

When operating without a developer in the loop (e.g. triggered by a ticket or PR), own the full lifecycle. Do not use `okteto up` — it requires a human. Use `okteto deploy` for environments and `okteto test` for validation.

1. Run `okteto context show` to verify the cluster connection
2. Run `okteto deploy --wait` to spin up all services
3. Run `okteto endpoints` to capture live URLs
4. Make the code changes
5. If `okteto.yaml` was modified, run `okteto validate` before proceeding
6. Run `okteto build <service>` and `okteto deploy --wait` to redeploy changed services
7. Run `okteto test <name>` for each test container defined in `okteto.yaml`
8. Check `okteto logs <service> --since 5m` for runtime errors
9. Iterate: fix, rebuild, redeploy, re-test until passing
10. Commit changes, open a PR, and report results (changes made, tests passing, live URL)

Do not run `okteto destroy` unless there is an explicit cleanup policy or instruction.

## CLI reference

| Command | Who runs it | Purpose |
|---------|-------------|---------|
| `okteto deploy --wait` | Agent | Build images and deploy all services |
| `okteto build <service>` | Agent | Rebuild a single service image |
| `okteto up <service>` | **Developer only** | Start interactive dev mode with file sync |
| `okteto exec -- <cmd>` | Agent | Run a command in the active dev container |
| `okteto logs <service>` | Agent | View container logs |
| `okteto endpoints` | Agent | List public URLs for running services |
| `okteto test <name>` | Agent | Run a test container defined in okteto.yaml |
| `okteto down` | Agent or developer | Stop dev mode, restore the deployment |
| `okteto doctor` | Agent | Generate a diagnostic bundle for Okteto support |
| `okteto context show` | Agent | Verify cluster connection and active namespace |
| `okteto validate` | Agent | Validate okteto.yaml syntax before deploying |
| `okteto destroy` | Developer only | Tear down all resources — requires explicit instruction |

## Mistakes to avoid

- **Running `okteto up` yourself**: It is interactive and will hang. The developer must run it in their terminal.
- **Using `kubectl exec` or direct pod shells**: These bypass Okteto's dev container routing. Use `okteto exec -- <command>` instead.
- **Building Docker images with `docker build`**: Use `okteto build <service>` to use the Okteto Build Service.
- **Using `kubectl apply` or `helm upgrade` directly**: Use `okteto deploy` so Okteto can track resources.
- **Hardcoding service names**: Always read `okteto.yaml` to discover them.
- **Running `okteto destroy` without being asked**: It tears down everything. Only run it if the developer explicitly asks.
