#!/usr/bin/env python3
"""Japanese App Store / Google Play competitor research and metadata checks.

Stdlib only. Google Play search uses the optional `google-play-scraper`
package if it is installed (pip install google-play-scraper).

Examples:
  python3 scripts/jp_competitors.py ios --term "家計簿" --limit 20 --out out/ios_kakeibo.json
  python3 scripts/jp_competitors.py ios --app-id 123456
  python3 scripts/jp_competitors.py play --term "家計簿" --limit 20
  python3 scripts/jp_competitors.py check --platform ios --title "..." --subtitle "..." --keywords "..."
  python3 scripts/jp_competitors.py check --platform play --title "..." --short "..."

Exit codes: 0 ok, 1 limit check failed, 2 usage error / missing optional
dependency, 3 network or API error.

All lengths are counted in Unicode code points (Python len()).
"""

import argparse
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

# ---------------------------------------------------------------------------
# Store limits (Unicode code points)
# ---------------------------------------------------------------------------

LIMITS = {
    "ios": {"title": 30, "subtitle": 30, "keywords": 100},
    "play": {"title": 30, "short": 80},
}

FIELD_LABELS = {
    "title": "Title",
    "subtitle": "Subtitle",
    "keywords": "Keywords",
    "short": "Short description",
}


def char_len(text):
    """Length in Unicode code points, which is how this tool counts limits."""
    return len(text or "")


def _field_result(name, text, limit):
    length = char_len(text)
    return {
        "field": name,
        "text": text,
        "length": length,
        "limit": limit,
        "remaining": limit - length,
        "ok": length <= limit,
    }


def _is_latin(word):
    return bool(re.fullmatch(r"[A-Za-z0-9 .'+&-]+", word))


def _contained_in(word, text):
    """True if `word` already appears in `text`.

    Japanese has no spaces, so a substring match is the useful test. Latin
    words are matched case-insensitively on word boundaries.
    """
    if not word or not text:
        return False
    if _is_latin(word):
        pattern = r"(?<![A-Za-z0-9])" + re.escape(word) + r"(?![A-Za-z0-9])"
        return re.search(pattern, text, flags=re.IGNORECASE) is not None
    return unicodedata.normalize("NFKC", word) in unicodedata.normalize("NFKC", text)


def check_ios(title="", subtitle="", keywords=""):
    """Check iOS app name, subtitle and keyword field against App Store limits."""
    limits = LIMITS["ios"]
    fields = [
        _field_result("title", title, limits["title"]),
        _field_result("subtitle", subtitle, limits["subtitle"]),
        _field_result("keywords", keywords, limits["keywords"]),
    ]
    warnings = []

    if keywords:
        if re.search(r",[ 　]", keywords):
            warnings.append("Keywords: space after comma wastes characters; use 'a,b,c'.")
        if re.search(r"[ 　],", keywords):
            warnings.append("Keywords: space before comma wastes characters.")
        if keywords != keywords.strip():
            warnings.append("Keywords: leading or trailing whitespace.")
        if re.search(r"[、，]", keywords):
            warnings.append("Keywords: Japanese comma (、 or ，) found; the App Store separator is the ASCII comma ','.")

        raw = keywords.split(",")
        words = [w.strip() for w in raw]
        if any(not w for w in words):
            warnings.append("Keywords: empty entry (double comma or trailing comma).")

        seen = {}
        dupes = []
        for w in words:
            if not w:
                continue
            key = unicodedata.normalize("NFKC", w).lower()
            if key in seen and w not in dupes:
                dupes.append(w)
            seen.setdefault(key, w)
        if dupes:
            warnings.append("Keywords: duplicate entries: " + ", ".join(dupes))

        in_title = [w for w in words if w and (_contained_in(w, title) or _contained_in(w, subtitle))]
        if in_title:
            warnings.append(
                "Keywords: already in title/subtitle (indexed anyway, can be removed): "
                + ", ".join(dict.fromkeys(in_title))
            )

    return {
        "platform": "ios",
        "fields": fields,
        "warnings": warnings,
        "ok": all(f["ok"] for f in fields),
    }


