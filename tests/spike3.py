"""Spike 3: the full tool surface (enable every toolset), list_changed notifications, and the runtime/input tools."""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import mcp_client as mc  # noqa: E402

OUT = os.path.join(mc.OUT, "spike3")
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

counts = {}
wrong = m.call_tool("godot_enable_toolset", {"toolset": "runtime"})
dump("wrong_argument.json", wrong)
n0 = len(m.notifications)
first = m.call_tool("godot_enable_toolset", {"category": "runtime"})
dump("enable_runtime.json", first)
dump("notifications_after_first_enable.json", m.notifications[n0:])
names = json.loads(m.text(m.call_tool("godot_list_toolsets", {})))
for ts in [t["name"] for t in names]:
    r = m.call_tool("godot_enable_toolset", {"category": ts})
    counts[ts] = len(m.request("tools/list", {})["tools"])
all_tools = m.request("tools/list", {})["tools"]
dump("tools_all.json", all_tools)
summary = {"tools_all": len(all_tools), "chars_all": len(json.dumps(all_tools, separators=(",", ":"))), "cumulative_counts": counts,
           "notifications_seen": len(m.notifications), "notification_methods": sorted({n["method"] for n in m.notifications})}
dump("summary.json", summary)
dump("runtime_input_tools.txt", "\n".join(f"{t['name']}: {t.get('description','')[:160]}" for t in all_tools
                                          if any(k in t["name"] for k in ("run", "input", "play", "runtime", "screenshot", "simulate", "test"))) + "\n")
m.close()
editor.terminate()
print(json.dumps({k: v for k, v in summary.items() if k != "cumulative_counts"}))
