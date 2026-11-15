"""같은 시드로 제로샷 Laya 한 판을 다시 두고, 수를 볼 수 있는 HTML로 저장한다.

  python replay_laya.py
  python replay_laya.py --seeds 100053 100086
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import laya

import board as B
import config as C
from eval_laya import pick, questions_for
from game2048 import ACTIONS, Game2048


def record(seeds: list[int]) -> list[dict]:
    games = [Game2048(s) for s in seeds]
    frames = {s: [{"move": None, "score": 0, "grid": B.to_grid(g.board)}] for s, g in zip(seeds, games)}
    agent = laya.load("convaiinnovations/laya", device="cuda")
    qcache: dict[tuple[str, ...], dict] = {}
    while True:
        live = [g for g in games if not g.done()]
        if not live:
            break
        groups: dict[tuple[str, ...], list] = defaultdict(list)
        for g in live:
            groups[tuple(a for a in ACTIONS if a in g.legal())].append(g)
        for legal, gs in groups.items():
            acts = {}
            if len(legal) == 1:
                acts = {id(g): legal[0] for g in gs}
            else:
                qs = qcache.setdefault(legal, questions_for(legal))
                results = agent.predict_batch([_state(g) for g in gs], qs, batch_size=8)
                acts = {id(g): pick(res["answers"], legal) for g, res in zip(gs, results)}
            for g in gs:
                move = acts[id(g)]
                g.step(move)
                frames[g.seed].append({"move": move, "score": g.score, "grid": B.to_grid(g.board)})
    return [{"seed": s, "score": frames[s][-1]["score"], "frames": frames[s]} for s in seeds]


def _state(g: Game2048) -> str:
    from game2048 import render_state
    return render_state(g)


def write_html(games: list[dict], path: Path) -> None:
    payload = json.dumps(games, separators=(",", ":"))
    path.write_text(PAGE.replace("/*GAMES*/", payload), encoding="utf-8")


PAGE = r"""<!doctype html>
<meta charset="utf-8">
<title>Laya 2048 replay</title>
<style>
  body { margin: 0; background: #faf8ef; color: #776e65; font: 16px/1.4 system-ui, sans-serif; }
  main { max-width: 920px; margin: 24px auto; padding: 0 16px; }
  h1 { font-size: 22px; font-weight: 700; margin: 0 0 8px; }
  .row { display: flex; gap: 28px; flex-wrap: wrap; }
  .game { }
  .meta { display: flex; gap: 16px; margin: 8px 0; font-variant-numeric: tabular-nums; }
  .board { background: #bbada0; border-radius: 6px; padding: 8px; display: grid; grid-template-columns: repeat(4, 72px); gap: 8px; }
  .cell { width: 72px; height: 72px; border-radius: 4px; display: grid; place-items: center; font-weight: 700; background: #cdc1b4; }
  .n2 { background: #eee4da; } .n4 { background: #ede0c8; } .n8 { background: #f2b179; color: #f9f6f2; }
  .n16 { background: #f59563; color: #f9f6f2; } .n32 { background: #f67c5f; color: #f9f6f2; }
  .n64 { background: #f65e3b; color: #f9f6f2; } .n128 { background: #edcf72; color: #f9f6f2; font-size: 22px; }
  .n256 { background: #edcc61; color: #f9f6f2; font-size: 22px; } .n512 { background: #edc850; color: #f9f6f2; font-size: 22px; }
  .n1024, .n2048 { background: #edc53f; color: #f9f6f2; font-size: 18px; }
  button, select { font: inherit; padding: 6px 12px; }
  .bar { display: flex; gap: 8px; align-items: center; margin-top: 16px; }
</style>
<main>
  <h1>학습 없는 Laya, 2048 한 수씩</h1>
  <p>왼쪽은 100판 중 최고점, 오른쪽은 평균에 가까운 판입니다. 방금 둔 수가 위에 표시됩니다.</p>
  <div class="row" id="games"></div>
  <div class="bar">
    <button id="play">일시정지</button>
    <label>속도 <input id="speed" type="range" min="1" max="20" value="6"></label>
    <span id="speedlabel"></span>
  </div>
</main>
<script>
const GAMES = /*GAMES*/;
const root = document.getElementById("games");
const views = GAMES.map(g => {
  const box = document.createElement("section");
  box.className = "game";
  box.innerHTML = `<div class="meta"><b>seed ${g.seed}</b><span class="mv"></span><span class="sc"></span></div><div class="board"></div>`;
  root.appendChild(box);
  const cells = [];
  const board = box.querySelector(".board");
  for (let i = 0; i < 16; i++) {
    const c = document.createElement("div");
    c.className = "cell";
    board.appendChild(c);
    cells.push(c);
  }
  return {g, cells, mv: box.querySelector(".mv"), sc: box.querySelector(".sc"), i: 0};
});
const ARROW = {up: "위", down: "아래", left: "왼쪽", right: "오른쪽"};
function draw(v) {
  const f = v.g.frames[v.i];
  f.grid.flat().forEach((n, k) => {
    v.cells[k].className = "cell" + (n ? " n" + n : "");
    v.cells[k].textContent = n || "";
  });
  v.mv.textContent = f.move ? ARROW[f.move] : "시작";
  v.sc.textContent = f.score + "점  " + (v.i + 1) + "/" + v.g.frames.length;
}
views.forEach(draw);
let timer = 0;
function step() {
  let live = false;
  for (const v of views) if (v.i < v.g.frames.length - 1) { v.i++; draw(v); live = true; }
  if (!live) { clearInterval(timer); timer = 0; document.getElementById("play").textContent = "다시"; }
}
function start() {
  clearInterval(timer);
  const n = +document.getElementById("speed").value;
  document.getElementById("speedlabel").textContent = n + "수/초";
  timer = setInterval(step, 1000 / n);
}
document.getElementById("play").onclick = () => {
  if (timer) { clearInterval(timer); timer = 0; document.getElementById("play").textContent = "재생"; }
  else {
    if (views.every(v => v.i >= v.g.frames.length - 1)) { views.forEach(v => { v.i = 0; draw(v); }); }
    document.getElementById("play").textContent = "일시정지";
    start();
  }
};
document.getElementById("speed").oninput = () => { if (timer) start(); else document.getElementById("speedlabel").textContent = document.getElementById("speed").value + "수/초"; };
start();
</script>
"""


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", nargs="+", type=int, default=[100053, 100069])
    a = p.parse_args()
    games = record(a.seeds)
    out = C.RESULTS_DIR / "laya_replay.html"
    out.parent.mkdir(exist_ok=True)
    write_html(games, out)
    print(json.dumps([{"seed": g["seed"], "score": g["score"], "moves": len(g["frames"]) - 1} for g in games]))
    print(out)
