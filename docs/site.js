// PlayLaya front page. Theme and sticky bar follow PlayJev's demo.js. The stage frames one of the ten vendored
// games at a time, cropped to the game's own board like PlayJev's demo. For 2048 it also shows the board as the
// text state the model is trained on (same format as 2048_decision_ft/game2048.py); the other games have no
// PlayLaya model yet, so their panel lists the controls and the source instead.
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

  // ---------------------------------------------------------------- the roster
  const GAMES = [
   {
    "id": "2048",
    "title": "2048",
    "entry": "games/2048/index.html",
    "w": 540,
    "h": 760,
    "view": ".container",
    "upstream": "gabrielecirulli/2048",
    "license": "MIT",
    "lic": "games/2048/LICENSE.txt",
    "controls": [
     "방향키 또는 스와이프: 타일 밀기",
     "New Game: 새 판"
    ],
    "embed": "games/2048/index.html?embed",
    "ft": true
   },
   {
    "id": "tetris",
    "title": "Tetris",
    "entry": "games/tetris/index.html",
    "w": 680,
    "h": 680,
    "view": "#canvas",
    "upstream": "jakesgordon/javascript-tetris",
    "license": "MIT",
    "lic": "games/tetris/LICENSE",
    "controls": [
     "Space: 시작",
     "← →: 옆으로 이동",
     "↑: 회전",
     "↓: 한 칸 내리기",
     "Esc: 판 끝내기"
    ],
    "embed": "games/tetris/index.html",
    "ft": false
   },
   {
    "id": "snake",
    "title": "Snake",
    "entry": "games/snake/src/index.html",
    "w": 520,
    "h": 520,
    "view": ".snake-playing-field",
    "upstream": "patorjk/JavaScript-Snake",
    "license": "MIT",
    "lic": "games/snake/LICENSE",
    "controls": [
     "Play Game 버튼, 또는 키보드 연결을 누른 뒤 Space: 시작",
     "방향키: 방향 바꾸기"
    ],
    "embed": "games/snake/src/index.html",
    "ft": false
   },
   {
    "id": "pacman",
    "title": "Pacman",
    "entry": "games/pacman/index.html",
    "w": 400,
    "h": 600,
    "view": "#pacman canvas",
    "upstream": "daleharvey/pacman",
    "license": "WTFPL",
    "lic": "games/pacman/LICENSE",
    "controls": [
     "N: 새 게임",
     "방향키: 다음 갈림길에서 방향 바꾸기",
     "P: 일시정지"
    ],
    "embed": "games/pacman/index.html",
    "ft": false
   },
   {
    "id": "racer",
    "title": "Javascript Racer",
    "entry": "games/racer/v4.final.html",
    "w": 1100,
    "h": 900,
    "view": "#canvas",
    "upstream": "jakesgordon/javascript-racer",
    "license": "MIT",
    "lic": "games/racer/LICENSE",
    "controls": [
     "↑ / W: 가속",
     "↓ / S: 감속",
     "← → / A D: 조향"
    ],
    "embed": "games/racer/v4.final.html",
    "ft": false
   },
   {
    "id": "invaders",
    "title": "Space Invaders",
    "entry": "games/invaders/index.html",
    "w": 800,
    "h": 600,
    "view": "canvas",
    "upstream": "StrykerKKD/SpaceInvaders",
    "license": "MIT",
    "lic": "games/invaders/LICENSE",
    "controls": [
     "Space: 시작, 다시 시작",
     "← →: 이동 (사격은 자동)"
    ],
    "embed": "games/invaders/index.html",
    "ft": false
   },
   {
    "id": "sokoban",
    "title": "Sokoban",
    "entry": "games/sokoban/index.html",
    "w": 1100,
    "h": 960,
    "view": "canvas",
    "upstream": "taniarascia/sokoban",
    "license": "MIT",
    "lic": "games/sokoban/LICENSE",
    "controls": [
     "방향키: 이동, 상자 밀기",
     "처음부터 버튼: 다시 시작 (새 탭에서는 Restart 버튼)"
    ],
    "embed": "games/sokoban/index.html",
    "ft": false
   },
   {
    "id": "mario",
    "title": "Infinite Mario",
    "entry": "games/mario/main.html",
    "w": 660,
    "h": 520,
    "view": "#canvas",
    "upstream": "robertkleffner/mariohtml5",
    "license": "Unlicense",
    "lic": "games/mario/LICENSE.md",
    "controls": [
     "S: 시작, 점프",
     "← →: 이동",
     "A: 달리기, 불꽃"
    ],
    "embed": "games/mario/main.html",
    "ft": false
   },
   {
    "id": "flappy",
    "title": "Floppy Bird",
    "entry": "games/flappy/index.html",
    "w": 320,
    "h": 525,
    "view": "#gamescreen",
    "upstream": "nebez/floppybird",
    "license": "Apache-2.0",
    "lic": "games/flappy/LICENSE",
    "controls": [
     "Space 또는 클릭/탭: 날갯짓",
     "죽은 뒤 Space: 다시 하기"
    ],
    "embed": "games/flappy/index.html",
    "ft": false
   },
   {
    "id": "breakout",
    "title": "Breakout",
    "entry": "games/breakout/index.html",
    "w": 700,
    "h": 540,
    "view": "#canvas",
    "upstream": "jakesgordon/javascript-breakout",
    "license": "MIT",
    "lic": "games/breakout/LICENSE",
    "controls": [
     "Space / Enter: 시작, 공 발사",
     "← → / A D: 패들 이동",
     "Esc: 판 끝내기"
    ],
    "embed": "games/breakout/index.html",
    "ft": false
   }
  ];

  const $ = (id) => document.getElementById(id);
  const hero = $('hero'), frame = $('game'), view = $('hero-view');
  const roMain = $('ro-main'), roSide = $('ro-side'), note = $('hero-note');
  const titleEl = $('hero-title'), scoreEl = $('hero-score'), openEl = $('btn-open'), newBtn = $('btn-new');
  if (!hero || !frame) return;
  const byId = Object.fromEntries(GAMES.map((g) => [g.id, g]));
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };

  let cur = null, observers = [], fitTimer = 0;

  // ---------------------------------------------------------------- framing: crop the page to the game's board
  function fit() {
    if (!cur) return;
    let r = { x: 0, y: 0, w: cur.w, h: cur.h };
    let doc = null; try { doc = frame.contentDocument; } catch (e) {}
    const v = doc && cur.view && doc.querySelector(cur.view);
    if (v) {
      const b = v.getBoundingClientRect();
      if (b.width > 40 && b.height > 40) r = { x: Math.max(0, b.left), y: Math.max(0, b.top), w: Math.min(b.width, cur.w), h: Math.min(b.height, cur.h) };
    }
    hero.style.setProperty('--ar', (r.w / r.h).toFixed(4));
    frame.style.width = cur.w + 'px'; frame.style.height = cur.h + 'px';
    const s = view.clientWidth / r.w;
    frame.style.transform = `scale(${s}) translate(${-r.x}px, ${-r.y}px)`;
  }
  window.addEventListener('resize', fit);

  // ---------------------------------------------------------------- 2048: the text state window
  const ACTIONS = ['up', 'down', 'left', 'right'];
  const DESC = { up: 'slide all tiles up', down: 'slide all tiles down', left: 'slide all tiles left', right: 'slide all tiles right' };
  const LETTERS = 'ABCD';
  function readBoard(doc) {
    const g = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]];
    doc.querySelectorAll('.tile-container .tile').forEach((t) => {
      const m = /tile-position-(\d)-(\d)/.exec(t.className); if (!m) return;
      const x = +m[1] - 1, y = +m[2] - 1, v = parseInt(t.textContent, 10) || 0;
      if (v > g[y][x]) g[y][x] = v;      // a merge leaves both sources under the merged tile; the sum is largest
    });
    const sc = doc.querySelector('.score-container');
    return { g, score: sc && sc.firstChild ? parseInt(sc.firstChild.nodeValue, 10) || 0 : 0 };
  }
  function slide(row) {
    const t = row.filter((v) => v), out = [];
    for (let i = 0; i < t.length; i++) { if (i + 1 < t.length && t[i] === t[i + 1]) { out.push(t[i] * 2); i++; } else out.push(t[i]); }
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
  function render2048() {
    const doc = frame.contentDocument, stateEl = $('state'), optsEl = $('opts');
    if (!doc || !stateEl) return;
    const { g, score } = readBoard(doc);
    const key = g.flat().join(',') + '|' + score, tiles = g.flat().filter((v) => v).length;
    if (last === null) { known = tiles === 2 && score === 0; moves = 0; }
    else if (key !== last) { if (tiles === 2 && score === 0) { moves = 0; known = true; } else moves++; }
    last = key;
    const empty = g.flat().filter((v) => !v).length, max = Math.max.apply(null, g.flat());
    stateEl.textContent = `Move: ${known ? moves : '?'} | Score: ${score} | Empty: ${empty} | Max tile: ${max}\n` +
      'Board (4x4, . = empty):\n' + g.map((r) => r.map((v) => String(v || '.').padStart(5)).join(' ')).join('\n');
    scoreEl.textContent = score.toLocaleString('ko-KR') + '점';
    const legal = ACTIONS.filter((a) => moved(g, a));
    optsEl.textContent = '';
    if (!legal.length) optsEl.appendChild(el('span', 'off', '둘 수 있는 수 없음 (게임 끝)'));
    legal.forEach((a, i) => { const s = el('span', null, `${LETTERS[i]}. ${a}`); s.title = DESC[a]; optsEl.appendChild(s); });
  }

  // ---------------------------------------------------------------- the readout column
  function readout(g) {
    roMain.textContent = ''; roSide.textContent = '';
    if (g.id === '2048') {
      roMain.append(el('p', 'readout-label', '모델이 보는 상태창 (지금 보드)'), el('pre', 'state', '불러오는 중'));
      roMain.lastChild.id = 'state';
      roSide.append(el('p', 'readout-label', '선택지: 보드를 실제로 바꾸는 수만'), el('div', 'opts'));
      roSide.lastChild.id = 'opts';
      scoreEl.textContent = '';
      note.textContent = '보드를 클릭하고 방향키로 두거나, 휴대폰에서는 스와이프하세요. 브라우저에서는 모델을 돌리지 않고, 학습 때 쓰는 상태창 형식만 그대로 보여 줘요.';
      return;
    }
    roMain.append(el('p', 'readout-label', '조작'));
    const ul = el('ul', 'factlist keys'); g.controls.forEach((c) => ul.appendChild(el('li', null, c))); roMain.appendChild(ul);
    roSide.append(el('p', 'readout-label', '원작과 라이선스'));
    const src = el('div', 'opts');
    const a = el('a', null, g.upstream); a.href = 'https://github.com/' + g.upstream; src.appendChild(a);
    const l = el('a', null, g.license); l.href = g.lic; src.appendChild(l);
    roSide.appendChild(src);
    scoreEl.textContent = g.license;
    note.textContent = '보드를 한 번 클릭한 뒤 키보드로 두세요. 이 게임은 아직 PlayLaya 파인튜닝 코드가 없어서, 모델 출력 없이 게임만 돌아가요.';
  }

  // ---------------------------------------------------------------- picking a game
  function pick(id, focus) {
    const g = byId[id] || byId['2048'];
    cur = g; last = null;
    observers.forEach((o) => o.disconnect()); observers = [];
    clearInterval(fitTimer);
    document.querySelectorAll('#picker button').forEach((b) => {
      const on = b.dataset.game === g.id; b.classList.toggle('on', on); b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    document.querySelectorAll('#grid .card').forEach((c) => c.classList.toggle('active', c.dataset.game === g.id));
    titleEl.textContent = g.title; frame.title = g.title;
    openEl.href = g.entry;
    newBtn.textContent = g.id === '2048' ? '새 게임' : '처음부터';
    readout(g);
    hero.style.setProperty('--ar', (g.w / g.h).toFixed(4));
    view.style.backgroundColor = g.id === '2048' ? '#faf8ef' : '';
    frame.style.visibility = 'hidden';
    frame.style.width = g.w + 'px'; frame.style.height = g.h + 'px';   // the page loads at its final size, so games that size themselves to the window never rebuild
    frame.dataset.want = g.id;
    frame.src = g.embed;
    if (focus) frame.focus();
    try { const u = new URL(location.href); u.searchParams.set('game', g.id); history.replaceState(null, '', u); } catch (e) {}
  }

  frame.addEventListener('load', () => {
    const g = cur; if (!g) return;
    let doc = null; try { doc = frame.contentDocument; } catch (e) {}
    if (!doc || !doc.body || doc.location.href === 'about:blank') return;
    fit(); frame.style.visibility = 'visible';
    [150, 500, 1200].forEach((t) => setTimeout(fit, t));   // fonts, canvases sized by script
    fitTimer = setInterval(fit, 2000);
    if (g.id === '2048') {
      const box = doc.querySelector('.tile-container'), sc = doc.querySelector('.score-container');
      let t = 0; const later = () => { clearTimeout(t); t = setTimeout(render2048, 80); };
      if (box) { const o = new MutationObserver(later); o.observe(box, { childList: true, subtree: true, attributes: true }); observers.push(o); }
      if (sc) { const o = new MutationObserver(later); o.observe(sc, { childList: true, characterData: true, subtree: true }); observers.push(o); }
      render2048();
    }
  });

  document.querySelectorAll('#picker button').forEach((b) => b.addEventListener('click', () => pick(b.dataset.game, true)));
  document.querySelectorAll('#grid [data-pick]').forEach((a) => a.addEventListener('click', (e) => {
    e.preventDefault(); pick(a.dataset.pick, true);
    document.querySelector('.lead-stage').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }));
  newBtn.addEventListener('click', () => {
    if (cur && cur.id === '2048') {
      const b = frame.contentDocument && frame.contentDocument.querySelector('.restart-button');
      if (b) b.click();
    } else if (cur) { frame.contentWindow.location.reload(); }
    frame.contentWindow.focus();
  });
  $('btn-focus').addEventListener('click', () => frame.contentWindow.focus());

  let start = '2048';
  try { const q = new URL(location.href).searchParams.get('game'); if (q && byId[q.toLowerCase()]) start = q.toLowerCase(); } catch (e) {}
  pick(start, false);
})();
