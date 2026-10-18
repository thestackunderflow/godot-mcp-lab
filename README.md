# Can an AI agent play its own game to check its work? A Godot MCP lab

**Lab snapshot: 17 Oct 2026.** Godot **4.7.2** stable (official Linux build, checked against the release's
`SHA512-SUMS.txt`), the community **godot-editor-mcp 2026.10.15** server (PyPI) and its editor add-on (the same
GitHub release, SHA-256 recorded in the image). Everything runs in Docker; nothing is installed on the host.

godot-editor-mcp is a **community project** ([hybridindie/godot-mcp](https://github.com/hybridindie/godot-mcp), MIT),
not part of Godot or the Godot Foundation. This lab asks what it hands an AI agent: what the agent can see, change, run
and check in a live Godot editor, through MCP.

## What's in it

| Path | What it is |
|---|---|
| `game/` | A tiny 2D platformer: one player (single jump), a floor, a ledge, three coins. The add-on's runtime probe is an autoload. |
| `fix/` | `player_double_jump.gd` (the lab's reference double jump) and `player_planted_bug.gd` (the brief's bug: no air jump after walking off a ledge). |
| `run-server.sh` | Starts Xvfb (a virtual screen) + the Godot editor headless + `godot-editor-mcp` on stdio, and stops them all when the server exits. |
| `tests/mcp_client.py` | A small MCP client (JSON-RPC 2.0 over stdio, no SDK) that also records server notifications. |
| `tests/test_lab.py` | Tests 0–8. Each session runs on a fresh copy of `game/`; every reply is saved in `tests/out/`. |
| `claude-run/` | `run-claude.sh` (one real headless Claude Code session, the brief's six prompts) and `summarize.py`. |

```bash
docker compose build
docker compose run --rm tests            # tests 0-9
bash claude-run/run-claude.sh            # optional: the real Claude Code session (needs `claude` logged in)
```

## The tests

Written first and run red (`tests/out/red-phase.log`: stub client), then green (`tests/out/green-phase.log`: **10 passed**).

0. **Versions.** Godot `4.7.2.stable.official`; server and add-on `2026.10.15`, bridge connected. In `initialize` the
   server names itself `godot-mcp` with **FastMCP's version (4.1.0)**, not the package's.
1. **Gated tools.** 29 toolsets; only `core` and `inspection` are on by default: **24 tools, 34,549 characters** of
   tool JSON. With every toolset enabled: **194 tools, 237,669 characters**. Each enable sends
   `notifications/tools/list_changed` (27 seen).
2. **Strict inputs.** `additionalProperties: false`, so a wrong argument name comes back as "unexpected keyword
   argument(s)". (`godot_enable_toolset` is annotated read-only, though it changes the tool list.)
3. **Live scene.** The editor's tree: Level → Floor, Ledge, Coins, Player.
4. **Edit, undo, confirm.** `dry_run` changes nothing. Create a Label and set its text; undo ×2 removes it, redo ×2
   restores it. `delete_node` without `confirm: true` is refused.
5. **Script check.** A missing colon on line 3 is reported as "Unexpected Indent" **on line 4**. The real player
   script parses.
6. **Closed loop, shipped game** (played in Xvfb, input injected through the runtime probe, velocity read live; each
   reading arrives ~0.1 s after the press, so gravity has already added ~+100). The first jump reads −387; a second
   press near the top of the arc (y = 136, about 90 px above the ledge) reads +331: no jump.
7. **Reference double jump.** The same second press, in mid-air, reads −327 (the air jump); a third press, still in
   the air (y = 130), reads −50: blocked (the jump speeds themselves are −420 and −360).

   Numbers are from the committed run (`tests/out/06_single_jump.json`, `07_double_jump.json`). Because each reading
   lands a few frames after the press, they move by a few tens from run to run; the tests check the sign and the
   jump/no-jump verdict, not the exact value.
8. **Planted bug.** Walk off the ledge and press jump at y = 316, well above the floor: the bug version keeps falling
   (+621), while the reference jumps (−278).
9. **Update check.** At start the server's *framework*, FastMCP, asks PyPI for a newer FastMCP (at most every 12 h; it
   caches the answer). `FASTMCP_CHECK_FOR_UPDATES=off` stops it. godot-mcp's own update check is opt-in
   (`GODOT_MCP_CHECK_UPDATES`) and off by default.

Game screenshots taken by the server: `tests/out/06_single_jump_game.png`, `07_double_jump_game.png`.

## The real Claude Code session

See `tests/out/claude-run/summary.md`. One session, the brief's six prompts, only the Godot MCP tools (no file tools),
no personal CLAUDE.md, the editor given a head start as on a desktop where Godot is already open, and the planted bug
swapped in between prompts 4 and 5 (disclosed). `claude-run-1-NOTE.md` explains why an earlier run was discarded: the
planted file's comment described the bug.
