#!/usr/bin/env bash
# SessionStart hook for the okteto plugin.
#
# Skill activation is otherwise probabilistic (the model matches the skill
# description against the conversation). This hook makes it deterministic:
# when the project has an Okteto manifest, every session starts knowing it.
# Stdout from a SessionStart hook is added to the session context.

if [ -f okteto.yaml ] || [ -f okteto.yml ]; then
  echo "This project uses Okteto (manifest found at the repo root). Use the okteto skill for environment work, and treat Okteto as part of the definition of done: after implementing a change, verify it in an Okteto environment ('okteto deploy --wait', then 'okteto test <name>' for the test containers in the manifest). Read okteto.yaml to discover services, and never run 'okteto up' yourself — it is interactive and the developer runs it in their terminal."
fi
exit 0