def check_play(title="", short=""):
    """Check Google Play title and short description against limits."""
    limits = LIMITS["play"]
    fields = [
        _field_result("title", title, limits["title"]),
        _field_result("short", short, limits["short"]),
    ]
    warnings = []
    for f in fields:
        if f["text"] != f["text"].strip():
            warnings.append(FIELD_LABELS[f["field"]] + ": leading or trailing whitespace.")
    return {
        "platform": "play",
        "fields": fields,
        "warnings": warnings,
        "ok": all(f["ok"] for f in fields),
    }


# ---------------------------------------------------------------------------
# Japanese-aware keyword extraction
# ---------------------------------------------------------------------------

KATAKANA = r"ァ-ヺー"           # ァ-ヺ and the long vowel mark ー
KANJI = r"一-鿿㐀-䶿々〆ヵヶ"  # CJK + 々〆ヵヶ
HIRAGANA = r"ぁ-ゖ"

RE_KATAKANA = re.compile("[" + KATAKANA + "]{2,}")
RE_KANJI = re.compile("[" + KANJI + "]+")
RE_KANJI_HIRA = re.compile("([" + KANJI + "]+)([" + HIRAGANA + "]{1,3})")
RE_LATIN = re.compile(r"[A-Za-z][A-Za-z0-9+'&-]*[A-Za-z0-9+]|[A-Za-z]{2,}")

# Hiragana endings that are particles/copulas rather than part of a word.
PARTICLE_ENDINGS = {
    "の", "は", "が", "を", "に", "で", "と", "も", "へ", "や", "か", "な",
    "から", "まで", "より", "など", "には", "では", "とは", "にも", "でも",
    "です", "ます", "した", "して", "する", "され", "でき", "だけ", "ので",
}

STOPWORDS_JA = {
    "アプリ", "機能", "場合", "利用", "使用", "可能", "以上", "以下", "対応",
    "提供", "必要", "方法", "情報", "内容", "画面", "表示", "設定", "選択",
    "ユーザー", "サービス", "バージョン", "アップデート", "お問い合わせ",
    "問合", "本アプリ", "当アプリ", "全て", "一部", "今回", "現在", "自分",
    "皆様", "お客様", "ダウンロード", "インストール", "以外", "ため", "こと",
    "もの", "よう", "その他", "他", "等", "様",
}

STOPWORDS_EN = {
    "the", "and", "for", "with", "app", "apps", "to", "of", "in", "on", "your",
    "you", "is", "by", "from", "more", "all", "it", "this", "that", "are",
    "be", "or", "an", "as", "at", "can", "our", "we", "my", "ios", "iphone",
    "ipad", "android", "ver", "version", "http", "https", "www", "com", "jp",
}


def _kanji_ngrams(run, sizes=(2, 3)):
    """Sub n-grams of a long kanji run, e.g. 家計簿管理 -> 家計, 計簿, ..., 家計簿."""
    out = []
    if len(run) < 4:
        return out
    for n in sizes:
        for i in range(len(run) - n + 1):
            out.append(run[i:i + n])
    return out


def tokenize_ja(text, ngrams=True):
    """Extract candidate keywords from Japanese/English text.

    Token types: katakana runs (2+), kanji runs (2+), kanji + short hiragana
    ending (e.g. 楽しい), latin words (lowercased). Long kanji runs also
    yield 2/3-character sub n-grams so compounds like 家計簿管理 still match
    家計簿. Text is NFKC-normalised first (half-width kana, full-width latin).
    """
    if not text:
        return []
    text = unicodedata.normalize("NFKC", text)
    tokens = []

    for m in RE_KATAKANA.finditer(text):
        tok = m.group(0).lstrip("ー")
        if len(tok) >= 2:
            tokens.append(tok)

    for m in RE_KANJI.finditer(text):
        run = m.group(0)
        if len(run) >= 2:
            tokens.append(run)
            if ngrams:
                tokens.extend(_kanji_ngrams(run))

    for m in RE_KANJI_HIRA.finditer(text):
        kanji, hira = m.group(1), m.group(2)
        if (hira in PARTICLE_ENDINGS or hira[0] in "のはがをにでとへやも"
                or (len(hira) > 1 and hira[-1] in "のはがをにでとへやも")):
            continue
        tokens.append(kanji + hira)

    for m in RE_LATIN.finditer(text):
        tokens.append(m.group(0).lower())

    return [t for t in tokens if t not in STOPWORDS_JA and t not in STOPWORDS_EN]


