Set up the Okteto development environment for this project. Follow these steps:

1. **Discover the project**: Read `okteto.yaml` in the project root to understand services, build targets, and dev configurations.

2. **Check prerequisites**:
   - Run `okteto version` to confirm the CLI is installed
   - Run `okteto context show` to confirm the user is connected to an Okteto instance
   - If either fails, stop and help the user install/configure Okteto

3. **Deploy all services**:
   - Run `okteto deploy --wait`
   - This builds images and deploys all services defined in okteto.yaml
   - Wait for it to complete successfully

4. **Show the running environment**:
   - Run `okteto endpoints` to display the public URLs
   - Share the URLs with the user so they can open the app in their browser

5. **Guide the user to start development**:
   - List the services available for development (from the `dev` section of `okteto.yaml`)
   - Ask which service they want to work on
   - Tell them to run `okteto up <service>` **in their terminal** (this is interactive -- do not run it yourself)
   - Once they confirm it's running, check the service directory for build/run commands (Makefile, package.json, pom.xml, etc.) and share the relevant ones

6. **Confirm readiness**:
   - Let the user know you can now help with: running tests (`okteto exec -- <cmd>`), debugging errors, reading code, and analyzing logs (`okteto logs <service>`)
