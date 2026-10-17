#!/usr/bin/env bash
# One real, logged, headless Claude Code session against the live Godot editor, using the brief's prompts.
#   Claude Code --stdio--> docker run -i [mcp_log_proxy.py --stdio--> run-server.sh: Xvfb + headless editor + godot-editor-mcp]
# Clean recipe: only the godot MCP tools (no built-in file tools, so every change goes through the editor), no personal
# CLAUDE.md, no user settings. The game is a disposable copy (claude-run/work/game). Between prompts 4 and 5 the brief's
# planted bug replaces scripts/player.gd (disclosed in the video).
set -uo pipefail
cd "$(dirname "$0")/.."
LAB="$(pwd -W 2>/dev/null || pwd)"
OUT=tests/out/${RUN_DIR:-claude-run}
rm -rf "$OUT" claude-run/work && mkdir -p "$OUT" claude-run/work
cp -r game claude-run/work/game && rm -rf claude-run/work/game/.godot
(cd claude-run/work && git init -q && git add -A && git -c user.name=lab -c user.email=lab@localhost commit -qm "start")

cat > claude-run/mcp-godot.json <<JSON
{ "mcpServers": { "godot": {
  "command": "docker",
  "args": ["run", "-i", "--rm", "--init",
           "-v", "$LAB:/work", "-e", "GAME=/work/claude-run/work/game", "-e", "LOGS=/work/$OUT",
           "godot-mcp-lab:4.7.2",
           "python3", "/work/proxy/mcp_log_proxy.py", "--log", "/work/$OUT/godot-mcp.jsonl", "--png-dir", "/work/$OUT",
           "--", "/work/run-server.sh"] } } }
JSON

SESSION=$(python -c 'import uuid; print(uuid.uuid4())')
echo "$SESSION" > "$OUT/session-id.txt"
CLAUDE="${CLAUDE:-claude}"
run() {   # run <n> <prompt> <--session-id|--resume>
  echo "{\"prompt\": $1, \"started\": \"$(date -u +%FT%TZ)\"}" >> "$OUT/timeline.jsonl"
  (cd claude-run/work && MSYS_NO_PATHCONV=1 timeout 1200 "$CLAUDE" -p "$2" "$3" "$SESSION" \
     --setting-sources project,local --settings '{"claudeMdExcludes":["**/.claude/CLAUDE.md"],"autoMemoryEnabled":false}' \
     --mcp-config "$LAB/claude-run/mcp-godot.json" --strict-mcp-config \
     --tools "" --allowedTools "mcp__godot" --permission-mode dontAsk --max-budget-usd 3 \
     --output-format stream-json --verbose < /dev/null) > "$OUT/prompt-$1.stream.jsonl" 2> "$OUT/prompt-$1.stderr.txt"
  echo "{\"prompt\": $1, \"exit\": $?, \"ended\": \"$(date -u +%FT%TZ)\"}" >> "$OUT/timeline.jsonl"
  (cd claude-run/work && git add -A && git -c user.name=lab -c user.email=lab@localhost commit -qm "after prompt $1" >/dev/null 2>&1; git show --stat HEAD > "../../$OUT/after-prompt-$1.stat.txt" 2>&1; git diff HEAD~1 HEAD -- . ':!*.uid' > "../../$OUT/after-prompt-$1.diff" 2>&1)
}

P1='Is Godot connected? Inspect the current project and scene tree. Do not modify anything yet. Summarize what you can see.'
P2='Enable the necessary scene-editing tools. Add a Label to the current level that says "Collect 3 coins". Place it at the top-left with readable sizing. Save the scene. Tell me exactly what you changed.'
P3='Inspect the existing player controller first. Add a double-jump feature using the project'"'"'s existing jump input. The player should get exactly one extra jump while airborne, and the ability should reset after landing. Preserve the existing movement behavior. Validate the script before running the game.'
P4='Run the project. Test the player'"'"'s jump and double jump. Use runtime inspection, input simulation, or screenshots if available. Do not claim success unless you have evidence that the second jump occurs and a third airborne jump is blocked.'
P5='The double jump works after a normal first jump, but fails when the player walks off a platform and then presses jump in mid-air. Reproduce the problem, inspect the relevant state, identify the cause, fix it, and verify the behavior again.'
P6='Explain which Godot MCP tools you used, what evidence each tool gave you, and which part of the task could not have been verified from source files alone.'

run 1 "$P1" --session-id
run 2 "$P2" --resume
run 3 "$P3" --resume
run 4 "$P4" --resume
cp fix/player_planted_bug.gd claude-run/work/game/scripts/player.gd       # the brief's prepared bug branch
(cd claude-run/work && git add -A && git -c user.name=lab -c user.email=lab@localhost commit -qm "planted bug (lab)" >/dev/null)
run 5 "$P5" --resume
run 6 "$P6" --resume
echo done
