# Japan Launch Pack

A static, single-page site for Japan Launch Pack, a fixed-price service that writes Japanese App Store and Google Play listings for indie apps. The repo also includes a small research script for looking at Japanese competitors and checking store character limits.

- `index.html`, `assets/`: the landing page (GitHub Pages ready, no build step, no frameworks, no trackers)
- `scripts/jp_competitors.py`: competitor search, keyword extraction and character-limit checks
- `tests/test_limits.py`: offline unit tests for the checker and keyword extractor

## Run the site locally

```sh
python3 -m http.server 8000
# open http://localhost:8000
```

To publish on GitHub Pages, enable Pages for the repository and serve from the root of the default branch. `.nojekyll` is included so files are served as-is.

## Switching the form provider

The apply form posts to whatever backend `assets/config.js` selects.

### `provider: "none"` (default)

The form is visible but the submit button is disabled, and the page says "Applications open in a few days". Nothing is sent anywhere.

### `provider: "google_form"`

Answers are POSTed to a Google Form with `fetch(..., { mode: "no-cors" })` as `application/x-www-form-urlencoded`, and an inline success message is shown.

1. Create a Google Form with short-answer or paragraph questions for: name, email, app URLs, platform, budget, timeline, notes. Plain text questions are the simplest. If you use multiple-choice questions, their options must match the form values exactly (`iOS`, `Android`, `Both`; `$49 founding`, `$99`, `$149`, `Not sure`; `ASAP`, `Within 1 month`, `1–3 months`, `Just exploring`).
2. Find the entry IDs: open the form, choose the three-dot menu, then **Get pre-filled link**, fill every field with a dummy value and copy the link. Each field appears as `entry.123456789=...`.
3. Take the form's public URL (`https://docs.google.com/forms/d/e/<ID>/viewform`) and replace `viewform` with `formResponse`.
4. Edit `assets/config.js`:

```js
window.JLP_CONFIG = {
  provider: "google_form",
  googleFormAction: "https://docs.google.com/forms/d/e/<ID>/formResponse",
  googleFormFields: {
    name: "entry.111111111",
    email: "entry.222222222",
    urls: "entry.333333333",
    platform: "entry.444444444",
    budget: "entry.555555555",
    timeline: "entry.666666666",
    notes: "entry.777777777"
  }
};
```

If the action URL or the `email`/`urls` entry IDs are missing or still placeholders (`entry.X`), the page falls back to the "none" behaviour, so a half-finished config never accepts applications that go nowhere. With `no-cors` the browser can't read Google's response, so after setting this up, send a test application and confirm it shows up in the form's responses.

Spam protection is a hidden honeypot field (`website`). If it is filled in, the page shows success and sends nothing.

## Competitor script

Python 3 standard library only. Google Play search needs the optional [`google-play-scraper`](https://pypi.org/project/google-play-scraper/) package.

```sh
# Search the Japan App Store (iTunes Search API, country=jp, lang=ja_jp)
python3 scripts/jp_competitors.py ios --term "家計簿" --limit 20 --out out/ios_kakeibo.json

# Look up an app by its App Store id and find similar apps (searches its name and genre)
python3 scripts/jp_competitors.py ios --app-id 123456

# Search Google Play Japan (lang="ja", country="jp")
pip install google-play-scraper
python3 scripts/jp_competitors.py play --term "家計簿" --limit 20

# Character-limit checks
python3 scripts/jp_competitors.py check --platform ios --title "ポケット家計簿" --subtitle "毎日のお金をグラフで見える化" --keywords "節約,貯金,予算"
python3 scripts/jp_competitors.py check --platform play --title "ポケット家計簿" --short "レシートを撮るだけで支出を記録"
```

Research output is a table with rank, name, developer, rating, rating count, price, genre and title length, followed by the most frequent keywords across the competitors' titles and descriptions. The `Apps` column shows how many apps use each keyword.

Options for `ios` and `play`:

| Option | Meaning |
| --- | --- |
| `--limit N` | number of apps (default 20) |
| `--top N` | number of keywords to show, `0` to skip (default 30) |
| `--titles-only` | extract keywords from titles only |
| `--json` | print JSON instead of a table |
| `--out FILE` | also write JSON to a file (`out/` is git-ignored) |

`check` also accepts `--json` and `--out`.

### How keywords are extracted

Japanese is written without spaces, so the script doesn't split on whitespace. After NFKC normalisation (half-width kana to full-width, full-width Latin to ASCII) it collects:

- katakana runs (`シンプル`, `カレンダー`)
- kanji runs (`家計簿`), plus 2- and 3-character n-grams of runs of 4 or more (`家計簿管理` also gives `家計簿`)
- kanji followed by a short hiragana ending (`楽しい`), skipping particles such as の, に, で
- Latin words, lowercased

Common words (アプリ, 機能, "the", "app" and similar) are filtered out. An n-gram is dropped when it only ever appears inside a longer keyword, so `計簿` doesn't crowd the list. It is a frequency heuristic, not a morphological analyser, so review the output before using it.

### Character-limit checks

Lengths are counted in Unicode code points (Python `len()`), and the output shows the remaining characters for each field.

| Store | Field | Limit |
| --- | --- | --- |
| App Store | App name (`--title`) | 30 |
| App Store | Subtitle (`--subtitle`) | 30 |
| App Store | Keywords (`--keywords`) | 100 |
| Google Play | Title (`--title`) | 30 |
| Google Play | Short description (`--short`) | 80 |

For the iOS keyword field the script also warns about spaces around commas, Japanese commas (`、`), empty entries, duplicates, and keywords already in the app name or subtitle.

Exit codes: `0` ok, `1` a field is over its limit, `2` usage error or `google-play-scraper` not installed, `3` network/API error.

### Tests

```sh
python3 -m unittest discover -s tests -v
```

The tests don't use the network.

## License

MIT. See [LICENSE](LICENSE).
