// PlayVLA: the sound files are not shipped, and Pacman only binds the keyboard after every sound
// reports canplaythrough. This silent stand-in calls each load callback at once, so the game starts.
// Same stub as PlayJev's games/pacman/pj_hook.js (OmniJev/PlayJev, Apache-2.0).
Pacman.Audio = function () {
  return { load: function (name, path, cb) { if (typeof cb === 'function') cb(); },
           play: function () {}, pause: function () {}, resume: function () {}, disableSound: function () {} };
};
