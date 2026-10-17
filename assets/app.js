// Japan Launch Pack - form handling and sample character counts.
// No frameworks, no trackers. Backend is chosen in assets/config.js.
(function () {
  "use strict";

  var config = window.JLP_CONFIG || { provider: "none" };

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

  function isGoogleFormReady() {
    if (config.provider !== "google_form") return false;
    if (!/^https:\/\/docs\.google\.com\/forms\/.+\/formResponse$/.test(config.googleFormAction || "")) {
      return false;
    }
    var fields = config.googleFormFields || {};
    return ["email", "urls"].every(function (k) {
      return /^entry\.\d+$/.test(fields[k] || "");
    });
  }

  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  function setError(input, errEl, message) {
    if (message) {
      input.setAttribute("aria-invalid", "true");
      if (errEl) errEl.textContent = message;
    } else {
      input.removeAttribute("aria-invalid");
      if (errEl) errEl.textContent = "";
    }
    return !message;
  }

  function validate(form) {
    var email = form.elements.email;
    var urls = form.elements.urls;
    var consent = form.elements.consent;
    var firstInvalid = null;

    var emailVal = email.value.trim();
    var emailMsg = !emailVal ? "Please enter your email address."
      : !EMAIL_RE.test(emailVal) ? "Please enter a valid email address." : "";
    if (!setError(email, document.getElementById("f-email-err"), emailMsg)) firstInvalid = firstInvalid || email;

    var urlsMsg = urls.value.trim() ? "" : "Please add at least one store URL (or write \"not live\").";
    if (!setError(urls, document.getElementById("f-urls-err"), urlsMsg)) firstInvalid = firstInvalid || urls;

    var consentMsg = consent.checked ? "" : "Please confirm you agree to how your information is used.";
    if (!setError(consent, document.getElementById("f-consent-err"), consentMsg)) firstInvalid = firstInvalid || consent;

    if (firstInvalid) firstInvalid.focus();
    return !firstInvalid;
  }

  function collect(form) {
    var platform = form.querySelector('input[name="platform"]:checked');
    return {
      name: form.elements.name.value.trim(),
      email: form.elements.email.value.trim(),
      urls: form.elements.urls.value.trim(),
      platform: platform ? platform.value : "",
      budget: form.elements.budget.value,
      timeline: form.elements.timeline.value,
      notes: form.elements.notes.value.trim()
    };
  }

  function showSuccess(form) {
    var success = document.getElementById("form-success");
    form.hidden = true;
    success.hidden = false;
    success.focus();
  }

  function initForm() {
    var form = document.getElementById("apply-form");
    if (!form) return;
    var submit = document.getElementById("f-submit");
    var status = document.getElementById("form-status");
    var closedNote = document.getElementById("form-closed");
    var ready = isGoogleFormReady();

    if (!ready) {
      // provider "none" (or an incomplete Google Form config): show the form, but don't accept submissions.
      closedNote.hidden = false;
      submit.disabled = true;
      submit.setAttribute("aria-describedby", "form-closed");
      submit.textContent = "Applications open in a few days";
    }

    // Clear an error as soon as the user fixes the field.
    ["email", "urls", "consent"].forEach(function (name) {
      var el = form.elements[name];
      var evt = el.type === "checkbox" ? "change" : "input";
      el.addEventListener(evt, function () {
        if (el.getAttribute("aria-invalid") === "true") validate(form);
      });
    });

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      status.textContent = "";
      status.classList.remove("is-error");
      if (!ready) return;
      if (!validate(form)) return;

      // Honeypot filled in: pretend success, send nothing.
      if (form.elements.website.value) {
        showSuccess(form);
        return;
      }

      var data = collect(form);
      var body = new URLSearchParams();
      Object.keys(config.googleFormFields).forEach(function (key) {
        var entry = config.googleFormFields[key];
        if (/^entry\.\d+$/.test(entry) && data[key] !== undefined) body.append(entry, data[key]);
      });

      submit.disabled = true;
      status.textContent = "Sending...";

      // Google Forms doesn't send CORS headers, so the response is opaque.
      // A resolved fetch means the request left the browser.
      fetch(config.googleFormAction, {
        method: "POST",
        mode: "no-cors",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: body.toString()
      }).then(function () {
        status.textContent = "";
        showSuccess(form);
      }).catch(function () {
        submit.disabled = false;
        status.classList.add("is-error");
        status.textContent = "Sorry, the application couldn't be sent. Please check your connection and try again.";
      });
    });
  }

  updateSampleCounts();
  initForm();
})();
