# Changes to the vendored 2048

Upstream: gabrielecirulli/2048 (MIT, see LICENSE.txt and UPSTREAM), copied from PlayJev's `demo/games/2048/`.

PlayLaya changes:

- Removed PlayJev's training/demo hooks from `<head>` (`pj_silence.js`, `_shared/pj_shim.js`, `pj_hook.js`,
  `pj_bridge.js`) and deleted `pj_hook.js`, so the page is the plain upstream game played with arrow keys or swipes.
- Added `style/playlaya_embed.css` and a one-line script: with `?embed` in the URL the text below the board is
  hidden, which is how the front page frames the game. Without `?embed` the page is unchanged.
