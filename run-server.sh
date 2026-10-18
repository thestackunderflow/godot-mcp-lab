#!/usr/bin/env bash
# Start everything one MCP session needs, inside the lab container, then run the MCP server on stdin/stdout:
#   Xvfb (a virtual screen, so the game can open a window without a GPU)
#   the Godot editor, headless, on the lab's game project (its add-on connects out to the server's bridge)
#   godot-editor-mcp on stdio (the MCP server; it listens for the editor on ws://127.0.0.1:9080)
# When the server exits (the client closes stdin), the editor, any game it started and Xvfb are stopped too, so
# the next session gets a free bridge port. Used by tests/test_lab.py and by the real Claude Code run.
set -uo pipefail
GAME="${GAME:-/work/game}"
LOGS="${LOGS:-/tmp}"
DISP="${DISP:-99}"
# The editor add-on is not committed (game/addons/ is git-ignored): install it from the pinned release zip the image
# downloaded and checksummed (/opt/godot_mcp_addon.zip), so a fresh clone works. Same 106 files as the lab's original run.
if [ ! -f "$GAME/addons/godot_mcp/plugin.cfg" ]; then
  python3 -c "import zipfile,sys; zipfile.ZipFile('/opt/godot_mcp_addon.zip').extractall(sys.argv[1])" "$GAME" \
    || { echo "could not install the add-on from /opt/godot_mcp_addon.zip" >&2; exit 1; }
fi
Xvfb ":$DISP" -screen 0 1280x720x24 >"$LOGS/xvfb.log" 2>&1 &
XVFB=$!
export DISPLAY=":$DISP"
godot --headless --editor --path "$GAME" >"$LOGS/editor.log" 2>&1 &
EDITOR=$!
cleanup() { pkill -P "$EDITOR" 2>/dev/null; kill "$EDITOR" "$XVFB" 2>/dev/null; wait 2>/dev/null; }
trap cleanup EXIT
# WAIT_EDITOR=<seconds>: give the editor a head start, like a desktop where Godot is already open before the agent
# starts (the add-on reconnects to the bridge on its own once the server is up). The tests poll instead (unset).
sleep "${WAIT_EDITOR:-0}"
godot-editor-mcp