def extract_keywords(docs, top=30, ngrams=True, min_apps=1):
    """Rank keywords across competitor documents.

    `docs` is a list of strings (one per app). Returns a list of dicts
    {keyword, count, apps} sorted by number of apps using the keyword, then
    total count. Sub-strings that never appear outside a longer keyword
    (same count and apps) are dropped, so 計簿 doesn't shadow 家計簿.
    """
    total = Counter()
    apps = Counter()
    for doc in docs:
        toks = tokenize_ja(doc, ngrams=ngrams)
        total.update(toks)
        apps.update(set(toks))

    ranked = sorted(total, key=lambda k: (-apps[k], -total[k], -len(k), k))
    ranked = [k for k in ranked if apps[k] >= min_apps]

    # Drop a token if a longer token contains it with identical stats.
    pool = ranked[: max(top * 4, 100)]
    keep = []
    for k in pool:
        shadowed = any(
            len(o) > len(k) and k in o and total[o] == total[k] and apps[o] == apps[k]
            for o in pool
        )
        if not shadowed:
            keep.append(k)
        if len(keep) >= top:
            break

    return [{"keyword": k, "count": total[k], "apps": apps[k]} for k in keep]


# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------

ITUNES_SEARCH = "https://itunes.apple.com/search"
ITUNES_LOOKUP = "https://itunes.apple.com/lookup"
USER_AGENT = "jp-competitors/1.0 (Python urllib)"


class FetchError(Exception):
    pass


def fetch_json(url, params, timeout=20):
    full = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise FetchError("request failed: %s (%s)" % (full, exc))


def itunes_search(term, limit=20):
    data = fetch_json(ITUNES_SEARCH, {
        "country": "jp", "lang": "ja_jp", "entity": "software",
        "term": term, "limit": max(1, min(int(limit), 200)),
    })
    return data.get("results", [])


def itunes_lookup(app_id):
    data = fetch_json(ITUNES_LOOKUP, {"id": app_id, "country": "jp", "lang": "ja_jp"})
    results = data.get("results", [])
    return results[0] if results else None


def normalize_ios(raw, rank):
    name = raw.get("trackName", "")
    return {
        "rank": rank,
        "id": raw.get("trackId"),
        "name": name,
        "developer": raw.get("artistName", ""),
        "rating": round(raw["averageUserRating"], 2) if raw.get("averageUserRating") is not None else None,
        "rating_count": raw.get("userRatingCount"),
        "price": raw.get("formattedPrice") or raw.get("price"),
        "genre": raw.get("primaryGenreName", ""),
        "genre_id": raw.get("primaryGenreId"),
        "title_length": char_len(name),
        "url": raw.get("trackViewUrl", ""),
        "description": raw.get("description", ""),
    }


def normalize_play(raw, rank):
    name = raw.get("title") or ""
    price = raw.get("price")
    if raw.get("free") or price in (0, 0.0):
        price = "Free"
    score = raw.get("score")
    return {
        "rank": rank,
        "id": raw.get("appId"),
        "name": name,
        "developer": raw.get("developer") or "",
        "rating": round(score, 2) if isinstance(score, (int, float)) else None,
        "rating_count": raw.get("ratings"),
        "price": price,
        "genre": raw.get("genre") or "",
        "genre_id": raw.get("genreId"),
        "title_length": char_len(name),
        "url": "https://play.google.com/store/apps/details?id=%s&hl=ja&gl=JP" % raw.get("appId", ""),
        "description": raw.get("description") or raw.get("summary") or "",
    }


