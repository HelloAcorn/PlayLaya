// PlayVLA front page. Written here; not a copy of PlayJev demo/demo.js.
// Theme and sticky bar follow PlayJev's demo.js (Apache-2.0, docs/licenses/PlayJev-LICENSE.txt).
// The stage frames one of the ten vendored games at a time, cropped to the game's own board.
// The side text is a short description of that game. The browser does not run the model.
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
      id: '2048', title: '2048',
      entry: 'games/2048/index.html', embed: 'games/2048/index.html?embed',
      w: 540, h: 760, view: '.container',
      about: '같은 숫자 타일을 밀어 합쳐 2048 타일을 만드는 퍼즐이에요. 한 방향으로 밀면 그 줄의 타일이 모두 움직이고, 같은 숫자가 만나면 두 배가 돼요. 방향키나 스와이프로 위, 아래, 왼쪽, 오른쪽으로 밉니다.'
    },
    {
      id: 'tetris', title: 'Tetris',
      entry: 'games/tetris/index.html', embed: 'games/tetris/index.html',
      w: 680, h: 680, view: '#canvas',
      about: '위에서 내려오는 블록을 빈틈없이 쌓아 가로줄을 지우는 게임이에요. 줄을 없앨수록 점수가 오르고, 블록이 맨 위까지 쌓이면 끝나요. Space로 시작하고, 좌우로 옮기고, 위 화살표로 돌리고, 아래 화살표로 한 칸 내립니다.'
    },
    {
      id: 'snake', title: 'Snake',
      entry: 'games/snake/src/index.html', embed: 'games/snake/src/index.html',
      w: 520, h: 520, view: '.snake-playing-field',
      about: '화면을 기어 다니는 뱀이 먹이를 먹을 때마다 길어지는 게임이에요. 벽이나 자기 몸에 닿으면 끝나요. 키보드 연결을 누르거나 게임 안 Play Game으로 시작한 뒤, 방향키로 가는 방향을 바꿉니다.'
    },
    {
      id: 'pacman', title: 'Pacman',
      entry: 'games/pacman/index.html', embed: 'games/pacman/index.html',
      w: 400, h: 600, view: '#pacman canvas',
      about: '미로 안의 점을 모두 먹고 유령을 피하는 게임이에요. 큰 알약을 먹으면 잠시 유령을 잡을 수 있고, 유령에게 닿으면 목숨이 줄어요. N으로 새 게임을 시작하고, 방향키로 다음 갈림길의 방향을 고릅니다.'
    },
    {
      id: 'racer', title: 'Javascript Racer',
      entry: 'games/racer/v4.final.html', embed: 'games/racer/v4.final.html',
      w: 1100, h: 900, view: '#canvas',
      about: '앞으로 뻗은 길을 달리며 다른 차와 커브를 피하는 레이싱 게임이에요. 속도를 유지한 채 길을 벗어나지 않는 것이 목표예요. 위 또는 W로 가속하고, 아래 또는 S로 감속하고, 좌우나 A, D로 방향을 바꿉니다.'
    },
    {
      id: 'invaders', title: 'Space Invaders',
      entry: 'games/invaders/index.html', embed: 'games/invaders/index.html',
      w: 800, h: 600, view: 'canvas',
      about: '위에서 내려오는 외계인을 막으며 점수를 올리는 슈팅 게임이에요. 외계인이 바닥에 닿거나 목숨이 없으면 끝나요. Space로 시작하고, 좌우 방향키로 움직이면 사격은 자동이에요.'
    },
    {
      id: 'sokoban', title: 'Sokoban',
      entry: 'games/sokoban/index.html', embed: 'games/sokoban/index.html',
      w: 1100, h: 960, view: 'canvas',
      about: '창고 안에서 상자를 밀어 목표 칸에 모두 넣는 퍼즐이에요. 상자는 밀기만 할 수 있어서, 한 번 잘못 밀면 다시 빼기 어려워요. 방향키로 이동하고 상자를 밀며, 처음부터 버튼으로 그 판을 다시 시작합니다.'
    },
    {
      id: 'mario', title: 'Infinite Mario',
      entry: 'games/mario/main.html', embed: 'games/mario/main.html',
      w: 660, h: 520, view: '#canvas',
      about: '오른쪽으로 달리며 적을 피하고 코인을 모으는 플랫폼 게임이에요. 구덩이에 빠지거나 적에게 맞으면 목숨이 줄고, 깃발에 닿으면 스테이지를 클리어해요. S로 시작하고 점프하고, 좌우로 이동하고, A로 달리거나 불꽃을 씁니다.'
    },
    {
      id: 'flappy', title: 'Floppy Bird',
      entry: 'games/flappy/index.html', embed: 'games/flappy/index.html',
      w: 320, h: 525, view: '#gamescreen',
      about: '파이프 사이를 새가 날아 통과하는 게임이에요. 한 번 누르면 위로 솟고, 가만히 두면 아래로 떨어지며, 파이프나 땅에 닿으면 끝나요. Space나 클릭, 탭으로 날갯짓하고, 죽은 뒤 Space로 다시 시작합니다.'
    },
    {
      id: 'breakout', title: 'Breakout',
      entry: 'games/breakout/index.html', embed: 'games/breakout/index.html',
      w: 700, h: 540, view: '#canvas',
      about: '패들로 공을 튕겨 위쪽 벽돌을 모두 깨는 게임이에요. 공이 바닥으로 빠지면 목숨이 줄고, 벽돌을 다 깨면 다음 판으로 넘어가요. Space나 Enter로 공을 발사하고, 좌우 또는 A, D로 패들을 움직입니다.'
    }
  ];

  const $ = (id) => document.getElementById(id);
  const hero = $('hero'), frame = $('game'), view = $('hero-view');
  const titleEl = $('hero-title'), blurbEl = $('game-blurb'), openEl = $('btn-open'), newBtn = $('btn-new');
  if (!hero || !frame || !blurbEl) return;
  const byId = Object.fromEntries(GAMES.map((g) => [g.id, g]));

  let cur = null, fitTimer = 0;

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

  // ---------------------------------------------------------------- picking a game
  function pick(id, focus) {
    const g = byId[id] || byId['2048'];
    cur = g;
    clearInterval(fitTimer);
    document.querySelectorAll('#picker button').forEach((b) => {
      const on = b.dataset.game === g.id; b.classList.toggle('on', on); b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    document.querySelectorAll('#grid .card').forEach((c) => c.classList.toggle('active', c.dataset.game === g.id));
    titleEl.textContent = g.title; frame.title = g.title;
    blurbEl.textContent = g.about;
    openEl.href = g.entry;
    newBtn.textContent = g.id === '2048' ? '새 게임' : '처음부터';
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
