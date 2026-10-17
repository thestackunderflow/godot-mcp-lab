"""Godot MCP lab: what the community godot-editor-mcp server hands an AI agent, and whether its closed loop
(inspect -> edit -> run -> press keys -> observe) really works. Run in the lab image: docker compose run --rm tests

Each session starts run-server.sh (Xvfb + headless Godot editor + MCP server) on a fresh copy of game/ with a
chosen player script, so tests never change the committed project. Every reply is saved in tests/out/."""
import base64
import json
import os
import shutil
import time

import pytest

import mcp_client as mc

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = mc.OUT
mc.TIMEOUT_S = 60


def save(name, obj):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(obj if isinstance(obj, str) else json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


class Session:
    """One MCP session on a fresh copy of the game, with `player` as scripts/player.gd."""
    n = 0

    def __init__(self, tag, player=None):
        self.dir = f"/tmp/game-{tag}"
        shutil.rmtree(self.dir, ignore_errors=True)
        shutil.copytree(os.path.join(ROOT, "game"), self.dir, ignore=shutil.ignore_patterns(".godot"))
        if player:
            shutil.copy(os.path.join(ROOT, "fix", player), os.path.join(self.dir, "scripts", "player.gd"))
        os.environ["GAME"] = self.dir
        Session.n += 1
        os.environ["DISP"] = str(100 + Session.n)
        os.environ["LOGS"] = os.path.join(OUT, f"logs-{tag}")
        os.makedirs(os.environ["LOGS"], exist_ok=True)
        self.m = mc.McpClient([os.path.join(ROOT, "run-server.sh")])
        self.m.start()
        for _ in range(90):
            time.sleep(1)
            if (self.m.call_tool("godot_health_check", {}).get("structuredContent") or {}).get("bridge_connected"):
                return
        raise mc.McpError("the editor never connected to the bridge")

    def call(self, name, args=None):
        return self.m.call_tool(name, args or {})

    def data(self, name, args=None):
        r = self.call(name, args)
        assert not r.get("isError"), f"{name}: {mc.McpClient.text(r)[:400]}"
        return r.get("structuredContent") or json.loads(mc.McpClient.text(r))

    def enable(self, *toolsets):
        for t in toolsets:
            self.data("godot_enable_toolset", {"category": t})

    def close(self):
        try:
            self.call("godot_runtime_stop_scene")
        except Exception:
            pass
        self.m.close()


@pytest.fixture(scope="class")
def s():
    sess = Session("main")
    yield sess
    sess.close()


class TestEditorSession:
    """Tests 0-5: one editor session."""

    def test_0_versions(self, s):
        info = s.data("godot_health_check")
        init = s.m.init_result
        save("00_versions.json", {"godot": os.popen("godot --headless --version").read().strip(), "health": info,
                                  "initialize_serverInfo": init.get("serverInfo"), "protocol": init.get("protocolVersion"),
                                  "pip": [l for l in open("/opt/pip-freeze.txt") if l.lower().startswith(("godot-editor-mcp", "fastmcp", "mcp=="))]})
        assert info["version"] == "2026.10.15" and info["addon_version"] == "2026.10.15" and info["bridge_connected"] is True


    def test_1_gated_surface(self, s):
        """Default: core + inspection only. Every toolset enabled: the full surface. Each enable announces itself."""
        default = s.m.request("tools/list", {})["tools"]
        toolsets = json.loads(mc.McpClient.text(s.call("godot_list_toolsets")))
        n0 = len(s.m.notifications)
        s.enable(*[t["name"] for t in toolsets if not t["enabled"]])
        full = s.m.request("tools/list", {})["tools"]
        notes = s.m.notifications[n0:]
        summary = {"toolsets": len(toolsets), "enabled_by_default": [t["name"] for t in toolsets if t["enabled"]],
                   "default_tools": len(default), "default_chars": len(json.dumps(default, separators=(",", ":"))),
                   "all_tools": len(full), "all_chars": len(json.dumps(full, separators=(",", ":"))),
                   "list_changed_notifications": sum(1 for n in notes if n["method"] == "notifications/tools/list_changed")}
        save("01_surface.json", summary)
        save("01_tools_default.json", default)
        save("01_tools_all.json", full)
        assert summary["enabled_by_default"] == ["core", "inspection"]
        assert summary["default_tools"] < summary["all_tools"]
        assert summary["list_changed_notifications"] >= len(toolsets) - 2


    def test_2_strict_schemas(self, s):
        """additionalProperties: false: a wrong argument name is refused out loud, not dropped."""
        r = s.call("godot_enable_toolset", {"toolset": "runtime"})
        tools = {t["name"]: t for t in s.m.request("tools/list", {})["tools"]}
        save("02_strict.json", {"wrong_argument_reply": r, "enable_toolset_schema": tools["godot_enable_toolset"]["inputSchema"],
                                "enable_toolset_annotations": tools["godot_enable_toolset"].get("annotations")})
        assert r.get("isError") is True and "unexpected keyword argument" in mc.McpClient.text(r)
        assert tools["godot_enable_toolset"]["inputSchema"].get("additionalProperties") is False


    def test_3_inspect_live_scene(self, s):
        tree = s.data("godot_inspection_get_scene_tree")["tree"]
        names = [c["name"] for c in tree["children"]]
        save("03_scene_tree.json", tree)
        assert tree["name"] == "Level" and names == ["Floor", "Ledge", "Player"]


    def test_4_edit_with_undo(self, s):
        """Add a Label in the live editor, then undo and redo it. dry_run changes nothing."""
        dry = s.data("godot_scene_edit_create_node", {"parent_path": ".", "node_type": "Label", "node_name": "Hint", "dry_run": True})
        after_dry = [c["name"] for c in s.data("godot_inspection_get_scene_tree")["tree"]["children"]]
        made = s.data("godot_scene_edit_create_node", {"parent_path": ".", "node_type": "Label", "node_name": "Hint"})
        s.data("godot_scene_edit_set_node_property", {"node_path": "Hint", "property": "text", "value": "Collect 3 coins"})
        with_label = [c["name"] for c in s.data("godot_inspection_get_scene_tree")["tree"]["children"]]
        text = s.data("godot_inspection_get_node_property", {"node_path": "Hint", "property": "text"})
        history = s.data("godot_list_history")
        undo = s.data("godot_undo", {"count": 2})
        after_undo = [c["name"] for c in s.data("godot_inspection_get_scene_tree")["tree"]["children"]]
        redo = s.data("godot_redo", {"count": 2})
        after_redo = [c["name"] for c in s.data("godot_inspection_get_scene_tree")["tree"]["children"]]
        no_confirm = s.call("godot_scene_edit_delete_node", {"node_path": "Hint"})
        still_there = [c["name"] for c in s.data("godot_inspection_get_scene_tree")["tree"]["children"]]
        save("04_edit_undo.json", {"dry_run_reply": dry, "after_dry_run": after_dry, "create_reply": made, "with_label": with_label,
                                   "label_text": text, "history": history, "undo": undo, "after_undo": after_undo, "redo": redo,
                                   "after_redo": after_redo, "delete_without_confirm": no_confirm, "after_delete_without_confirm": still_there})
        assert "Hint" not in after_dry
        assert "Hint" in with_label and "Hint" not in after_undo and "Hint" in after_redo
        assert no_confirm.get("isError") is True and "Hint" in still_there


    def test_5_script_check(self, s):
        """A GDScript with a syntax error: the server reports it with a line number."""
        bad = "extends Node\n\nfunc _ready() -> void\n\tprint(\"missing colon\")\n"
        s.data("godot_scripts_write", {"script_path": "res://scripts/broken.gd", "content": bad})
        errs = s.call("godot_scripts_get_parse_errors", {"script_path": "res://scripts/broken.gd"})
        ok = s.call("godot_scripts_get_parse_errors", {"script_path": "res://scripts/player.gd"})
        save("05_parse_errors.json", {"broken": errs, "player": ok})
        e = json.loads(mc.McpClient.text(errs))
        assert e["ok"] is False and e["errors"]          # the error is reported ...
        assert e["errors"][0]["line"] in (3, 4)         # ... at the missing colon (3) or the line after it (4)
        assert json.loads(mc.McpClient.text(ok))["ok"] is True




# ---- the closed loop: play the game, press keys, read the player's live state -----------------------------------

def jump_test(tag, player):
    """Play the level; jump; press jump again near the top; press a third time. Returns velocity.y after each press."""
    sess = Session(tag, player)
    try:
        sess.enable("runtime", "input")
        sess.data("godot_runtime_play_scene")
        for _ in range(20):
            time.sleep(0.5)
            if sess.data("godot_runtime_get_game_scene_tree").get("connected"):
                break
        time.sleep(1.0)                                   # let the player settle on the ledge
        vy = lambda: sess.data("godot_runtime_read_property", {"node_path": "/root/Level/Player", "property": "velocity"})["value"]["y"]
        press = lambda: (sess.data("godot_input_simulate_action", {"action": "jump", "pressed": True}), time.sleep(0.05),
                         sess.data("godot_input_simulate_action", {"action": "jump", "pressed": False}))
        out = {"start_y": sess.data("godot_runtime_read_property", {"node_path": "/root/Level/Player", "property": "position"})["value"]["y"]}
        press(); time.sleep(0.05); out["after_1st"] = vy()
        time.sleep(0.35); out["before_2nd"] = vy()
        press(); time.sleep(0.05); out["after_2nd"] = vy()
        time.sleep(0.15); press(); time.sleep(0.05); out["after_3rd"] = vy()
        shot = sess.call("godot_runtime_capture_game_screenshot")
        img = next((c for c in shot.get("content", []) if c.get("type") == "image"), None)
        if img:
            with open(os.path.join(OUT, f"{tag}_game.png"), "wb") as f:
                f.write(base64.b64decode(img["data"]))
        out["input_stats"] = sess.data("godot_input_get_stats")
        save(f"{tag}.json", out)
        return out
    finally:
        sess.close()


def walk_off_test(tag, player):
    """Walk right off the ledge without jumping, then press jump in mid-air. Returns velocity.y after the press."""
    sess = Session(tag, player)
    try:
        sess.enable("runtime", "input")
        sess.data("godot_runtime_play_scene")
        for _ in range(20):
            time.sleep(0.5)
            if sess.data("godot_runtime_get_game_scene_tree").get("connected"):
                break
        time.sleep(1.0)
        rd = lambda p: sess.data("godot_runtime_read_property", {"node_path": "/root/Level/Player", "property": p})["value"]
        sess.data("godot_input_simulate_action", {"action": "move_right", "pressed": True})
        out = {"start": rd("position")}
        for _ in range(40):                                # walk until the player is falling
            time.sleep(0.05)
            if rd("velocity")["y"] > 60:
                break
        sess.data("godot_input_simulate_action", {"action": "move_right", "pressed": False})
        out["falling_vy"] = rd("velocity")["y"]
        out["falling_pos"] = rd("position")
        sess.data("godot_input_simulate_action", {"action": "jump", "pressed": True}); time.sleep(0.05)
        sess.data("godot_input_simulate_action", {"action": "jump", "pressed": False}); time.sleep(0.05)
        out["after_air_jump"] = rd("velocity")["y"]
        save(f"{tag}.json", out)
        return out
    finally:
        sess.close()


JUMPED = -150   # velocity.y below this right after a press = a jump happened (jumps are -420 / -360; gravity adds +49 in 0.05 s)


def test_6_shipped_game_single_jump():
    r = jump_test("06_single_jump", None)
    assert r["after_1st"] < JUMPED                        # the first jump works
    assert r["after_2nd"] > JUMPED                        # no second jump in the shipped game


def test_7_reference_double_jump():
    r = jump_test("07_double_jump", "player_double_jump.gd")
    assert r["after_1st"] < JUMPED and r["after_2nd"] < JUMPED   # the second jump works
    assert r["after_3rd"] > JUMPED                               # a third is blocked


def test_8_planted_bug_walk_off_ledge():
    bug = walk_off_test("08_walk_off_bug", "player_planted_bug.gd")
    good = walk_off_test("08_walk_off_reference", "player_double_jump.gd")
    save("08_summary.json", {"bug_after_air_jump": bug["after_air_jump"], "reference_after_air_jump": good["after_air_jump"]})
    assert bug["falling_vy"] > 60 and good["falling_vy"] > 60    # both really walked off and were falling
    assert bug["falling_pos"]["y"] < 500 and good["falling_pos"]["y"] < 500   # pressed well above the floor (floor top ~600)
    assert bug["after_air_jump"] > 0                             # the bug: no jump, still falling (not landed)
    assert good["after_air_jump"] < JUMPED                       # the reference: the air jump works
