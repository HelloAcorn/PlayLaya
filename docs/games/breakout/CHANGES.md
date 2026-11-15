# Changes to the vendored Breakout

Upstream: [jakesgordon/javascript-breakout](https://github.com/jakesgordon/javascript-breakout) (MIT, see `LICENSE` and `UPSTREAM`), copied from PlayJev's `demo/games/breakout/` (OmniJev/PlayJev).

PlayLaya changes:

- `index.html`: removed PlayJev's training/demo scripts from `<head>` (`_shared/pj_shim.js`, `pj_hook.js`, `pj_bridge.js`) and deleted `pj_hook.js`, so the page runs on the real clock and the keyboard like the upstream game. Kept PlayJev's `pj_silence.js` (now `docs/pj_silence.js`, Apache-2.0), which stops the page from requesting the sound files that are not shipped.
- Added `<link rel="icon" href="data:,">` so the browser does not ask the site root for `/favicon.ico`.
- Sound files are not shipped; the sound checkbox is off by default, as upstream.
