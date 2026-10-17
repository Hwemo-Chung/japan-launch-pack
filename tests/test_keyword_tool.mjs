import { createRequire } from "module";
import assert from "assert/strict";
const require = createRequire(import.meta.url);
const K = require("../assets/keyword-tool.js");
let n = 0; const t = (name, fn) => { fn(); n++; };

t("split on mixed separators", () => {
  assert.deepEqual(K.splitKeywords("家計簿, 節約、貯金，レシート\n支出　収入 budget"), ["家計簿","節約","貯金","レシート","支出","収入","budget"]);
});
t("dedupe case-insensitive for latin", () => {
  const r = K.processKeywords("Budget,budget,BUDGET,家計簿,家計簿");
  assert.deepEqual(r.keywords, ["Budget","家計簿"]); assert.equal(r.duplicates.length, 3);
});
t("NFKC folds full-width latin", () => {
  assert.deepEqual(K.processKeywords("ＡＢＣ,abc").keywords, ["ABC"]);
});
t("remove words already in title/subtitle", () => {
  const r = K.processKeywords("家計簿,節約,レシート", { removeTitleWords: true, title: "かんたん家計簿", subtitle: "レシート読み取り" });
  assert.deepEqual(r.keywords, ["節約"]); assert.deepEqual(r.removedFromTitle, ["家計簿","レシート"]);
});
t("join has no spaces", () => { assert.equal(K.joinKeywords(["a","b","家計"]), "a,b,家計"); });
t("code point length", () => { assert.equal(K.len("家計簿"), 3); assert.equal(K.len("😀a"), 2); });
t("fit drops from the end", () => {
  const list = Array.from({ length: 30 }, (_, i) => "語" + i);
  const f = K.fitToLimit(list, 100);
  assert.ok(K.len(K.joinKeywords(f.keywords)) <= 100);
  assert.equal(f.keywords.length + f.dropped.length, 30);
  assert.equal(f.dropped[f.dropped.length - 1], "語29");
});
t("check limits", () => {
  assert.deepEqual(K.check("あ".repeat(31), 30), { count: 31, limit: 30, remaining: -1, over: true });
  assert.equal(K.check("", 80).over, false);
});
console.log(`ok ${n} tests`);
