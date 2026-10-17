# Japan Launch Pack

A static, single-page site for Japan Launch Pack, a fixed-price service that writes Japanese App Store and Google Play listings for indie apps. The repo also includes a small research script for looking at Japanese competitors and checking store character limits.

- `index.html`, `assets/`: the landing page (GitHub Pages ready, no build step, no frameworks, no trackers)
- `case-study-picbatch.html`: sample analysis run on the founder's own pre-launch Android app, PicBatch. Raw search results and `check` output it was built from are in `case-study/data/`
- `scripts/jp_competitors.py`: competitor search, keyword extraction and character-limit checks
- `tests/test_limits.py`: offline unit tests for the checker and keyword extractor

## Run the site locally

```sh
python3 -m http.server 8000
# open http://localhost:8000
```

To publish on GitHub Pages, enable Pages for the repository and serve from the root of the default branch. `.nojekyll` is included so files are served as-is.

## Application form

Applications go through an external Google Form. The `#apply` section lists what the form asks (name, email, app store URL(s), platform, budget, timeline, notes) and has an "Open the application form" button that opens the form in a new tab (`target="_blank" rel="noopener noreferrer"`). Every other Apply link on the page (nav, hero, final CTA) points to `#apply`, so visitors see the privacy note before they leave the site.

The form URL lives in two places:

- `index.html`: the `href` of `#apply-link`. This is the real URL, so the button works without JavaScript.
- `assets/config.js`: `window.JLP_CONFIG.formUrl`. `assets/app.js` copies it into the button's `href` on load. Anything that isn't an `https://docs.google.com/forms/...` URL is ignored and the HTML `href` is kept.

To change the form, update both to the new public `.../viewform` URL. Validation, spam protection and storing responses are handled by Google Forms.

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
