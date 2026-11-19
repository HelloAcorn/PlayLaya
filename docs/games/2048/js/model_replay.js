// 미리 기록한 이미지 모델의 한 판을 같은 보드 위에 재생한다.
// 기본 파일은 replays/my_model.json. ?replay=이름.json 은 그 폴더 안의 다른 파일(확인용).
(function () {
  var DIRS = ["up", "down", "left", "right"];
  var KO = { up: "위", down: "아래", left: "왼쪽", right: "오른쪽" };
  var watchBtn = document.getElementById("model-watch");
  var panel = document.getElementById("model-panel");
  var emptyEl = document.getElementById("model-empty");
  var noteEl = document.getElementById("model-note");
  var playBtn = document.getElementById("model-play");
  var speed = document.getElementById("model-speed-range");
  var speedLabel = document.getElementById("model-speed-label");
  var scoreEl = document.getElementById("model-score");
  var moveEl = document.getElementById("model-move");
  var progressEl = document.getElementById("model-progress");
  var seedEl = document.getElementById("model-seed");
  var barsEl = document.getElementById("model-bars");
  if (!watchBtn || !panel || !emptyEl || !noteEl || typeof GameManager === "undefined") return;

  var watching = false;
  var loading = false;
  var timer = 0;
  var catalog = [];
  var current = null;
  var frames = [];
  var index = 0;

  var origRestart = GameManager.prototype.restart;
  GameManager.prototype.restart = function () {
    if (watching) leave(false);
    return origRestart.apply(this, arguments);
  };

  function replayName() {
    var q = "";
    try { q = new URLSearchParams(location.search).get("replay") || ""; } catch (e) { q = ""; }
    if (/^[\w.-]+\.json$/.test(q)) return q;
    return "my_model.json";
  }

  function showMissing() {
    watching = false;
    document.documentElement.classList.remove("model-watching");
    stop();
    panel.hidden = true;
    watchBtn.hidden = false;
    emptyEl.hidden = false;
    noteEl.hidden = false;
  }

  function leave(restore) {
    watching = false;
    document.documentElement.classList.remove("model-watching");
    stop();
    panel.hidden = true;
    emptyEl.hidden = true;
    noteEl.hidden = true;
    watchBtn.hidden = false;
    if (restore && window.gameManager) window.gameManager.actuate();
  }

  function stop() {
    if (timer) { clearInterval(timer); timer = 0; }
  }

  function framesOf(g) {
    var out = [];
    if (g.start && g.start.length === 16) out.push({ g: g.start, m: null, s: 0, p: null });
    var moves = g.moves || [];
    for (var i = 0; i < moves.length; i++) {
      var m = moves[i];
      if (!m || !m.g || m.g.length !== 16) continue;
      out.push(m);
    }
    return out;
  }

  function usable(data) {
    if (!data || !data.games || !data.games.length) return [];
    if (data.fixture && replayName() === "my_model.json") return [];
    var out = [];
    for (var i = 0; i < data.games.length; i++) {
      var g = data.games[i];
      var fr = g && framesOf(g);
      if (fr && fr.length && fr.some(function (f) { return f.m; })) out.push({ raw: g, frames: fr });
    }
    return out;
  }

  function paint(grid) {
    var box = document.querySelector(".tile-container");
    if (!box) return;
    var frag = document.createDocumentFragment();
    for (var i = 0; i < 16; i++) {
      var v = grid[i];
      if (!v) continue;
      var col = (i % 4) + 1;
      var row = ((i / 4) | 0) + 1;
      var tile = document.createElement("div");
      var inner = document.createElement("div");
      tile.className = "tile tile-" + v + " tile-position-" + col + "-" + row + (v > 2048 ? " tile-super" : "");
      inner.className = "tile-inner";
      inner.textContent = v;
      tile.appendChild(inner);
      frag.appendChild(tile);
    }
    box.textContent = "";
    box.appendChild(frag);
  }

  function drawBars(p, move) {
    barsEl.textContent = "";
    for (var i = 0; i < DIRS.length; i++) {
      var name = DIRS[i];
      var val = p ? +p[i] || 0 : 0;
      if (val < 0) val = 0;
      if (val > 1) val = 1;
      var row = document.createElement("div");
      row.className = "model-bar" + (move === name ? " on" : "");
      var lab = document.createElement("span");
      lab.textContent = KO[name];
      var track = document.createElement("span");
      track.className = "track";
      var fill = document.createElement("i");
      fill.style.width = (val * 100) + "%";
      track.appendChild(fill);
      var pct = document.createElement("span");
      pct.textContent = p ? Math.round(val * 100) + "%" : "";
      row.appendChild(lab);
      row.appendChild(track);
      row.appendChild(pct);
      barsEl.appendChild(row);
    }
  }

  function moveCount(fr) {
    var n = 0;
    for (var i = 0; i < fr.length; i++) if (fr[i].m) n++;
    return n;
  }

  function draw() {
    var f = frames[index];
    if (!f) return;
    paint(f.g);
    var score = f.s || 0;
    scoreEl.textContent = "점수 " + score;
    var box = document.querySelector(".score-container");
    if (box) box.textContent = String(score);
    // 재생 중에는 점수 칸만 맞춘다. BEST 가 더 작아 보이지 않게 현재 점수를 보여 주고, 저장하지는 않는다.
    var best = document.querySelector(".best-container");
    if (best) best.textContent = String(score);
    var label = f.m ? (KO[f.m] || f.m) : "시작";
    if (index === frames.length - 1 && current.raw.done) label += " · 판 끝";
    moveEl.textContent = "이번 수 " + label;
    var taken = 0;
    for (var i = 0; i <= index; i++) if (frames[i].m) taken++;
    progressEl.textContent = taken + " / " + moveCount(frames) + "수";
    seedEl.textContent = "시드 " + current.raw.seed;
    drawBars(f.p, f.m);
  }

  function atEnd() {
    return index >= frames.length - 1;
  }

  function stepFrame() {
    if (!atEnd()) { index++; draw(); }
    if (atEnd()) { stop(); playBtn.textContent = "다시"; }
  }

  function startTimer() {
    stop();
    var n = +speed.value || 4;
    speedLabel.textContent = n + "수/초";
    timer = setInterval(stepFrame, 1000 / n);
  }

  function pick(list) {
    if (list.length === 1) return list[0];
    var i = Math.floor(Math.random() * list.length);
    var guard = 0;
    while (current && list[i] === current && guard++ < 8) i = Math.floor(Math.random() * list.length);
    return list[i];
  }

  function nextGame(autoplay) {
    current = pick(catalog);
    frames = current.frames;
    index = 0;
    draw();
    if (autoplay) {
      playBtn.textContent = "일시정지";
      startTimer();
    } else {
      stop();
      playBtn.textContent = "재생";
    }
  }

  function hideOverlay() {
    var msg = document.querySelector(".game-message");
    if (!msg) return;
    msg.classList.remove("game-won");
    msg.classList.remove("game-over");
  }

  function begin(list) {
    catalog = list;
    watching = true;
    document.documentElement.classList.add("model-watching");
    watchBtn.hidden = true;
    emptyEl.hidden = true;
    panel.hidden = false;
    noteEl.hidden = false;
    hideOverlay();
    current = null;
    nextGame(true);
  }

  watchBtn.addEventListener("click", function () {
    if (loading) return;
    loading = true;
    watchBtn.disabled = true;
    fetch("replays/" + replayName(), { cache: "no-store" }).then(function (res) {
      if (!res.ok) throw new Error("missing");
      return res.json();
    }).then(function (data) {
      var list = usable(data);
      if (!list.length) showMissing();
      else begin(list);
    }).catch(function () {
      showMissing();
    }).then(function () {
      loading = false;
      watchBtn.disabled = false;
    });
  });

  playBtn.addEventListener("click", function () {
    if (!watching) return;
    if (timer) {
      stop();
      playBtn.textContent = "재생";
      return;
    }
    if (atEnd()) { index = 0; draw(); }
    playBtn.textContent = "일시정지";
    startTimer();
  });

  document.getElementById("model-step").addEventListener("click", function () {
    if (!watching) return;
    stop();
    if (atEnd()) { index = 0; draw(); playBtn.textContent = "재생"; return; }
    index++;
    draw();
    playBtn.textContent = atEnd() ? "다시" : "재생";
  });

  document.getElementById("model-next").addEventListener("click", function () {
    if (!watching || !catalog.length) return;
    nextGame(true);
  });

  document.getElementById("model-human").addEventListener("click", function () {
    leave(true);
  });

  speed.addEventListener("input", function () {
    speedLabel.textContent = (+speed.value || 4) + "수/초";
    if (timer) startTimer();
  });

  document.addEventListener("keydown", function (e) {
    if (!watching) return;
    var k = e.which || e.keyCode;
    if (k === 82 || k === 37 || k === 38 || k === 39 || k === 40 ||
        k === 65 || k === 68 || k === 72 || k === 74 || k === 75 || k === 76 || k === 83 || k === 87) {
      e.preventDefault();
      e.stopImmediatePropagation();
    }
  }, true);

  var board = document.querySelector(".game-container");
  if (board) {
    ["touchstart", "touchmove", "touchend"].forEach(function (ev) {
      board.addEventListener(ev, function (e) {
        if (!watching) return;
        e.stopImmediatePropagation();
        if (ev !== "touchend") e.preventDefault();
      }, { capture: true, passive: false });
    });
  }
})();
