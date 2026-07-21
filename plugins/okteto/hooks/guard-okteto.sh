#!/usr/bin/env bash
# PreToolUse guard for the okteto plugin.
#
# The okteto skill teaches two hard rules; this hook enforces them mechanically
# so a session can't wedge even if the model forgets:
#
#   1. `okteto up` is interactive and hangs a non-interactive shell. Deny it
#      and redirect the agent to hand the command to the developer.
#   2. `okteto destroy` / `okteto namespace delete` are destructive. Require
#      user confirmation, unless the environment pre-authorizes teardown by
#      setting OKTETO_ALLOW_AGENT_DESTROY=1|true (the "explicit cleanup
#      policy" case from the skill, e.g. a pipeline-owned preview env).
#
# Fails open: on any parse problem the command is allowed, so this hook can
# never break a session. It only ever tightens `okteto` invocations.

input=$(cat)

if command -v jq >/dev/null 2>&1; then
  cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null)
else
  # Crude fallback when jq is unavailable: pull the first "command" value out
  # of the raw JSON. Best effort only — the fail-open default covers the rest.
  cmd=$(printf '%s' "$input" | sed -n 's/.*"command"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
fi

[ -n "$cmd" ] || exit 0

emit() { # $1 = permissionDecision, $2 = reason (no double quotes allowed)
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"%s","permissionDecisionReason":"%s"}}\n' "$1" "$2"
  exit 0
}

# Help output is harmless — let usage lookups through.
case "$cmd" in
  *--help*|*" -h"*) exit 0 ;;
esac

if printf '%s' "$cmd" | grep -qE 'okteto[[:space:]]+up([[:space:]]|$)'; then
  emit deny "okteto up is interactive and will hang the agent. Tell the developer to run it in their terminal instead: okteto up <service> (append -n <ns> when using an isolated worktree namespace). In autonomous mode use okteto deploy / okteto build / okteto test."
fi

if printf '%s' "$cmd" | grep -qE 'okteto[[:space:]]+(destroy([[:space:]]|$)|namespace[[:space:]]+delete)'; then
  case "$OKTETO_ALLOW_AGENT_DESTROY" in
    1|true) exit 0 ;;
  esac
  emit ask "Destructive okteto command. Per the okteto skill cleanup rules, teardown needs explicit authorization: the developer confirms it, or the environment sets OKTETO_ALLOW_AGENT_DESTROY=1 (e.g. a pipeline that owns its preview environment)."
fi

exit 0
