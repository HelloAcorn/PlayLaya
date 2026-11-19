# Changes to the vendored Floppy Bird

Upstream: [nebez/floppybird](https://github.com/nebez/floppybird) (Apache-2.0, see `LICENSE` and `UPSTREAM`), copied from PlayJev's `demo/games/flappy/` (OmniJev/PlayJev).

PlayVLA changes:

- `index.html`: removed PlayJev's training/demo scripts from `<head>` (`_shared/pj_shim.js`, `pj_hook.js`, `pj_bridge.js`) and deleted `pj_hook.js`, so the page runs on the real clock and the keyboard like the upstream game. Kept PlayJev's `pj_silence.js` (now `docs/pj_silence.js`, Apache-2.0), which stops the page from requesting the sound files that are not shipped.
- Added `<link rel="icon" href="data:,">` so the browser does not ask the site root for `/favicon.ico`.
- Added `js/playlaya_no_sound.js` after `js/main.js`: the sound files are not shipped, so the crash sound's `ended` event never fires and the score board with the replay button would never appear. The script sets `isIncompatible.any` to return true, the game's own path that skips the sounds and shows the score at once.
- PlayJev's copy already removed the third-party analytics script line from `index.html`.
