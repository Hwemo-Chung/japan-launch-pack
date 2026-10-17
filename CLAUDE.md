# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Two independent pieces that share one concept (store character limits counted in Unicode code points):

1. **Landing page** for "Japan Launch Pack", a fixed-price Japanese App Store / Google Play listing service. It's a static single page (`index.html` + `assets/`) for GitHub Pages: no build step, no frameworks, no trackers, system fonts. `.nojekyll` makes Pages serve files as-is.
2. **Research CLI** `scripts/jp_competitors.py`: Japan-store competitor search, keyword extraction, and metadata limit checks. Python 3 stdlib only. `google-play-scraper` is optional and only used by the `play` subcommand.

`TASK.md` is the original spec. Check it before changing copy or features.

## Commands

```sh
python3 -m http.server 8000                       # serve the site at http://localhost:8000
python3 -m unittest discover -s tests -v          # all tests (offline, no network)
python3 -m unittest tests.test_limits.IosCheckTest.test_within_limits   # single test (run from repo root)

python3 scripts/jp_competitors.py ios --term "家計簿" --limit 5          # live iTunes Search API call
python3 scripts/jp_competitors.py check --platform ios --title "..." --subtitle "..." --keywords "a,b,c"
python3 scripts/jp_competitors.py check --platform play --title "..." --short "..."
```

There's no linter or formatter configured. `out/` (research JSON output) is git-ignored.

## Architecture notes

### Landing page / form
- Applications go through an external Google Form. The `#apply` section has no embedded form, only an intro, the list of what the form asks, the privacy note, and an "Open the application form" button (`#apply-link`, `target="_blank" rel="noopener noreferrer"`).
- All other Apply CTAs (nav, hero, final CTA, footer contact) link to `#apply` in-page on purpose, so visitors read the privacy note before leaving the site. Don't point them straight at the Google Form.
- The form URL is in two places that must stay in sync: the `href` of `#apply-link` in `index.html` (so it works without JS) and `formUrl` in `assets/config.js` (`window.JLP_CONFIG`). `assets/app.js` (an IIFE in ES5 style using `var` and `function`; keep it that way) copies `formUrl` into the href only if it matches `https://docs.google.com/forms/`.
- The illustrative sample table in `index.html` gets its counts from `updateSampleCounts()` in `app.js`. It reads `[data-count-text]` cells and `.count[data-limit]` badges, so you only edit the text and the badges recompute. `charCount` uses `Array.from(text).length` to match Python's `len()`.

### `jp_competitors.py`
- Flow: `build_parser` → `cmd_ios` / `cmd_play` / `cmd_check`. Raw API results go through `normalize_ios` / `normalize_play` into one common app dict, then `emit_research` handles keywords, the table or JSON output, and the optional `--out` file. The `description` field is used for keyword extraction but removed from the output.
- `LIMITS` holds the store limits (iOS title/subtitle 30, keywords 100; Play title 30, short 80). `check_ios` adds warnings about the keyword field (spaces around commas, `、`/`，`, empty entries, NFKC-case-insensitive duplicates, words already in title/subtitle). Japanese terms count as "already in title" by substring match; Latin terms only on word boundaries.
- Keyword extraction (`tokenize_ja` / `extract_keywords`) is a regex heuristic, not a morphological analyzer. It NFKC-normalizes the text, then collects katakana runs, kanji runs plus 2/3-grams of runs with 4+ characters, kanji+hiragana endings that aren't particles, and Latin words. Ranking is by number of apps, then total count. A substring is dropped when a longer token has identical stats.
- `--app-id` looks up the app, searches by the main part of its name and then by its genre, removes duplicates, and lists same-genre apps first.
- The exit codes are part of the interface: `0` ok, `1` limit exceeded, `2` usage error / scraper missing, `3` network/API error.
- Tests import the script by putting `scripts/` on `sys.path`, so keep it importable: no side effects at import time.

## Content constraints (from TASK.md)

- Never claim the seller is a native Japanese speaker. They are described as a "Tokyo-based app engineer", and the Japanese copy is AI-assisted research plus human review. Native proofreading may be offered later but isn't promised.
- No employer names, no invented statistics, no ranking or download guarantees.
- Pricing messaging must stay explicit: "Apply now, pay later. No payment is collected on this page."
- Tone is plain and confident, with no hype and no emojis. Keep the page accessible and keep the OG meta tags.
- Don't `git push`.
