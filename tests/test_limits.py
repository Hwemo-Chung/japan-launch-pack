"""Offline tests for the limit checker and keyword extractor (no network)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

import jp_competitors as jc  # noqa: E402


def field(result, name):
    return next(f for f in result["fields"] if f["field"] == name)


class CharLenTest(unittest.TestCase):
    def test_counts_code_points(self):
        self.assertEqual(jc.char_len("家計簿"), 3)
        self.assertEqual(jc.char_len("ポケット家計簿 - レシートで簡単支出管理"), 21)
        self.assertEqual(jc.char_len(""), 0)
        self.assertEqual(jc.char_len(None), 0)

    def test_astral_character_is_one(self):
        # U+20BB7 is outside the BMP; it is one code point.
        self.assertEqual(jc.char_len("\U00020BB7野家"), 3)


class IosCheckTest(unittest.TestCase):
    def test_within_limits(self):
        r = jc.check_ios("ポケット家計簿", "毎日のお金をグラフで見える化", "節約,貯金,予算")
        self.assertTrue(r["ok"])
        self.assertEqual(field(r, "title")["remaining"], 30 - 7)
        self.assertEqual(field(r, "subtitle")["length"], 14)
        self.assertEqual(field(r, "keywords")["length"], 8)
        self.assertEqual(r["warnings"], [])

    def test_exact_limit_is_ok(self):
        r = jc.check_ios("あ" * 30, "い" * 30, "う" * 100)
        self.assertTrue(r["ok"])
        self.assertTrue(all(f["remaining"] == 0 for f in r["fields"]))

    def test_over_limit(self):
        r = jc.check_ios("あ" * 31, "", "x" * 101)
        self.assertFalse(r["ok"])
        self.assertEqual(field(r, "title")["remaining"], -1)
        self.assertFalse(field(r, "keywords")["ok"])
        self.assertTrue(field(r, "subtitle")["ok"])

    def test_space_after_comma(self):
        r = jc.check_ios("", "", "節約, 貯金")
        self.assertTrue(any("space after comma" in w for w in r["warnings"]))

    def test_fullwidth_space_after_comma(self):
        r = jc.check_ios("", "", "節約,　貯金")
        self.assertTrue(any("space after comma" in w for w in r["warnings"]))

    def test_japanese_comma(self):
        r = jc.check_ios("", "", "節約、貯金")
        self.assertTrue(any("Japanese comma" in w for w in r["warnings"]))

    def test_duplicates(self):
        r = jc.check_ios("", "", "節約,貯金,節約,Budget,budget")
        dup = [w for w in r["warnings"] if "duplicate" in w]
        self.assertEqual(len(dup), 1)
        self.assertIn("節約", dup[0])
        self.assertIn("budget", dup[0].lower())

    def test_empty_entry(self):
        r = jc.check_ios("", "", "節約,,貯金,")
        self.assertTrue(any("empty entry" in w for w in r["warnings"]))

    def test_words_already_in_title_or_subtitle(self):
        r = jc.check_ios("ポケット家計簿", "グラフで見える化", "家計簿,グラフ,節約")
        w = [x for x in r["warnings"] if "already in title" in x]
        self.assertEqual(len(w), 1)
        self.assertIn("家計簿", w[0])
        self.assertIn("グラフ", w[0])
        self.assertNotIn("節約", w[0])

    def test_latin_word_match_uses_word_boundaries(self):
        r = jc.check_ios("Budget Book", "", "budget,get")
        w = [x for x in r["warnings"] if "already in title" in x]
        self.assertEqual(len(w), 1)
        # "get" is inside "Budget" but is not a word of the title.
        self.assertTrue(w[0].endswith(": budget"), w[0])


class PlayCheckTest(unittest.TestCase):
    def test_within_limits(self):
        r = jc.check_play("ポケット家計簿", "レシートを撮るだけで支出を記録")
        self.assertTrue(r["ok"])
        self.assertEqual(field(r, "short")["limit"], 80)
        self.assertEqual(field(r, "short")["remaining"], 80 - 15)

    def test_over_limit(self):
        r = jc.check_play("あ" * 31, "い" * 81)
        self.assertFalse(r["ok"])
        self.assertEqual(field(r, "title")["remaining"], -1)
        self.assertEqual(field(r, "short")["remaining"], -1)

    def test_whitespace_warning(self):
        r = jc.check_play(" 家計簿", "")
        self.assertTrue(any("whitespace" in w for w in r["warnings"]))


class TokenizeTest(unittest.TestCase):
    def test_katakana_kanji_latin(self):
        toks = jc.tokenize_ja("シンプル家計簿 - Money Tracker")
        self.assertIn("シンプル", toks)
        self.assertIn("家計簿", toks)
        self.assertIn("money", toks)
        self.assertIn("tracker", toks)

    def test_kanji_with_hiragana_ending(self):
        toks = jc.tokenize_ja("楽しい節約")
        self.assertIn("楽しい", toks)
        self.assertIn("節約", toks)

    def test_particles_not_attached(self):
        toks = jc.tokenize_ja("家計簿の管理が簡単にできる")
        self.assertIn("家計簿", toks)
        self.assertIn("管理", toks)
        self.assertIn("簡単", toks)
        self.assertNotIn("家計簿の", toks)
        self.assertNotIn("簡単に", toks)

    def test_long_kanji_run_yields_ngrams(self):
        toks = jc.tokenize_ja("家計簿管理")
        self.assertIn("家計簿管理", toks)
        self.assertIn("家計簿", toks)
        self.assertIn("管理", toks)

    def test_trailing_long_vowel_kept(self):
        self.assertIn("カレンダー", jc.tokenize_ja("カレンダー表示"))

    def test_trailing_particle_not_attached(self):
        self.assertNotIn("多くの", jc.tokenize_ja("多くの人"))

    def test_halfwidth_katakana_normalised(self):
        self.assertIn("カード", jc.tokenize_ja("ｶｰﾄﾞ"))

    def test_stopwords_removed(self):
        toks = jc.tokenize_ja("便利なアプリ for your iPhone")
        self.assertNotIn("アプリ", toks)
        self.assertNotIn("for", toks)
        self.assertNotIn("your", toks)
        self.assertNotIn("iphone", toks)

    def test_single_characters_ignored(self):
        self.assertEqual(jc.tokenize_ja("a 本 ア"), [])


class ExtractKeywordsTest(unittest.TestCase):
    DOCS = [
        "家計簿 - レシートで簡単支出管理",
        "シンプル家計簿 お小遣い帳",
        "家計簿アプリ Zaim風 節約",
        "貯金 節約 マネー管理",
    ]

    def test_ranking_and_counts(self):
        kws = jc.extract_keywords(self.DOCS, top=10)
        by_kw = {k["keyword"]: k for k in kws}
        self.assertEqual(kws[0]["keyword"], "家計簿")
        self.assertEqual(by_kw["家計簿"]["apps"], 3)
        self.assertEqual(by_kw["節約"]["apps"], 2)

    def test_counts_total_and_apps_separately(self):
        kws = jc.extract_keywords(["節約 節約 節約", "節約"], top=5)
        self.assertEqual(kws[0], {"keyword": "節約", "count": 4, "apps": 2})

    def test_shadowed_substrings_dropped(self):
        kws = [k["keyword"] for k in jc.extract_keywords(["家計簿管理", "家計簿管理"], top=20)]
        self.assertIn("家計簿管理", kws)
        # 計簿 only ever appears inside 家計簿 with the same stats.
        self.assertNotIn("計簿", kws)

    def test_top_limit(self):
        self.assertLessEqual(len(jc.extract_keywords(self.DOCS, top=3)), 3)

    def test_empty(self):
        self.assertEqual(jc.extract_keywords([], top=10), [])


class CliTest(unittest.TestCase):
    def test_check_exit_codes(self):
        import contextlib
        import io

        with contextlib.redirect_stdout(io.StringIO()):
            ok = jc.main(["check", "--platform", "play", "--title", "家計簿", "--short", "簡単"])
            bad = jc.main(["check", "--platform", "ios", "--title", "あ" * 31])
        self.assertEqual(ok, 0)
        self.assertEqual(bad, 1)


if __name__ == "__main__":
    unittest.main()
