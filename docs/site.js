// PlayVLA front page. Written here; not a copy of PlayJev demo/demo.js.
// Theme and sticky bar follow PlayJev's demo.js (Apache-2.0, docs/licenses/PlayJev-LICENSE.txt).
// The stage frames one of the ten vendored games at a time, cropped to the game's own board
// like PlayJev's demo. Every game shows the text state a
// decision model would read, plus that game's lettered moves (PlayJev's action list). 2048 stays on the
// format in 2048_decision_ft/game2048.py. The other nine have no fine-tuning code yet; the panel only
// mirrors the live game. State is read from the game's own objects (DOM for 2048, closures that are
// already global for Tetris/Racer/Floppy Bird/Pacman/Sokoban/Breakout, and playlayaBoard / playlayaGame /
// playlayaApp where the instance was not already visible).
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

  let cur = null, observers = [], fitTimer = 0, poll = 0;

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
  const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
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

  // ---------------------------------------------------------------- the other nine: same window, PlayJev's moves
  // name + description, in PlayJev's order (demo/data.js). Letters stay put: A is always the first move.
  const MOVES = {
    tetris: [
      ['left', 'shift the falling piece one column to the left'],
      ['right', 'shift the falling piece one column to the right'],
      ['rotate', 'turn the falling piece a quarter turn clockwise'],
      ['drop', 'send the falling piece straight down until it lands'],
      ['none', 'leave the piece alone and let it sink one row']
    ],
    snake: [
      ['up', 'turn the snake to move up'],
      ['down', 'turn the snake to move down'],
      ['left', 'turn the snake to move left'],
      ['right', 'turn the snake to move right']
    ],
    pacman: [
      ['up', 'head up at the next opening'],
      ['down', 'head down at the next opening'],
      ['left', 'head left at the next opening'],
      ['right', 'head right at the next opening']
    ],
    racer: [
      ['left', 'steer to the left'],
      ['right', 'steer to the right'],
      ['faster', 'press the accelerator'],
      ['slower', 'press the brake'],
      ['left faster', 'accelerate while steering left'],
      ['right faster', 'accelerate while steering right']
    ],
    invaders: [
      ['left', 'move the ship left'],
      ['right', 'move the ship right'],
      ['noop', 'keep the ship where it is']
    ],
    sokoban: [
      ['up', 'move one square up, pushing a box ahead if the square behind it is free'],
      ['down', 'move one square down, pushing a box ahead if the square behind it is free'],
      ['left', 'move one square left, pushing a box ahead if the square behind it is free'],
      ['right', 'move one square right, pushing a box ahead if the square behind it is free']
    ],
    mario: [
      ['noop', 'do nothing for a moment'],
      ['left', 'walk to the left'],
      ['right', 'walk to the right'],
      ['jump', 'jump up'],
      ['right jump', 'jump while moving to the right'],
      ['right run', 'run to the right at full speed'],
      ['right run jump', 'run to the right at full speed and jump']
    ],
    flappy: [
      ['flap', 'flap the wings once to rise'],
      ['wait', 'do nothing and let the bird fall']
    ],
    breakout: [
      ['left', 'move the paddle to the left'],
      ['right', 'move the paddle to the right'],
      ['stay', 'keep the paddle where it is']
    ]
  };
  const TET = { cyan: 'I', blue: 'J', orange: 'L', yellow: 'O', green: 'S', purple: 'T', red: 'Z' };
  const num = (n) => (Number(n) || 0).toLocaleString('ko-KR');
  const fix = (n, d) => { const p = Math.pow(10, d); return (Math.round((Number(n) || 0) * p) / p).toFixed(d); };
  function showMoves(id, illegal) {
    const optsEl = $('opts'); if (!optsEl) return;
    optsEl.textContent = '';
    (MOVES[id] || []).forEach((m, i) => {
      const s = el('span', illegal && illegal[m[0]] ? 'off' : '', `${LETTERS[i]}. ${m[0]}`);
      s.title = m[1];
      optsEl.appendChild(s);
    });
  }
  function readTetris(win) {
    if (!win.getBlock || win.nx == null || win.ny == null) return null;
    const nx = win.nx, ny = win.ny, grid = [];
    for (let y = 0; y < ny; y++) {
      const row = [];
      for (let x = 0; x < nx; x++) {
        const b = win.getBlock(x, y);
        row.push(b && b.color ? (TET[b.color] || '#') : '.');
      }
      grid.push(row);
    }
    const curp = win.current, playing = !!win.playing;
    const name = curp && curp.type ? (TET[curp.type.color] || '?') : '?';
    if (playing && curp && win.eachblock) {
      win.eachblock(curp.type, curp.x, curp.y, curp.dir, (x, y) => {
        if (y >= 0 && y < ny && x >= 0 && x < nx) grid[y][x] = name.toLowerCase();
      });
    }
    const next = win.next && win.next.type ? (TET[win.next.type.color] || '?') : '?';
    const dirs = ['up', 'right', 'down', 'left'];
    const illegal = {};
    if (!playing || !curp || !win.unoccupied) ['left', 'right', 'rotate', 'drop', 'none'].forEach((k) => { illegal[k] = true; });
    else {
      if (!win.unoccupied(curp.type, curp.x - 1, curp.y, curp.dir)) illegal.left = true;
      if (!win.unoccupied(curp.type, curp.x + 1, curp.y, curp.dir)) illegal.right = true;
      const nd = curp.dir === win.DIR.MAX ? win.DIR.MIN : curp.dir + 1;
      if (!win.unoccupied(curp.type, curp.x, curp.y, nd)) illegal.rotate = true;
    }
    const where = playing && curp ? `${name} rot ${dirs[curp.dir] || curp.dir} at (${curp.x}, ${curp.y})` : '-';
    return {
      score: num(win.score || 0) + '점', illegal,
      text: `Phase: ${playing ? 'playing' : 'waiting'} | Score: ${win.score || 0} | Lines: ${win.rows || 0}\n` +
        `Piece: ${where} | Next: ${next}\n` +
        'Court (10x20, . empty, letter locked, lowercase falling):\n' +
        grid.map((r) => r.join('')).join('\n')
    };
  }
  let snakeTrack = null;
  function readSnake(win, doc) {
    const b = win.playlayaBoard;
    if (!b || !b.grid || !b.grid.length || !b.grid[0]) return null;
    const grid = b.grid, rows = grid.length, cols = grid[0].length;
    const bw = b.getBlockWidth(), bh = b.getBlockHeight();
    const headEl = doc.getElementById('snake-snakehead-alive');
    let hr = -1, hc = -1;
    if (headEl && bw) {
      hc = Math.round(parseFloat(headEl.style.left) / bw);
      hr = Math.round(parseFloat(headEl.style.top) / bh);
    }
    let food = '-', length = 0;
    const lines = [];
    for (let r = 0; r < rows; r++) {
      let line = '';
      for (let c = 0; c < cols; c++) {
        const v = grid[r][c];
        const edge = r === 0 || c === 0 || r === rows - 1 || c === cols - 1;
        if (r === hr && c === hc) { line += 'O'; length++; }
        else if (v === b.getGridFoodValue()) { line += '*'; food = `(${c},${r})`; }
        else if (edge && v > 0) line += '#';
        else if (v > 0) { line += 'o'; length++; }
        else line += '.';
      }
      lines.push(line);
    }
    const st = b.getBoardState();
    const phase = st === 2 ? (b.getPaused() ? 'paused' : 'playing') : st === 1 ? 'ready' : 'welcome';
    let dir = 'none';
    if (snakeTrack && hr === snakeTrack.hr && hc === snakeTrack.hc) dir = snakeTrack.dir;
    else if (snakeTrack && hr >= 0) {
      const dr = hr - snakeTrack.hr, dc = hc - snakeTrack.hc;
      if (dr < 0) dir = 'up'; else if (dr > 0) dir = 'down';
      else if (dc < 0) dir = 'left'; else if (dc > 0) dir = 'right';
      else dir = snakeTrack.dir;
    }
    if (hr >= 0) snakeTrack = { hr, hc, dir };
    const rev = { up: 'down', down: 'up', left: 'right', right: 'left' };
    const illegal = {};
    if (phase === 'welcome') ['up', 'down', 'left', 'right'].forEach((k) => { illegal[k] = true; });
    else if (phase === 'playing' && rev[dir]) illegal[rev[dir]] = true;
    return {
      score: '길이 ' + length, illegal,
      text: `Phase: ${phase} | Length: ${length} | Dir: ${dir}\n` +
        `Head: (${hc},${hr}) | Food: ${food}\n` +
        'Board (# wall, O head, o body, * food, . empty):\n' + lines.join('\n')
    };
  }
  function readPacman(win) {
    const P = win.PACMAN;
    if (!P || !P.getUser || !P.getUser() || !P.getMap || !P.getMap()) return null;
    const user = P.getUser(), map = P.getMap(), ghosts = P.getGhosts() || [];
    const h = map.height, w = map.width;
    if (!h || !w) return null;
    const Pac = win.Pacman || {};
    const cell = (y, x) => map.block({ y, x });
    const grid = [];
    for (let y = 0; y < h; y++) {
      const row = [];
      for (let x = 0; x < w; x++) {
        const b = cell(y, x);
        row.push(b === Pac.WALL ? '#' : b === Pac.BISCUIT ? '.' : b === Pac.PILL ? 'o' : b === Pac.BLOCK ? '-' : ' ');
      }
      grid.push(row);
    }
    const at = (pos) => pos ? { x: Math.round(pos.x / 10), y: Math.round(pos.y / 10) } : null;
    const put = (pos, ch) => { const p = at(pos); if (p && grid[p.y] && grid[p.y][p.x] != null) grid[p.y][p.x] = ch; };
    const dirName = (d) => d === win.UP ? 'up' : d === win.DOWN ? 'down' : d === win.LEFT ? 'left' : d === win.RIGHT ? 'right' : 'none';
    const gbits = ghosts.map((g) => {
      const pos = g.getPosition ? g.getPosition() : null;
      put(pos, g.isVunerable && g.isVunerable() ? 'e' : 'G');
      const p = at(pos);
      return p ? `${dirName(g.getDirection ? g.getDirection() : 0)} (${p.x},${p.y})` : '-';
    });
    const up = user.getPosition();
    put(up, 'P');
    const pp = at(up);
    const phaseN = P.getState();
    const phase = phaseN === win.WAITING ? 'waiting' : phaseN === win.PAUSE ? 'paused' : phaseN === win.PLAYING ? 'playing'
      : phaseN === win.COUNTDOWN ? 'countdown' : phaseN === win.DYING ? 'dying' : phaseN === win.EATEN_PAUSE ? 'eaten' : String(phaseN);
    const score = user.theScore ? user.theScore() : 0;
    return {
      score: num(score) + '점', illegal: {},
      text: `Phase: ${phase} | Score: ${score} | Lives: ${user.getLives()} | Level: ${P.getLevel()}\n` +
        `Pac: (${pp ? pp.x : '?'},${pp ? pp.y : '?'}) dir ${dirName(user.getDirection())} | Ghosts: ${gbits.join(', ') || '-'}\n` +
        'Maze (# wall, . dot, o pill, - gate, space empty, P pac, G ghost, e eatable):\n' +
        grid.map((r) => r.join('')).join('\n')
    };
  }
  function readRacer(win) {
    if (win.speed == null || win.playerX == null) return null;
    const segs = win.segments || [];
    const held = [];
    if (win.keyLeft) held.push('left');
    if (win.keyRight) held.push('right');
    if (win.keyFaster) held.push('faster');
    if (win.keySlower) held.push('slower');
    let curve = 0;
    const ahead = [];
    if (segs.length && win.playerZ != null && win.findSegment) {
      const ps = win.findSegment((win.position || 0) + win.playerZ);
      if (ps) {
        curve = ps.curve || 0;
        for (let i = 1; i <= 6; i++) {
          const seg = segs[(ps.index + i) % segs.length];
          if (!seg) continue;
          const cars = (seg.cars || []).map((c) => fix(c.offset, 2));
          ahead.push(`+${i} curve ${fix(seg.curve, 2)} cars ${cars.join(',') || '-'}`);
        }
      }
    }
    const mph = 5 * Math.round((win.speed || 0) / 500);
    const pct = win.trackLength ? (100 * (win.position || 0) / win.trackLength) : 0;
    return {
      score: mph + ' mph', illegal: {},
      text: `Speed: ${Math.round(win.speed || 0)} (${mph} mph) | Track: ${pct.toFixed(1)}% | Lap: ${fix(win.currentLapTime, 1)}s\n` +
        `Lane: ${fix(win.playerX, 3)} | Curve: ${fix(curve, 2)} | Segments: ${segs.length}\n` +
        `Held: ${held.join('+') || 'none'}\nRoad ahead:\n` + (ahead.join('\n') || '(road still loading)')
    };
  }
  function readInvaders(win) {
    const game = win.playlayaGame;
    if (!game || !game.state) return null;
    const phase = game.state.current || 'boot';
    const bag = { texts: [], ship: null, aliens: [], shots: { bullet: 0, enemyBullet: 0 } };
    const seen = new Set();
    (function walk(obj, depth) {
      if (!obj || depth > 8 || seen.has(obj)) return;
      seen.add(obj);
      if (typeof obj.text === 'string') bag.texts.push(obj.text);
      if (obj.key === 'ship' && obj.alive) bag.ship = obj;
      if (obj.key === 'invader') bag.aliens.push(obj);
      if (obj.alive && (obj.key === 'bullet' || obj.key === 'enemyBullet')) bag.shots[obj.key]++;
      const kids = obj.children;
      if (kids && kids.length) for (let i = 0; i < kids.length; i++) walk(kids[i], depth + 1);
    })(game.world, 0);
    const pick = (label) => { const t = bag.texts.find((s) => s.indexOf(label) === 0); return t ? t.slice(label.length).trim() : '-'; };
    let formation = '(no aliens yet)';
    if (bag.aliens.length) {
      const pts = bag.aliens.map((a) => ({ x: Math.round(a.x), y: Math.round(a.y), on: !!(a.alive && a.exists !== false) }));
      const ys = [...new Set(pts.map((p) => p.y))].sort((a, b) => a - b);
      const xs = [...new Set(pts.map((p) => p.x))].sort((a, b) => a - b);
      formation = ys.map((y) => xs.map((x) => { const p = pts.find((q) => q.x === x && q.y === y); return !p ? ' ' : p.on ? 'X' : '.'; }).join('')).join('\n');
    }
    const alive = bag.aliens.filter((a) => a.alive).length;
    const ship = bag.ship ? Math.round(bag.ship.x) : '-';
    const score = pick('Score:');
    return {
      score: (score === '-' ? '0' : score) + '점', illegal: phase === 'Play' ? {} : { left: true, right: true, noop: true },
      text: `Phase: ${phase} | Score: ${score} | Health: ${pick('Health:')} | Lives: ${pick('Lives:')}\n` +
        `Ship x: ${ship} | Aliens: ${alive}/${bag.aliens.length || 0} | Bullets ship ${bag.shots.bullet} alien ${bag.shots.enemyBullet}\n` +
        'Formation (X alive, . gone):\n' + formation
    };
  }
  function readSokoban(win) {
    const b = win.sokoban;
    if (!b || !b.board) return null;
    const onGoals = b.board.reduce((n, row) => n + row.filter((c) => c === 'success_block').length, 0);
    const lines = b.board.map((row, y) => row.map((c) => (
      c === 'wall' ? '#' : c === 'block' ? '$' : c === 'success_block' ? '*' : c === 'player' ? '@' : c === 'void' ? '+' : '.'
    )).join(''));
    let coords = null;
    try { coords = b.findPlayerCoords(); } catch (e) { coords = null; }
    const step = { up: [-1, 0], down: [1, 0], left: [0, -1], right: [0, 1] };
    const legal = {};
    if (coords) {
      for (const name of Object.keys(step)) {
        const [dy, dx] = step[name];
        const y = coords.y + dy, x = coords.x + dx;
        const cell = b.board[y] && b.board[y][x];
        if (cell === 'empty' || cell === 'void') legal[name] = true;
        else if (cell === 'block' || cell === 'success_block') {
          const dest = b.board[y + dy] && b.board[y + dy][x + dx];
          legal[name] = dest === 'empty' || dest === 'void';
        } else legal[name] = false;
      }
    }
    const won = b.goalCount != null && onGoals === b.goalCount;
    const illegal = {};
    ['up', 'down', 'left', 'right'].forEach((k) => { if (won || !legal[k]) illegal[k] = true; });
    const under = coords && b.levelMap && b.levelMap[coords.y] && b.levelMap[coords.y][coords.x];
    const you = coords ? ` | You: (${coords.x},${coords.y})${under === 'void' ? ' on a goal' : ''}` : '';
    return {
      score: (b.level || 1) + '레벨', illegal,
      text: `Level: ${b.level || 1} | Boxes on goals: ${onGoals}/${b.goalCount == null ? '?' : b.goalCount}${you}${won ? ' | won' : ''}\n` +
        'Board (# wall, . floor, + goal, $ box, * box on goal, @ you):\n' + lines.join('\n')
    };
  }
  function marioPhase(win, st) {
    const M = win.Mario; if (!M || !st) return 'loading';
    if (M.LevelState && st instanceof M.LevelState) return 'level';
    if (M.MapState && st instanceof M.MapState) return 'map';
    if (M.TitleState && st instanceof M.TitleState) return 'title';
    if (M.LoseState && st instanceof M.LoseState) return 'lose';
    if (M.WinState && st instanceof M.WinState) return 'win';
    if (M.LoadingState && st instanceof M.LoadingState) return 'loading';
    return 'other';
  }
  function readMario(win) {
    const app = win.playlayaApp;
    const st = app && app.stateContext && app.stateContext.State;
    if (!st) return null;
    const phase = marioPhase(win, st);
    const m = win.Mario && win.Mario.MarioCharacter;
    const lives = m ? m.Lives : 3, coins = m ? m.Coins : 0;
    const head = `Phase: ${phase} | Lives: ${lives} | Coins: ${coins}`;
    if (phase === 'level' && m && m.World && m.World.Level) {
      const level = m.World.Level, Tile = win.Mario.Tile;
      const mx = m.X / 16 | 0, my = m.Y / 16 | 0;
      const enemies = [];
      const objs = (m.World.Sprites && m.World.Sprites.Objects) || [];
      for (let i = 0; i < objs.length; i++) {
        const s = objs[i];
        if (!s || s === m || s.X == null) continue;
        enemies.push([s.X / 16 | 0, s.Y / 16 | 0]);
      }
      const rows = [];
      for (let y = my - 5; y <= my + 5; y++) {
        let line = '';
        for (let x = mx - 8; x <= mx + 8; x++) {
          if (x === mx && y === my) { line += 'M'; continue; }
          if (enemies.some((e) => e[0] === x && e[1] === y)) { line += 'E'; continue; }
          if (!level || y < 0 || x < 0 || y >= level.Height || x >= level.Width) { line += ' '; continue; }
          const beh = (Tile.Behaviors && Tile.Behaviors[level.GetBlock(x, y) & 255]) || 0;
          if (beh & Tile.PickUpable) line += 'o';
          else if (beh & Tile.Bumpable) line += '?';
          else if (beh & (Tile.BlockAll | Tile.BlockUpper | Tile.BlockLower)) line += '#';
          else line += '.';
        }
        rows.push(line);
      }
      const face = m.Facing === -1 ? 'left' : m.Facing === 1 ? 'right' : 'none';
      const size = m.Fire ? 'fire' : m.Large ? 'big' : 'small';
      return {
        score: '목숨 ' + lives, illegal: {},
        text: `${head} | Time: ${m.World.TimeLeft | 0}\n` +
          `X: ${fix(m.X, 1)} Y: ${fix(m.Y, 1)} | vx: ${fix(m.Xa, 2)} vy: ${fix(m.Ya, 2)} | Facing: ${face} | Ground: ${m.OnGround ? 'yes' : 'no'} | Size: ${size}\n` +
          'Nearby (M mario, # solid, ? brick, o coin, E enemy, . empty):\n' + rows.join('\n')
      };
    }
    if (phase === 'map') {
      return {
        score: '목숨 ' + lives, illegal: {},
        text: `${head} | World: ${st.WorldNumber + 1}\nMap tile: (${st.XMario / 16 | 0}, ${st.YMario / 16 | 0}) | Can enter: ${st.CanEnterLevel ? 'yes' : 'no'}`
      };
    }
    return {
      score: '목숨 ' + lives, illegal: {},
      text: head + (phase === 'title' ? '\nPress S to start' : '')
    };
  }
  function readFlappy(win) {
    if (win.currentstate == null || win.position == null) return null;
    const phase = ['splash', 'playing', 'score'][win.currentstate] || String(win.currentstate);
    const pipes = win.pipes || [], gaps = [];
    for (let i = 0; i < pipes.length; i++) {
      const p = pipes[i];
      if (!p || !p.position || (p.parent && !p.parent().length)) continue;
      const upper = p.children ? p.children('.pipe_upper') : null;
      const top = upper && upper.height ? Math.round(upper.height()) : 0;
      gaps.push(`x ${Math.round(p.position().left)} gap-top ${top} h ${win.pipeheight}`);
    }
    return {
      score: num(win.score || 0) + '점', illegal: {},
      text: `Phase: ${phase} | Score: ${win.score || 0}\n` +
        `Bird y: ${Math.round(win.position)} | vy: ${fix(win.velocity, 2)} | rot: ${Math.round(win.rotation || 0)}\n` +
        `Pipes: ${pipes.length}\n` + (gaps.length ? 'Gaps:\n' + gaps.join('\n') : 'Gaps: none yet')
    };
  }
  function readBreakout(win) {
    const g = (win.Game && win.Game.current) || win.game;
    if (!g || !g.court || !g.paddle || !g.ball || !g.score || !g.is) return null;
    const court = g.court, chunk = court.chunk || 1, xs = (court.cfg && court.cfg.xchunks) || 30;
    const maxY = (court.bricks || []).reduce((m, b) => Math.max(m, b.pos.y), -1);
    const rows = [];
    for (let y = 0; y <= maxY; y++) rows.push(Array(xs).fill('.'));
    (court.bricks || []).forEach((brick) => {
      if (brick.hit || !rows[brick.pos.y]) return;
      for (let x = brick.pos.x1; x <= brick.pos.x2 && x < xs; x++) rows[brick.pos.y][x] = brick.c || '#';
    });
    const px = (g.paddle.x - court.left) / chunk, pw = g.paddle.w / chunk;
    const bx = (g.ball.x - court.left) / chunk, by = (g.ball.y - court.top) / chunk;
    const phase = g.is('menu') ? 'menu' : g.is('game') ? 'game' : 'other';
    const moving = g.paddle.dleft ? 'left' : g.paddle.dright ? 'right' : 'still';
    const illegal = {};
    if (px <= 0.05) illegal.left = true;
    if (px + pw >= xs - 0.05) illegal.right = true;
    return {
      score: num(g.score.score || 0) + '점', illegal,
      text: `Phase: ${phase} | Level: ${(g.level || 0) + 1} | Score: ${g.score.score || 0} | Lives: ${g.score.lives}\n` +
        `Ball: (${fix(bx, 2)}, ${fix(by, 2)}) v (${fix(g.ball.dx, 2)}, ${fix(g.ball.dy, 2)}) | Paddle: ${fix(px, 2)}..${fix(px + pw, 2)} ${moving}\n` +
        'Bricks (. empty, letter still up):\n' + (rows.length ? rows.map((r) => r.join('')).join('\n') : '(none)')
    };
  }
  const READ = {
    tetris: readTetris, snake: readSnake, pacman: readPacman, racer: readRacer, invaders: readInvaders,
    sokoban: readSokoban, mario: readMario, flappy: readFlappy, breakout: readBreakout
  };
  function renderOther() {
    const g = cur; if (!g || g.id === '2048' || !READ[g.id]) return;
    const stateEl = $('state'); if (!stateEl) return;
    let win = null, doc = null;
    try { win = frame.contentWindow; doc = frame.contentDocument; } catch (e) { return; }
    if (!win || !doc) return;
    const snap = READ[g.id](win, doc);
    if (!snap) return;
    stateEl.textContent = snap.text;
    scoreEl.textContent = snap.score;
    showMoves(g.id, snap.illegal);
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
    roMain.append(el('p', 'readout-label', '모델이 보는 상태창 (지금 보드)'), el('pre', 'state', '불러오는 중'));
    roMain.lastChild.id = 'state';
    roSide.append(el('p', 'readout-label', '선택지'), el('div', 'opts'));
    roSide.lastChild.id = 'opts';
    showMoves(g.id, null);
    scoreEl.textContent = '';
    note.textContent = '보드를 한 번 클릭한 뒤 키보드로 두세요. 상태창은 이 판을 텍스트로 옮긴 것이고, 선택지 글자는 2048과 같이 A, B, C… 예요. 파인튜닝 코드는 아직 2048만 있어요.';
  }

  // ---------------------------------------------------------------- picking a game
  function pick(id, focus) {
    const g = byId[id] || byId['2048'];
    cur = g; last = null; snakeTrack = null;
    observers.forEach((o) => o.disconnect()); observers = [];
    clearInterval(fitTimer); clearInterval(poll); poll = 0;
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
    const g = cur; if (!g || frame.dataset.want !== g.id) return;
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
    } else {
      renderOther();
      poll = setInterval(renderOther, 100);
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
