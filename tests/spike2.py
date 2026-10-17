"""Spike 2: toolsets, what enabling one does on the wire, and whether the game can run and take input headless."""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import mcp_client as mc  # noqa: E402

OUT = os.path.join(mc.OUT, "spike2")
os.makedirs(OUT, exist_ok=True)


def dump(name, obj):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(obj if isinstance(obj, str) else json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


m = mc.McpClient(mc.SERVER_CMD)
m.start()
editor = subprocess.Popen(["godot", "--headless", "--editor", "--path", "/work/game"],
                          stdout=open(os.path.join(OUT, "editor.log"), "w"), stderr=subprocess.STDOUT)
for _ in range(60):
    time.sleep(1)
    if (m.call_tool("godot_health_check", {}).get("structuredContent") or {}).get("bridge_connected"):
        break

dump("toolsets.json", m.call_tool("godot_list_toolsets", {}))
dump("safety_classes.json", m.call_tool("godot_list_tools_by_safety_class", {}))
dump("server_info.json", m.call_tool("godot_get_server_info", {}))
before = len(m.request("tools/list", {})["tools"])
n0 = len(m.notifications)
en = m.call_tool("godot_enable_toolset", {"toolset": "runtime"})
dump("enable_runtime.json", en)
after_tools = m.request("tools/list", {})["tools"]
dump("tools_after_runtime.txt", "\n".join(t["name"] for t in after_tools) + "\n")
dump("notifications_after_enable.json", m.notifications[n0:])
summary = {"tools_before": before, "tools_after_runtime": len(after_tools)}
# try every toolset to count the full surface
ts = m.call_tool("godot_list_toolsets", {})
dump("summary.json", summary)
dump("server_stderr.txt", "\n".join(m.stderr_text()))
m.close()
editor.terminate()
print(json.dumps(summary))
