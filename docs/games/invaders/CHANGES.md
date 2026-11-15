# Changes to the vendored Space Invaders

Upstream: [StrykerKKD/SpaceInvaders](https://github.com/StrykerKKD/SpaceInvaders) (MIT, see `LICENSE` and `UPSTREAM`), copied from PlayJev's `demo/games/invaders/` (OmniJev/PlayJev).

PlayLaya changes:

- `index.html`: removed PlayJev's training/demo scripts from `<head>` (`_shared/pj_shim.js`, `pj_hook.js`, `pj_bridge.js`) and deleted `pj_hook.js`, so the page runs on the real clock and the keyboard like the upstream game. Kept PlayJev's `pj_silence.js` (now `docs/pj_silence.js`, Apache-2.0), which stops the page from requesting the sound files that are not shipped.
- Added `<link rel="icon" href="data:,">` so the browser does not ask the site root for `/favicon.ico`.
- `assets/javascript/main.js`: `window.playlayaGame = _game` so the front page can read the Phaser sprites (ship, aliens, HUD text). No gameplay change.
