// PlayVLA: the sound files are not shipped, so the hit sound's "ended" event never fires and the
// score board (with the replay button) would never appear after a crash. The game already skips the
// sounds and shows the score at once on browsers it treats as incompatible; use that path everywhere.
isIncompatible.any = function () { return true; };
