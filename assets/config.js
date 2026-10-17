// Form backend configuration. See README.md ("Switching the form provider").
//
// provider:
//   "none"        - form is shown but submit is disabled ("Applications open in a few days").
//   "google_form" - answers are POSTed to a Google Form (formResponse endpoint).
window.JLP_CONFIG = {
  provider: "none",            // "none" | "google_form"
  googleFormAction: "",        // e.g. https://docs.google.com/forms/d/e/<ID>/formResponse
  googleFormFields: {
    name: "entry.X",
    email: "entry.X",
    urls: "entry.X",
    platform: "entry.X",
    budget: "entry.X",
    timeline: "entry.X",
    notes: "entry.X"
  }
};
