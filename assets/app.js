// Japan Launch Pack - application link and sample character counts.
// No frameworks, no trackers. The form URL is set in assets/config.js.
(function () {
  "use strict";

  var config = window.JLP_CONFIG || {};

  // Count by Unicode code points, the same way scripts/jp_competitors.py does.
  function charCount(text) {
    return Array.from(text).length;
  }

  // Recompute the sample counts so the illustrative table can't drift from its text.
  function updateSampleCounts() {
    var rows = document.querySelectorAll(".sample-table tbody tr");
    rows.forEach(function (row) {
      var textCell = row.querySelector("[data-count-text]");
      var badge = row.querySelector(".count[data-limit]");
      if (!textCell || !badge) return;
      var limit = parseInt(badge.getAttribute("data-limit"), 10);
      var n = charCount(textCell.textContent.trim());
      badge.textContent = n + " / " + limit;
      badge.classList.toggle("over", n > limit);
      badge.setAttribute("aria-label", n + " of " + limit + " characters used");
    });
  }

  // Point the apply button at config.formUrl. The href in index.html is already
  // the real URL, so this only matters if config.js is changed; anything that
  // isn't an https Google Forms URL is ignored and the HTML href is kept.
  function updateApplyLink() {
    var link = document.getElementById("apply-link");
    var url = config.formUrl || "";
    if (!link || !/^https:\/\/docs\.google\.com\/forms\//.test(url)) return;
    link.href = url;
  }

  updateSampleCounts();
  updateApplyLink();
})();
