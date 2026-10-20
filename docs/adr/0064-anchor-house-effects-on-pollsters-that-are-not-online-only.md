# 0064. Anchor house effects on pollsters that are not online-only

Date: 2026-10-13. Status: accepted (adopted 2026-10-20; not adopted 2026-10-13).

This ADR amends ADR 0054's house-effect specification ("one firm effect per firm").
Each firm still has its own effect. What changes is which firms define zero: firms
whose polls are all online-only no longer set it.

## Context

ADR 0054 draws every firm's house effect around zero with a shared scale
(`tau_firm`). The unbiased frame is therefore the average of whichever firms poll a
campaign. Each firm counts equally, however much evidence it contributes.

The 2026-10-13 diagnostics (backend `docs/research/repeat-firm-anchor-2026-10-13.md`
and `docs/research/online-free-anchor-2026-10-13.md`) found:

- **Who sets the zero.** The only two online-only polls in the 2026 fit, Ipsos (Sept 4–8)
  and Canada Pulse (Sept 14–24), took the two most pro-Chow house effects (+7.6 and
  +3.8 points on the Chow–Bradford margin). Because effects centre on zero, they
  pulled every other firm's effect toward Bradford: Liaison −3.8, Mainstreet −4.3.
- **How large the pull is.** About 3 of the roughly 9 points in the model's current
  Chow–Bradford margin came from this. Keeping both polls in the fit but out of the
  anchor gave almost the same answer as dropping them entirely. Their influence ran
  through the anchor, not through their data.
- **The historical record.** In each of the three past Toronto races with an online
  poll in the final four weeks (2006, 2010, 2023), that poll sat furthest from the race's
  other polls (12.5–13.9 points on average, against about 4 for phone and IVR). The
  record is thin: three polls, three firms, three eras.

A general rule was tested first and failed: anchoring on firms with repeat polls was
not adopted (`repeat-firm-anchor-2026-10-13.md`).

## Decision

1. **Online-only firm.** A firm is online-only in a campaign when every poll it
   contributes to that campaign's fit has a `collection_mode` in `ONLINE_ONLY_MODES`
   (`online`, `online_panel`, `online-sms-invitation`). Mixed online-and-telephone
   designs, and polls whose mode is not reported, are not online-only.
2. **Anchor.** In a campaign that has both online-only firms and other firms, every
   firm's effect is centred on the mean effect of the other firms
   (`house_anchor="non_online"`, `PRODUCTION_HOUSE_ANCHOR`). Online-only firms keep
   a free effect in that frame. Every poll stays in the fit with its usual weight.
   A campaign without both kinds of firm is fitted exactly as before.
3. **Scope.** The rule applies to every campaign in every fit: the seven historical
   campaigns and 2026. House effects mean the same thing everywhere, and `tau_firm` is
   learned under one definition.
4. **Feed.** `model.specification.house_anchor` records `"non_online"`. Forecast
   schema 5 is otherwise unchanged.

## Why (maintainer, 2026-10-13)

- Under the old anchor, the two online polls had an outsized effect, swinging how
  biased every other pollster appeared.
- The limited historical evidence is that online polls are further from the field,
  so so large an effect on the frame is not justified.
- There is the least data on online polling, yet it had the largest effect.

## Evidence and guard rails

- **Do-no-harm test.** Pre-registered and committed before any fit
  (`online-free-anchor-2026-10-13.md`); it **passed** at 14 and 7 days:
  - mean leader-margin CRPS 7.99 → 7.06 and 6.59 → 5.88;
  - coverage equal (6/7, 7/7);
  - no extra sampling failures.
  Most of the gain is 2006, whose Decima online poll had been seen as the largest outlier
  before the test was written. That gain is not independent evidence for the rule. The
  binding claim is no harm.
- **Disclosure.** The decision followed diagnostics of the 2026 forecast, and it lowers
  Chow's published chance (67.5% → about 63% on the current inputs). It is a
  methodological judgement about online-only polling, recorded with its motivation. It
  is not a correction justified by any poll's distance from the others (ADR 0030).
  No poll is excluded (ADR 0062 is unchanged).
- **Not covered.** A future online-only firm with a long record is still kept out of the
  anchor. Revisiting this needs a new decision.

## Not adopted (maintainer, 2026-10-13)

The rule passed its do-no-harm test and `backend-2026-10-13.3` was built and previewed with it,
but it was not promoted. The forecast is public and widely followed, and the change would have
moved Chow's published chance from 67.5% to about 63% thirteen days before the election with
no new poll behind it. Readers would reasonably take that as a change in the race. The possible
gain in accuracy does not justify that risk this late.

- `PRODUCTION_HOUSE_ANCHOR` is `"prior"` again: the ADR 0054 frame, as published before this ADR.
- The `house_anchor="non_online"` option, its tests and the research notes stay, as the record
  for revisiting the rule after the election.
- `backend-2026-10-13.3` is an immutable release that is never promoted.

## Adopted (maintainer, 2026-10-20)

The maintainer reversed the October 13 decision and adopted the rule as written. It ships as
its own release, after the release that added the October 16-19 polls (Mainstreet, Build
Canada, Pollara), so the published change from new polls and the change from this rule are
seen separately.

- `PRODUCTION_HOUSE_ANCHOR` is `"non_online"` again; the production tests pin it.
- The rule is unchanged, so firms new since October 13 follow it by collection mode:
  Build Canada (`online-sms-invitation`) keeps its own effect but does not set zero;
  Pollara (`mixed`) helps set it. No firm is chosen by its results (ADR 0030).
- `backend-2026-10-13.3` stays unpromoted; the adopting release is a fresh build.
