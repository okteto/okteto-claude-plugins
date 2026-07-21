---
description: Guided Okteto environment setup — verify prerequisites, deploy all services, show endpoints, and hand off into dev mode
---

Set up the Okteto development environment for this project. Follow these steps:

1. **Check for the manifest**:
   - Run `ls okteto.yaml okteto.yml 2>/dev/null` to verify a manifest exists
   - If neither file exists, stop and tell the user:
     > "There's no `okteto.yaml` in this repo. The `okteto-onboarding` skill walks you through creating one. Want me to invoke it?"
   - Do not proceed with the rest of `dev-setup` until a manifest is in place

2. **Discover the project**: Read `okteto.yaml` in the project root to understand services, build targets, and dev configurations.

3. **Check prerequisites**:
   - Run `okteto version` to confirm the CLI is installed
   - Run `okteto context show` to confirm the user is connected to an Okteto instance (note the active namespace it reports)
   - If either fails, stop and help the user install/configure Okteto

   **Worktree check:** if this checkout is a git worktree (`git rev-parse --git-common-dir` differs from `git rev-parse --git-dir`, or it shows in `git worktree list`), give it its own namespace so it doesn't collide with the other worktrees:
   - Derive a name from the branch: `ns=$(git branch --show-current | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g; s/^-*//; s/-*$//' | cut -c1-50)`
   - Create it: `okteto namespace create <ns>`
   - For the rest of this setup, **append `-n <ns>` to every `okteto` command below** (`deploy`, `endpoints`, `up`). Do not use `okteto namespace use` — the `-n` flag is safe when several worktrees run at once. A single non-worktree checkout can skip this and use the default namespace.

4. **Validate the manifest**:
   - Run `okteto validate` to check `okteto.yaml` for syntax and schema errors
   - If it fails, show the error and help the user fix the manifest before proceeding

5. **Deploy all services**:
   - Run `okteto deploy --wait`
   - This builds images and deploys all services defined in okteto.yaml
   - Wait for it to complete successfully

6. **Show the running environment**:
   - Run `okteto endpoints` to display the public URLs
   - Share the URLs with the user so they can open the app in their browser

7. **Guide the user to start development**:
   - List the services available for development (from the `dev` section of `okteto.yaml`)
   - Ask which service they want to work on
   - Tell them to run `okteto up <service>` **in their terminal** (this is interactive -- do not run it yourself); if you created a worktree namespace in step 3, tell them to run `okteto up <service> -n <ns>`
   - Once they confirm it's running, check the service directory for build/run commands (Makefile, package.json, pom.xml, etc.) and share the relevant ones

8. **Confirm readiness**:
   - Let the user know you can now help with: running tests (`okteto exec -- <cmd>`), debugging errors, reading code, and analyzing logs (`okteto logs <service>`)