def _search_terms_for_app(app):
    """Terms to find apps similar to `app`: the main part of its name, then its genre."""
    terms = []
    name = unicodedata.normalize("NFKC", app.get("trackName", ""))
    main = re.split(r"\s*[-–—:|｜/]\s*|\s+[(（]", name)[0].strip()
    if main:
        terms.append(main)
    genre = app.get("primaryGenreName")
    if genre:
        terms.append(genre)
    return list(dict.fromkeys(terms))


def ios_similar(app_id, limit=20):
    """Look up an app, then search by its name and genre for similar apps."""
    app = itunes_lookup(app_id)
    if not app:
        raise FetchError("no app found for id %s in the Japan store" % app_id)
    seen = {app.get("trackId")}
    merged = []
    for term in _search_terms_for_app(app):
        for raw in itunes_search(term, limit=limit * 2):
            if raw.get("trackId") in seen:
                continue
            seen.add(raw.get("trackId"))
            merged.append(raw)
    # Same primary genre first, keeping search order inside each group.
    gid = app.get("primaryGenreId")
    merged.sort(key=lambda r: 0 if r.get("primaryGenreId") == gid else 1)
    return app, merged[:limit]


def play_search(term, limit=20):
    try:
        from google_play_scraper import search  # optional dependency
    except ImportError:
        return None
    return search(term, lang="ja", country="jp", n_hits=limit)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def display_width(text):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def fit(text, width):
    """Truncate/pad `text` to a display width (CJK characters count as 2)."""
    text = "" if text is None else str(text).replace("\n", " ")
    if display_width(text) > width:
        out, w = "", 0
        for c in text:
            cw = display_width(c)
            if w + cw > width - 1:
                break
            out += c
            w += cw
        text = out + "…"
    return text + " " * max(0, width - display_width(text))


def print_table(apps):
    cols = [("#", 3), ("Name", 34), ("Developer", 22), ("Rating", 6),
            ("Ratings", 8), ("Price", 8), ("Genre", 14), ("Len", 4)]
    print("  ".join(fit(h, w) for h, w in cols))
    print("  ".join("-" * w for _, w in cols))
    for a in apps:
        rating = "" if a["rating"] is None else "%.2f" % a["rating"]
        count = "" if a["rating_count"] is None else str(a["rating_count"])
        row = [a["rank"], a["name"], a["developer"], rating, count,
               a["price"], a["genre"], a["title_length"]]
        print("  ".join(fit(v, w) for v, (_, w) in zip(row, cols)))


def print_keywords(keywords, n_apps):
    if not keywords:
        return
    print()
    print("Top keywords in competitor titles/descriptions (%d apps):" % n_apps)
    print("  " + fit("Keyword", 24) + "  " + fit("Count", 6) + "  Apps")
    for k in keywords:
        print("  " + fit(k["keyword"], 24) + "  " + fit(k["count"], 6) + "  %d/%d" % (k["apps"], n_apps))


def print_check(result):
    label = "App Store (iOS)" if result["platform"] == "ios" else "Google Play"
    print("Character-limit check: %s (counted in Unicode code points)" % label)
    for f in result["fields"]:
        status = "OK  " if f["ok"] else "OVER"
        print("  [%s] %-18s %3d / %-3d  remaining %d" % (
            status, FIELD_LABELS[f["field"]], f["length"], f["limit"], f["remaining"]))
        if f["text"]:
            print("         " + f["text"])
    for w in result["warnings"]:
        print("  warning: " + w)
    print("Result: " + ("all fields within limits" if result["ok"] else "one or more fields over the limit"))


def write_json(path, payload):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    sys.stdout.flush()
    print("\nSaved JSON to " + path, file=sys.stderr)


