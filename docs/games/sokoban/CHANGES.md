# Changes to the vendored Sokoban

Upstream: [taniarascia/sokoban](https://github.com/taniarascia/sokoban) (MIT, see `LICENSE` and `UPSTREAM`), copied from PlayJev's `demo/games/sokoban/` (OmniJev/PlayJev).

PlayVLA changes:

- `index.html`: removed PlayJev's training/demo scripts from `<head>` (`_shared/pj_shim.js`, `pj_hook.js`, `pj_bridge.js`) and deleted `pj_hook.js`, `pj.json`, so the page runs on the real clock and the keyboard like the upstream game. Kept PlayJev's `pj_silence.js` (now `docs/pj_silence.js`, Apache-2.0), which stops the page from requesting the sound files that are not shipped.
- Added `<link rel="icon" href="data:,">` so the browser does not ask the site root for `/favicon.ico`.
- `Sokoban.js`, `script.js`, `levels/` are PlayJev's copy, which carries PlayJev's vendor patch (Microban level set, `window.sokoban` handle, chain push refused; see PlayJev `games/sokoban/NOTES.md`).
- `levels/microban.js` is Microban by David W. Skinner; his terms and the credit are in `levels/CREDITS.md` (copied from PlayJev).
