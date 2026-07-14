Debug the current Okteto environment and identify root causes for any unhealthy services.

## Instructions

1. **Parse the argument** (if provided):
   - If the user gave a service name (e.g. `/debug-env catalog`), scope the entire investigation to that service only.
   - If no argument was given, check all services in the current namespace.

2. **Run the full triage algorithm** from the okteto-debugging skill:
   - Verify connectivity with `okteto context show`
   - Read `okteto.yaml` to get the canonical service list
   - Run `kubectl get pods` to snapshot pod states
   - Apply the matching playbook for each unhealthy pod state

3. **Emit one diagnosis block per unhealthy service:**

   ```
   ## Diagnosis: <service-name>
   **Root cause:** <one sentence>
   **Evidence:**
   <relevant log or describe excerpt — 5 to 20 lines>
   **Fix:**
   <exact command or code change>
   **Confidence:** High / Medium / Low
   ```

4. **If all services are healthy**, report that clearly and suggest `okteto doctor` for deeper diagnostics.

5. **Do not run any write operations** — this command is read-only. Never run `okteto destroy`, `okteto build`, or `okteto deploy` as part of this command. Diagnose only; propose fixes for the user to run.