def emit_research(args, source, query, apps, extra=None):
    docs = []
    for a in apps:
        docs.append(a["name"] if args.titles_only else a["name"] + "\n" + a["description"])
    keywords = extract_keywords(docs, top=args.top) if args.top > 0 else []

    public_apps = [{k: v for k, v in a.items() if k != "description"} for a in apps]
    payload = {"source": source, "query": query, "count": len(apps),
               "apps": public_apps, "keywords": keywords}
    if extra:
        payload.update(extra)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if extra and extra.get("target"):
            t = extra["target"]
            print("Target: %s  (%s, %s)" % (t["name"], t["developer"], t["genre"]))
            print()
        print_table(apps)
        print_keywords(keywords, len(apps))
    if args.out:
        write_json(args.out, payload)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_ios(args):
    try:
        if args.app_id:
            target, raws = ios_similar(args.app_id, limit=args.limit)
            apps = [normalize_ios(r, i + 1) for i, r in enumerate(raws)]
            t = normalize_ios(target, 0)
            t.pop("description", None)
            emit_research(args, "itunes", {"app_id": args.app_id}, apps, {"target": t})
        else:
            raws = itunes_search(args.term, limit=args.limit)
            apps = [normalize_ios(r, i + 1) for i, r in enumerate(raws)]
            emit_research(args, "itunes", {"term": args.term}, apps)
    except FetchError as exc:
        print("error: " + str(exc), file=sys.stderr)
        return 3
    if not apps:
        print("No results.", file=sys.stderr)
    return 0


def cmd_play(args):
    try:
        raws = play_search(args.term, limit=args.limit)
    except Exception as exc:  # the scraper raises its own exception types
        print("error: Google Play search failed: %s" % exc, file=sys.stderr)
        return 3
    if raws is None:
        print("google-play-scraper is not installed. Install it with:\n"
              "  pip install google-play-scraper", file=sys.stderr)
        return 2
    apps = [normalize_play(r, i + 1) for i, r in enumerate(raws[: args.limit])]
    emit_research(args, "google_play", {"term": args.term}, apps)
    return 0


def cmd_check(args):
    if args.platform == "ios":
        result = check_ios(args.title or "", args.subtitle or "", args.keywords or "")
    else:
        result = check_play(args.title or "", args.short or "")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_check(result)
    if args.out:
        write_json(args.out, result)
    return 0 if result["ok"] else 1


def build_parser():
    p = argparse.ArgumentParser(
        prog="jp_competitors.py",
        description="Japanese App Store / Google Play competitor research and metadata limit checks.")
    sub = p.add_subparsers(dest="command", required=True)

    def research_opts(sp):
        sp.add_argument("--limit", type=int, default=20, help="number of apps (default 20)")
        sp.add_argument("--top", type=int, default=30, help="number of keywords to show, 0 to skip (default 30)")
        sp.add_argument("--titles-only", action="store_true", help="extract keywords from titles only")
        sp.add_argument("--json", action="store_true", help="print JSON instead of a table")
        sp.add_argument("--out", help="also write JSON to this file")

    ios = sub.add_parser("ios", help="search the Japan App Store (iTunes Search API)")
    g = ios.add_mutually_exclusive_group(required=True)
    g.add_argument("--term", help="search term, e.g. 家計簿")
    g.add_argument("--app-id", help="App Store numeric id: look it up and find similar apps")
    research_opts(ios)
    ios.set_defaults(func=cmd_ios)

    play = sub.add_parser("play", help="search Google Play Japan (needs google-play-scraper)")
    play.add_argument("--term", required=True, help="search term, e.g. 家計簿")
    research_opts(play)
    play.set_defaults(func=cmd_play)

    chk = sub.add_parser("check", help="check metadata against store character limits")
    chk.add_argument("--platform", choices=["ios", "play"], required=True)
    chk.add_argument("--title", default="")
    chk.add_argument("--subtitle", default="", help="iOS only")
    chk.add_argument("--keywords", default="", help="iOS only, comma-separated")
    chk.add_argument("--short", default="", help="Google Play short description")
    chk.add_argument("--json", action="store_true", help="print JSON")
    chk.add_argument("--out", help="also write JSON to this file")
    chk.set_defaults(func=cmd_check)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "check":
        if args.platform == "ios" and args.short:
            parser.error("--short is for --platform play")
        if args.platform == "play" and (args.subtitle or args.keywords):
            parser.error("--subtitle/--keywords are for --platform ios")
    elif args.limit < 1:
        parser.error("--limit must be at least 1")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
