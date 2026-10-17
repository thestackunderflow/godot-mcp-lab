"""Spike 4: the closed loop headless. Play the level from the editor, press jump, read the player's position over time."""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import mcp_client as mc  # noqa: E402
mc.TIMEOUT_S = 30

OUT = os.path.join(mc.OUT, "spike4")
os.makedirs(OUT, exist_ok=True)
log = []


def call(name, args):
    print("->", name, flush=True)
    r = m.call_tool(name, args)
    log.append({"tool": name, "args": args, "isError": r.get("isError"), "text": m.text(r)[:1500],
                "structured": r.get("structuredContent")})
    return r


print("start server", flush=True)
m = mc.McpClient(mc.SERVER_CMD)
m.start()
print("server up", flush=True)
editor = subprocess.Popen(["godot", "--headless", "--editor", "--path", "/work/game"],
                          stdout=open(os.path.join(OUT, "editor.log"), "w"), stderr=subprocess.STDOUT)
for i in range(60):
    time.sleep(1)
    print("health", i, flush=True)
    if (m.call_tool("godot_health_check", {}).get("structuredContent") or {}).get("bridge_connected"):
        break
for ts in ("runtime", "input"):
    call("godot_enable_toolset", {"category": ts})
call("godot_runtime_run_and_capture", {"timeout_seconds": 3})
call("godot_runtime_play_scene", {})
time.sleep(4)
call("godot_runtime_is_playing", {})
call("godot_runtime_get_game_scene_tree", {})
call("godot_runtime_read_property", {"node_path": "/root/Level/Player", "property": "position"})
call("godot_runtime_monitor_property", {"node_path": "/root/Level/Player", "property": "position", "samples": 40})
call("godot_input_simulate_action", {"action": "jump", "pressed": True})
time.sleep(0.2)
call("godot_input_simulate_action", {"action": "jump", "pressed": False})
time.sleep(2)
call("godot_runtime_get_property_samples", {})
call("godot_input_get_stats", {})
call("godot_runtime_get_game_output", {})
call("godot_runtime_capture_game_screenshot", {})
call("godot_runtime_stop_scene", {})
with open(os.path.join(OUT, "log.json"), "w", encoding="utf-8") as f:
    json.dump(log, f, indent=1, ensure_ascii=False)
m.close()
editor.terminate()
for e in log:
    print(e["tool"], "ERR" if e["isError"] else "ok", e["text"][:220].replace("\n", " | "))
