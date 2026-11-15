# Changes to the vendored Pacman

Upstream: [daleharvey/pacman](https://github.com/daleharvey/pacman) (WTFPL, see `LICENSE` and `UPSTREAM`), copied from PlayJev's `demo/games/pacman/` (OmniJev/PlayJev).

PlayLaya changes:

- `index.html`: removed PlayJev's training/demo scripts from `<head>` (`_shared/pj_shim.js`, `pj_hook.js`, `pj_bridge.js`) and deleted `pj_hook.js`, so the page runs on the real clock and the keyboard like the upstream game. Kept PlayJev's `pj_silence.js` (now `docs/pj_silence.js`, Apache-2.0), which stops the page from requesting the sound files that are not shipped.
- Added `<link rel="icon" href="data:,">` so the browser does not ask the site root for `/favicon.ico`.
- Added `playlaya_silent_audio.js` after `pacman.js`: the sound files are not shipped, and the game only binds the keyboard once every sound reports `canplaythrough`, so this silent stand-in (same stub as PlayJev's hook) calls each load callback at once.
- `pacman.js` is PlayJev's copy, which carries PlayJev's additive vendor patch (16 lines exposing `PACMAN.getState()` and similar getters; no logic or rendering change).
