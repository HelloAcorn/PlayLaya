// PlayLaya front page. Theme and sticky bar follow PlayJev's demo.js; the rest frames the vendored 2048 and
// shows the board as the text state the model is trained on (same format as 2048_decision_ft/game2048.py).
(function () {
  'use strict';
  const remember = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* private window */ } };

  // ---------------------------------------------------------------- chrome
  (function theme() {
    const root = document.documentElement, btn = document.getElementById('theme');
    let stored = null; try { stored = localStorage.getItem('ps-theme'); } catch (e) {}
    if (stored === 'dark' || stored === 'light') root.dataset.theme = stored;
    const isDark = () => root.dataset.theme ? root.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    const label = () => { btn.textContent = isDark() ? '라이트' : '다크'; };
    btn.addEventListener('click', () => { root.dataset.theme = isDark() ? 'light' : 'dark'; remember('ps-theme', root.dataset.theme); label(); });
    label();
  })();
  (function stickyLine() {
    const top = document.querySelector('.top'); if (!top) return;
    const onScroll = () => top.classList.toggle('stuck', window.scrollY > 4);
    window.addEventListener('scroll', onScroll, { passive: true }); onScroll();
  })();

  // ---------------------------------------------------------------- the 2048 board
  const hero = document.getElementById('hero');
  const frame = document.getElementById('game');
  const view = document.getElementById('hero-view');
  const stateEl = document.getElementById('state');
  const optsEl = document.getElementById('opts');
  const scoreEl = document.getElementById('hero-score');
  if (!hero || !frame) return;

  const W = 540;            // wider than the upstream 520px phone breakpoint, so the desktop layout shows; the frame is scaled to fit the tile
  let H = 700;
  function fit() {
    const doc = frame.contentDocument;
    const c = doc && doc.querySelector('.game-container');
    if (c) H = Math.max(560, Math.ceil(c.getBoundingClientRect().bottom) + 12);
    hero.style.setProperty('--ar', (W / H).toFixed(4));
    frame.style.width = W + 'px'; frame.style.height = H + 'px';
    const s = view.clientWidth / W;
    frame.style.transform = `scale(${s})`;
  }
  window.addEventListener('resize', fit);

  const ACTIONS = ['up', 'down', 'left', 'right'];
  const DESC = { up: 'slide all tiles up', down: 'slide all tiles down', left: 'slide all tiles left', right: 'slide all tiles right' };
  const LETTERS = 'ABCD';

  function readBoard(doc) {
    const g = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]];
    doc.querySelectorAll('.tile-container .tile').forEach((el) => {
      const m = /tile-position-(\d)-(\d)/.exec(el.className); if (!m) return;
      const x = +m[1] - 1, y = +m[2] - 1;
      const v = parseInt(el.textContent, 10) || 0;
      if (v > g[y][x]) g[y][x] = v;      // a merge leaves both sources under the merged tile; the sum is largest
    });
    const sc = doc.querySelector('.score-container');
    const score = sc && sc.firstChild ? parseInt(sc.firstChild.nodeValue, 10) || 0 : 0;
    return { g, score };
  }

  // slide one row toward index 0; returns the new row
  function slide(row) {
    const t = row.filter((v) => v); const out = [];
    for (let i = 0; i < t.length; i++) {
      if (i + 1 < t.length && t[i] === t[i + 1]) { out.push(t[i] * 2); i++; } else out.push(t[i]);
    }
    while (out.length < 4) out.push(0);
    return out;
  }
  function moved(g, a) {
    for (let k = 0; k < 4; k++) {
      let line;
      if (a === 'left') line = g[k].slice();
      else if (a === 'right') line = g[k].slice().reverse();
      else if (a === 'up') line = [g[0][k], g[1][k], g[2][k], g[3][k]];
      else line = [g[3][k], g[2][k], g[1][k], g[0][k]];
      const s = slide(line);
      if (s.some((v, i) => v !== line[i])) return true;
    }
    return false;
  }

  let moves = 0, known = true, last = null;
  function render() {
    const doc = frame.contentDocument; if (!doc) return;
    const { g, score } = readBoard(doc);
    const key = g.flat().join(',') + '|' + score;
    const tiles = g.flat().filter((v) => v).length;
    if (last === null) { known = tiles === 2 && score === 0; moves = 0; }
    else if (key !== last) {
      if (tiles === 2 && score === 0) { moves = 0; known = true; } else moves++;
    }
    last = key;
    const empty = g.flat().filter((v) => !v).length;
    const max = Math.max.apply(null, g.flat());
    const rows = g.map((r) => r.map((v) => String(v || '.').padStart(5)).join(' '));
    stateEl.textContent = `Move: ${known ? moves : '?'} | Score: ${score} | Empty: ${empty} | Max tile: ${max}\n` +
      'Board (4x4, . = empty):\n' + rows.join('\n');
    scoreEl.textContent = score.toLocaleString('ko-KR') + '점';
    const legal = ACTIONS.filter((a) => moved(g, a));
    optsEl.textContent = '';
    if (!legal.length) { const s = document.createElement('span'); s.className = 'off'; s.textContent = '둘 수 있는 수 없음 (게임 끝)'; optsEl.appendChild(s); }
    legal.forEach((a, i) => {
      const s = document.createElement('span');
      s.textContent = `${LETTERS[i]}. ${a}`; s.title = DESC[a];
      optsEl.appendChild(s);
    });
  }

  let timer = 0;
  const schedule = () => { clearTimeout(timer); timer = setTimeout(render, 80); };

  let wired = false;
  frame.addEventListener('load', () => {
    const doc = frame.contentDocument;
    if (!doc) { stateEl.textContent = '게임 프레임을 읽을 수 없어요.'; return; }
    if (wired || !doc.querySelector('.tile-container')) return;
    wired = true;
    fit();
    setTimeout(fit, 300);   // the web fonts can change the heading height once they arrive
    const box = doc.querySelector('.tile-container');
    new MutationObserver(schedule).observe(box, { childList: true, subtree: true, attributes: true });
    new MutationObserver(schedule).observe(doc.querySelector('.score-container'), { childList: true, characterData: true, subtree: true });
    render();
  });
  if (frame.contentDocument && frame.contentDocument.readyState === 'complete' && frame.contentDocument.querySelector('.tile-container')) frame.dispatchEvent(new Event('load'));

  document.getElementById('btn-new').addEventListener('click', () => {
    const b = frame.contentDocument && frame.contentDocument.querySelector('.restart-button');
    if (b) b.click();
    frame.contentWindow.focus();
  });
  document.getElementById('btn-focus').addEventListener('click', () => frame.contentWindow.focus());
})();
