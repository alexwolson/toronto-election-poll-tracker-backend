# Anchor house effects on non-online pollsters: do-no-harm test (2026-10-13)

**Status: approved by the maintainer, 2026-10-13. Binding. Committed before any fit.**

## Decision and its reasons (maintainer, 2026-10-13)

The maintainer decided the house-effect frame should be set without online-only polls:
1. As it stands, the online polls have an outsized effect, swinging how biased the other polls look.
2. The limited evidence is that online polling is worse, so so large an effect is not justified.
3. There is the least data on online polling, yet it has the largest effect.

**Disclosure.** The decision follows 2026-10-13 diagnostics: `repeat-firm-anchor-2026-10-13.md` and the
read-only checks in that session. Those showed:
- Ipsos (+7.6) and Canada Pulse (+3.8), the two online-only 2026 polls, set the house-effect zero point.
- Without them, the current Chow–Bradford margin moves from about +9.2 to about +6.3.
- In the historical corpus, the three online polls in the final four weeks sat furthest from their race's
  other polls.

The motivation includes a 2026 result, so this test only guards against harm. It is not evidence for the
change.

## Variant O

`build_model(..., house_anchor="non_online")`, applied in every campaign (maintainer's choice).

- **Online-only firm:** every poll from the firm in that campaign's fitted data has a collection mode in
  `ONLINE_ONLY_MODES` = {online, online_panel, online-sms-invitation}. Mixed online-and-telephone designs
  and unreported modes are not online-only (maintainer's choice).
- **When both kinds of firm are present:** every firm's effect is centred on the mean of the
  non-online-only firms. Online-only firms keep a free effect in that frame, and every poll stays in the fit.
- **Otherwise:** unchanged from production P.

Code: b47ba99..this commit on `feat/online-free-house-anchor`. Tests cover the mode flag on historical and
2026 polls, the centring, the both-kinds condition, and that the model compiles and samples.

**Where O changes a held-out fold** (computed from the data before any fit):
- At 14 days: 2006 (Decima), 2010 (Angus Reid), 2014 (Ipsos, whose polls by then were online only) and
  2023 (Viewpoints).
- At 7 days: 2006, 2010 and 2014. 2023 is unchanged because Viewpoints' unreported-mode poll by then
  counts as non-online.
- In training data with full results: 2006 and 2010.

## Fast do-no-harm test (maintainer's choice)

**Reused baseline.** The arm P fits of the repeat-firm anchor test (`queue-box/`, `queue-mac/`):
- production code, at the same pinned inputs: `results-2026-10-07.1`, `polling-2026-10-13.1`;
- the same settings (4 × (1,000 + 4,000)) and the same retry rule.

Before any O fit, one P fold is re-run on this commit and must match the stored fit in every recorded
field. That shows the code change leaves P unchanged.

**Arm O fits:**
- each changed fold at 3 seeds (20260921–20260923);
- each unchanged fold at seed 20260921 only, as a check that it barely moves;
- 28 fits in all, P and O for a (fold, seed) always on the same machine.

**Criteria (binding), at 14 days and at 7 days**, over the scored (fold, seed) set, which is identical for
P and O:
1. O's mean leader-margin CRPS is no worse than P's by more than 0.10 points;
2. a fold is covered when 2 of 3 seeds cover it (changed folds) or its single seed covers it (unchanged
   folds), and O covers at least as many folds as P;
3. after the retry, O has no more sampling failures than P.

**Outcome.** If all three pass at both horizons, O goes to the maintainer for adoption (ADR, release,
preview, go). If any fails, O is not adopted on this evidence, and the maintainer decides what follows.

**2026 (report only):** computed once, after scoring, on the current inputs (`polling-2026-10-13.2`).

**Records:**
- runs in `research-runs/online-free-anchor-2026-10-13/` (never in git);
- scorer `docs/research/compact_mayoral/score_online.py`, committed with this note;
- results appended below, without editing anything above.

---

## Run record (appended; nothing above this line is edited)

**Machine assignment (fixed before any O fit).** Each P fit is compared with an O fit from the same
machine.
- **Box (Linux):** the seed-20260921 P fits are on the box, so it runs O for 14 d (all seven folds) and for
  7 d 2003, 2006, 2010 and 2014: 11 fits.
- **Mac:**
  - it holds the seed 20260922/3 P fits, so it runs O for the changed folds at those seeds: 14 fits;
  - to balance the load, it also re-runs P and O for the three unchanged 7 d folds at seed 20260921 (2018,
    2022, 2023). Those three box P fits are set aside and not scored.
- **Identity check, run first on the Mac:** P at 14 d, 2006, seed 20260922 (stored by the Mac) must match
  in every recorded field.
- **Rebalance at 15:08 (maintainer: "load balance the remaining tasks"):** the Mac finished its share first.
  The box's queue loop was stopped while its 14 d 2022 fit was still running, and that fit completed on the
  box. The box's last unstarted item, 7 d 2003 at seed 20260921, ran on the Mac as a P+O pair. Its box P fit
  is set aside like the other three re-run on the Mac.
- **Scored P set:**
  - every stored P fit, except the box P fits for 7 d 2003, 2018, 2022 and 2023 at seed 20260921;
  - those four come from the Mac's re-runs.
