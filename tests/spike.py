"""Spike (exploration before the tests): can a headless Godot editor connect to the MCP server, and what's exposed?
Writes tests/out/spike/. Run in the lab image: python3 tests/spike.py"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import mcp_client as mc  # noqa: E402

OUT = os.path.join(mc.OUT, "spike")
os.makedirs(OUT, exist_ok=True)


def dump(name, obj):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(obj if isinstance(obj, str) else json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


m = mc.McpClient(mc.SERVER_CMD)
init = m.start()
dump("initialize.json", init)
tools0 = m.request("tools/list", {})["tools"]
dump("tools_default.json", tools0)
dump("tools_default_names.txt", "\n".join(t["name"] for t in tools0) + "\n")

editor = subprocess.Popen(["godot", "--headless", "--editor", "--path", "/work/game"],
                          stdout=open(os.path.join(OUT, "editor.log"), "w"), stderr=subprocess.STDOUT)
status = None
for i in range(60):
    time.sleep(2)
    try:
        names = [t["name"] for t in tools0]
        probe = next((n for n in names if "status" in n or "health" in n or "connection" in n), None)
        r = m.call_tool(probe, {}) if probe else None
        status = {"tool": probe, "reply": r, "after_s": (i + 1) * 2}
        if r and (r.get("structuredContent") or {}).get("bridge_connected") is True:
            break
    except Exception as e:  # keep trying while the editor boots
        status = {"error": str(e), "after_s": (i + 1) * 2}
dump("status.json", status)

tree = None
for n in ("godot_inspection_get_scene_tree",):
    try:
        tree = m.call_tool(n, {})
    except Exception as e:
        tree = {"error": str(e)}
dump("scene_tree.json", tree)
dump("notifications.json", m.notifications)
dump("server_stderr.txt", "\n".join(m.stderr_text()))
m.close()
editor.terminate()
print(json.dumps({"tools_default": len(tools0), "status": status and status.get("tool"), "after_s": status and status.get("after_s")}))
