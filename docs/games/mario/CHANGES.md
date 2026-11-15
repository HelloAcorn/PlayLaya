# Changes to the vendored Infinite Mario

Upstream: [robertkleffner/mariohtml5](https://github.com/robertkleffner/mariohtml5) (Unlicense, see `LICENSE.md` and `UPSTREAM`), copied from PlayJev's `demo/games/mario/` (OmniJev/PlayJev).

PlayLaya changes:

- `main.html`: removed PlayJev's training/demo scripts from `<head>` (`_shared/pj_shim.js`, `pj_hook.js`, `pj_bridge.js`) and deleted `pj_hook.js`, so the page runs on the real clock and the keyboard like the upstream game. Kept PlayJev's `pj_silence.js` (now `docs/pj_silence.js`, Apache-2.0), which stops the page from requesting the sound files that are not shipped.
- Added `<link rel="icon" href="data:,">` so the browser does not ask the site root for `/favicon.ico`.
- `main.html`: upstream starts the game from `$(document).ready(...)` with jQuery from a Google CDN. PlayJev's copy no longer loads that CDN script, so the start line now uses `document.addEventListener("DOMContentLoaded", ...)` instead. Nothing else changed.
- The MIDI music files are not shipped (PlayJev removed them), so the game is silent.
