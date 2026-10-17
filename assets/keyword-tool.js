/* Japan Launch Pack: keyword field tool. Runs entirely in the browser; no network calls. */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) { module.exports = api; }
  root.JLPKeywords = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var LIMITS = { iosTitle: 30, iosSubtitle: 30, iosKeywords: 100, playTitle: 30, playShort: 80 };

  function len(s) { return Array.from(s || "").length; }

  function splitKeywords(text) {
    return String(text || "")
      .split(/[,\u3001\uFF0C\u060C;\uFF1B\n\r\t \u3000]+/)
      .map(function (s) { return s.trim(); })
      .filter(Boolean);
  }

  function normalizeOne(s, nfkc) { s = s.trim(); return nfkc && s.normalize ? s.normalize("NFKC") : s; }
  function keyOf(s) { return s.toLowerCase(); }

  /* Returns { keywords, duplicates, removedFromTitle } */
  function processKeywords(text, opts) {
    opts = opts || {};
    var nfkc = opts.nfkc !== false;
    var title = normalizeOne(String(opts.title || "") + " " + String(opts.subtitle || ""), nfkc).toLowerCase();
    var seen = {}, out = [], dups = [], removed = [];
    splitKeywords(text).forEach(function (raw) {
      var w = normalizeOne(raw, nfkc);
      if (!w) return;
      var k = keyOf(w);
      if (seen[k]) { dups.push(w); return; }
      seen[k] = true;
      if (opts.removeTitleWords && title.trim() && title.indexOf(k) !== -1) { removed.push(w); return; }
      out.push(w);
    });
    return { keywords: out, duplicates: dups, removedFromTitle: removed };
  }

  function joinKeywords(list) { return list.join(","); }

  /* Drops keywords from the end until the joined string fits. Returns { keywords, dropped } */
  function fitToLimit(list, limit) {
    limit = limit || LIMITS.iosKeywords;
    var kept = list.slice(), dropped = [];
    while (kept.length && len(joinKeywords(kept)) > limit) { dropped.unshift(kept.pop()); }
    return { keywords: kept, dropped: dropped };
  }

  function check(value, limit) { var n = len(value); return { count: n, limit: limit, remaining: limit - n, over: n > limit }; }

  return { LIMITS: LIMITS, len: len, splitKeywords: splitKeywords, processKeywords: processKeywords,
           joinKeywords: joinKeywords, fitToLimit: fitToLimit, check: check };
});

/* UI wiring (browser only) */
(function () {
  if (typeof document === "undefined") return;
  document.addEventListener("DOMContentLoaded", function () {
    var K = window.JLPKeywords;
    var $ = function (id) { return document.getElementById(id); };
    var input = $("kw-input"); if (!input) return;
    var lastResult = [];

    function setCounter(el, value, limit) {
      var c = K.check(value, limit);
      el.textContent = c.count + " / " + limit + (c.over ? "  (" + (-c.remaining) + " over)" : "  (" + c.remaining + " left)");
      el.classList.toggle("over", c.over);
    }

    function render() {
      var r = K.processKeywords(input.value, {
        nfkc: $("opt-nfkc").checked, removeTitleWords: $("opt-title").checked,
        title: $("ios-title").value, subtitle: $("ios-subtitle").value
      });
      lastResult = r.keywords;
      var joined = K.joinKeywords(r.keywords);
      $("kw-output").value = joined;
      setCounter($("kw-count"), joined, K.LIMITS.iosKeywords);
      var notes = [];
      if (r.duplicates.length) notes.push("Removed duplicates: " + r.duplicates.join(", "));
      if (r.removedFromTitle.length) notes.push("Removed (already in title/subtitle): " + r.removedFromTitle.join(", "));
      $("kw-notes").textContent = notes.join(" | ");
      [["ios-title", K.LIMITS.iosTitle], ["ios-subtitle", K.LIMITS.iosSubtitle],
       ["play-title", K.LIMITS.playTitle], ["play-short", K.LIMITS.playShort]].forEach(function (p) {
        setCounter($(p[0] + "-count"), $(p[0]).value, p[1]);
      });
    }

    ["kw-input", "ios-title", "ios-subtitle", "play-title", "play-short"].forEach(function (id) { $(id).addEventListener("input", render); });
    ["opt-nfkc", "opt-title"].forEach(function (id) { $(id).addEventListener("change", render); });

    $("btn-fit").addEventListener("click", function () {
      var f = K.fitToLimit(lastResult, K.LIMITS.iosKeywords);
      input.value = f.keywords.join(", ");
      render();
      $("kw-dropped").textContent = f.dropped.length ? "Dropped to fit 100: " + f.dropped.join(", ") : "Already fits in 100 characters.";
    });

    $("btn-copy").addEventListener("click", function () {
      var out = $("kw-output"), msg = $("copy-msg");
      var done = function () { msg.textContent = "Copied."; setTimeout(function () { msg.textContent = ""; }, 2000); };
      if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(out.value).then(done, function () { out.select(); document.execCommand("copy"); done(); }); }
      else { out.select(); document.execCommand("copy"); done(); }
    });
    render();
  });
})();
