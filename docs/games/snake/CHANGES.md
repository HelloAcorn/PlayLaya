# Changes to the vendored Snake

Upstream: [patorjk/JavaScript-Snake](https://github.com/patorjk/JavaScript-Snake) (MIT, see `LICENSE` and `UPSTREAM`), copied from PlayJev's `demo/games/snake/` (OmniJev/PlayJev).

PlayVLA changes:

- `src/index.html`: removed PlayJev's training/demo scripts from `<head>` (`_shared/pj_shim.js`, `pj_hook.js`, `pj_bridge.js`) and deleted `pj_hook.js`, so the page runs on the real clock and the keyboard like the upstream game. Kept PlayJev's `pj_silence.js` (now `docs/pj_silence.js`, Apache-2.0), which stops the page from requesting the sound files that are not shipped.
- `src/js/init.js`: `window.playlayaBoard = mySnakeBoard` after the board is created, so the front page can read the grid and phase. No gameplay change.
