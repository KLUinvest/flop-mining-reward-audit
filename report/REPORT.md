# FLOP Testnet Mining — Verified Compute & Reward Accounting

**Status:** Draft technical audit. No publication has occurred. Awaiting human review and
explicit go-ahead before any Technocore message, GitHub push, or other external action.

**Scope:** What the official FLOP Network Yellow Paper (v0.5.0, draft) specifies about (1) how
mined/served compute is verified ("Proof of Useful Inference") and (2) how rewards are computed
and accounted — with a focus on the two commits published on 2026-10-13, which this report treats
as the most recent authoritative text at analysis time.

**Author tooling note:** This report, the verification matrix, and the reproducible tests were
produced read-only against public sources. No private key, DID, passphrase, or Technocore network
write was used at any point.

---

## 1. Sources used (exact commits)

All claims below are traceable to a specific file + line in a specific commit of the **official**
`flop-labs/yellowpaper` GitHub repository, cloned locally into `official-yellowpaper/` (not
modified, not forked, not pushed anywhere).

| Artifact | Commit | Date | Note |
|---|---|---|---|
| `yellowpaper.md`, `CHANGELOG.md`, `params/flop-protocol-params.yaml`, `evidence/*` | **`70e691c758e53eed17a016a02b0a2ae1200d3744`** | 2026-10-13 14:38:47 +0800 | Latest sync at analysis time; "sync 0.5.0 (draft) from flop-core@5e6e24279" |
| Same files, immediately prior revision | `b03378c0a6d5194d69e5be90968f46e8e6813cb8` | 2026-10-13 13:16:50 +0800 | "sync 0.5.0 (draft) from flop-core@a1f3759e"; the larger of the two 2026-10-13 commits (23 files, +4567/-604) |
| Prior sync (baseline, for diff context) | `3c97bbc` | 2026-09-25 | Last sync before the two 2026-10-13 commits |

Clone command used (read-only, public repo, no credentials):
```bash
git clone https://github.com/flop-labs/yellowpaper.git official-yellowpaper
```
Verify locally: `git -C official-yellowpaper log --oneline -3` should show `70e691c` as `HEAD`.

Secondary sources (cross-checked, not used for normative claims):
- `https://flop.finance/intro/yellowpaper/` — the rendered mirror of the same text. Fetched via
  direct HTTPS GET (`curl`) on 2026-10-15; its "Updated 2026-09-24" banner is **stale relative to
  the GitHub source** — this report treats the GitHub repository as authoritative over the
  website mirror, since the website's `Updated` date predates the two commits analyzed here.
- `https://flop.finance/` and `https://flop.finance/llms.txt` — project overview pages, consulted
  only for context (not cited for normative claims).

## 2. What changed on 2026-10-13 (both commits, in order)

### Commit `b03378c` (13:16 +0800) — the larger sync
Per its own `CHANGELOG.md` entry (`## [Unreleased]`), this commit:
- **Ratified D-0517**, replacing §8.2's Miner/Validator airdrop unlock rule: a Miner grant now
  unlocks a quarter of principal at its start block and the rest only against *earn-to-unlock
  credit* tied to settled compute-channel payouts; the prior linear performance-scaled curve
  (SPEC-022) is superseded for Miner/Validator grants.
- **Ratified D-0522**, specifying the Agent airdrop unlock as *spend-to-unlock*:
  `⌊K/3⌋` where `K` is the agent's locked-principal share of settled `payable`s, with locked
  compute spend capped at `⌊3P/4⌋`.
- **Ratified D-0518**: block rewards and the Labs/Foundation subsidy are explicitly *liquid on
  issue* — never auto-compounded or force-staked.
- **Made current-profile channel settlements payment-only** (R11.2b, referencing internal task
  1494): receipt claims no longer feed public work rewards or performance vesting.
- Added **D-0519** (paid-storage service-lane close/claim rules) and **D-0512** (a devnet-only
  exception to the paid-storage activation gate) — both tangential to mining reward accounting
  but part of the same economic surface.
- Added substantial new evidence artifacts: `evidence/money-path-v1.{json,md,schema.json}` (a
  golden-vector corpus for compute-channel amount transitions) and
  `evidence/check-money-path-vectors.py`.

### Commit `70e691c` (14:38 +0800) — the smaller follow-up, same day
Per its `CHANGELOG.md` entry, this commit:
- **Named RTMR3 as the ONLY accepted measurement path** for the model root (§3.3 step 2,
  `D-0404`) — a narrowing from "RTMR3 (or measure it via kernel cmdline into MRTD)" to "RTMR3 as a
  TDX event-log entry... No other register or measurement path is accepted." This is the single
  most concrete *verification-mechanics* tightening in either commit.
- **Updated Appendix E/H implementation-status text to match landed code**, explicitly
  **without changing any protocol rule** (its own wording: "no protocol rule changes"):
  - marked multi-round bisection and `G_n` overflow rejection **LIVE**,
  - recorded the devnet paid-storage pallet's Quint/CI models as **PARTIAL**,
  - noted the runtime-benchmark build "now compiles in every runtime flavour" for E.46, though
    "no benchmark run, dedicated `flop-poui` weights or runtime hash is claimed" — i.e. a build
    fix, not new verification evidence,
  - clarified E.41 (validator active-set cap): "every promotion path enforces it" now, narrowing
    the previously-described gap to only the `MaxAuthorities`=200 ceiling and a storage-bound
    alignment task.
- **Specified Appendix D's chain-inclusion-fee terms** explicitly (base fee + encoded-length fee +
  adjusted-weight fee breakdown) — an editorial/clarifying addition, confirmed by the earlier
  table's existing 80/10/10 target language being retained unchanged.

**Overall characterization of the 2026-10-13 changes:** the larger commit (`b03378c`) contains
genuine new *ratified decisions* that change documented reward-unlock rules (D-0517, D-0522,
D-0518, R11.2b). The smaller commit (`70e691c`) is predominantly a status/documentation sync
against landed code, with one substantive verification-mechanics change (RTMR3-only measurement
path) and no claimed new reward-accounting rule. Both commits are regenerated automatically by
`scripts/publish_yellowpaper.py` from the private `flop-core` repository — the publish commit
message states "No normative text is altered" for the publish-time transform itself, meaning the
*content* changes originate upstream in `flop-core` commits `a1f3759e` and `5e6e24279`, which this
report could not independently inspect (that repository was not available for direct review; only
its generated mirror was).

## 3. Verified-compute mechanics (§3) — summary of documented rules

FLOP's "Proof of Useful Inference" is a **tiered hybrid**, not a single primitive:

**All "status" values in this table and throughout §3–§4 are copied verbatim from the
yellowpaper's own Appendix H self-assessment. This audit did not inspect any runtime code,
binary, or deployment and makes no independent claim about what is actually running anywhere.**
Where this report uses the word "documented," it means "the yellowpaper's own text asserts
this" — never "this audit observed this."

| Tier | Mechanism | Mandatory per spec text? | Appendix H.2's own self-reported status (NOT independently verified by this audit) |
|---|---|---|---|
| 1 | TEE attestation + measured `model_hash` (RTMR3-only as of 2026-10-13) | Optional (raises assurance to HARD tier) | Appendix H.2 states "LIVE (on-TDX e2e pending)"; same appendix separately states the CVM RTMR3 extension step is "PLANNED" |
| 2 | TOPLOC activation commitment (top-128 hidden-state values, prefill only) | **Required for every session**, per R3.1 | Appendix H.2 states "PARTIAL": commitment required; decode-step coverage and end-to-end error bound left open in E.43 |
| 3 | Independent optimistic re-execution by 3 bonded "checker" identities, unanimous verdict required | **Required**, per R3.3/R3.5d | Appendix H.2 states "PLANNED": the shipped checker re-prefill lives inside the validator watchtower only; the specified 3-checker VRF-assigned lane is not wired per the text, open item E.53 |
| 4 | On-chain validator BFT quorum (≥⌈2/3 × active⌉) crediting | **Required**, per R3.4/R3.6 | Appendix H.2 states "LIVE" |

Normative text carried forward unchanged by the 2026-10-13 commits (these are requirements the
specification states, not implementation observations):
- The specification explicitly disclaims proving *answer quality* — TOPLOC and re-execution are
  specified to detect model/precision/prompt substitution, not output correctness (R3.4c,
  normative text).
- `G_n` (billed reference-work) is specified as a **deterministic accounting convention**
  (`G_n = floor(F_eff / 1e9)`), to be computed by a shared `no_std` primitive — the spec text
  explicitly states this is **not** a physical FLOP/instruction count, energy measurement, or
  latency measurement (R4.1–R4.4). This formula's arithmetic properties (flooring behavior) were
  independently re-derived and checked in this audit's own test script (§6) — that is a check of
  the *formula*, not of whatever code actually runs on any FLOP node.
- A reject-only throughput tripwire is specified (never clamps or rewrites a claim); Appendix H.3
  self-reports this as "LIVE." This audit did not run or observe the tripwire itself.

## 4. Reward-accounting mechanics (§8–§9, §11–§12) — summary of documented rules

### Emission (protocol-level, independent of any individual miner's behavior)

The emission schedule, split ratios, and genesis-supply bucketing below are specification
constants taken from `params/flop-protocol-params.yaml` and the normative prose; their arithmetic
consistency was independently re-derived in this audit's tests (§6). Their deployment status
(whether a running FLOP node actually applies them) is separately addressed via Appendix H
self-reports further down this section — the two are kept distinct throughout.

- Per-block reward starts at 96 FLOP, halves every 63,072,000 blocks (~2 years) for 5 eras, then
  floors at 3 FLOP/block forever. **This schedule was independently recomputed from the committed
  parameter file in `tests/` (§6) and matches the prose exactly.**
- Split 750‑ppt miner / 100‑ppt validator / 100‑ppt agent / 50‑ppt staker (sums to 1000 ppt,
  independently re-verified in §6). Agent and staker legs currently accrue in sovereign pool
  accounts with **no ratified distribution policy** (open item E.40, per the spec text itself) —
  i.e. specified but not yet specified as distributable even on paper.
- A separate Labs/Foundation subsidy (8+8 FLOP/block at era 0) halves on the same schedule and
  terminates at era 5 (not merely floors, like the block reward). Total minted amount
  (1,955,232,000 FLOP) independently re-derived in §6.
- All of the above (miner leg, validator leg, subsidy) is specified as **liquid on issue** — no
  forced staking or vesting of the reward itself (R9.1, R9.13, re-ratified by D-0518 on
  2026-10-13). **Appendix H.4 self-reports this as "LIVE"** (reward liquidity row); this audit did
  not independently observe any running node to confirm that self-report.

### Mining-specific reward unlock (airdrop/vesting layer, §8.2 — materially changed 2026-10-13)

The three bullets below are **specification requirements** — what the yellowpaper's normative
text (R8.7, R8.8) states a Miner/Agent/Validator grant's unlock rule *must* be. They describe the
rule as written, not any observed running behavior.

- A **Miner** grant unlocks ¼ of principal immediately, the rest only against *earn-to-unlock
  credit*: one FLOP of principal released per FLOP the account receives as a channel's miner in a
  **finalized, dispute-window-cleared** settled session. Block rewards earn **no** credit toward
  this unlock. This is the ratified D-0517 rule (2026-10-13), replacing an earlier linear
  performance-scaled curve.
- An **Agent** grant unlocks `⌊K/3⌋` against settled compute-channel spend, capped so locked spend
  never exceeds `⌊3P/4⌋` of principal (D-0522, 2026-10-13).
- A **Validator** grant stays fully frozen until the first halving (block 63,072,000), then
  releases one grant per day — but the release order itself remains unresolved (open item E.38),
  so the yellowpaper's own text states Validator grants **MUST NOT** be released until that is
  fixed.

**Appendix H.4's own self-report (unchanged conclusion across both 2026-10-13 commits) states**
this entire unlock mechanism is **"PARTIAL"**: per that text, the deployed pallet still vests
every tier linearly with a *retired* performance adjustment, has no genesis quarter or
earn-to-unlock credit wired, and lets any tier spend locked principal without the new spend caps.
**This audit did not inspect any runtime, binary, or deployed pallet to confirm Appendix H's own
characterization** — the finding below is entirely sourced from the yellowpaper's own text, not
from independent observation:

> According to the yellowpaper's own Appendix H.4, the 2026-10-13 commits changed the
> *specification* text (new unlock formulas, newly ratified decisions D-0517/D-0522), while the
> same appendix states the *deployed* pallet behavior has not yet caught up. Readers should treat
> this as the document's own self-assessment of a spec/implementation gap, not as this audit's
> independent finding about any running system.

### Channel settlement and current public-credit status
- `R11.2b` (unchanged core rule, clarified wording 2026-10-13) specifies that current-profile
  compute-channel settlements are **payment-only** — the rule as written states they do not feed
  public work-vesting credit or block reward eligibility. **Appendix H.5 self-reports this as
  "LIVE payment-only"**; future audited credit is an open item in the spec text itself (E.44).
  This audit did not independently verify the Appendix H.5 self-report against any running code.
- `R12.1d` (failed/early-close): a specified three-way conservation split
  `P + (1-φ)(E-P) + φ(E-P) = E`, φ = 20%. This identity's algebraic correctness was independently
  re-derived and checked for several (E, P) pairs in this audit's tests (§6) — that confirms the
  *formula is internally consistent as written*, not that any running settlement code implements
  it correctly.

## 5. Documented vs. implemented vs. provisional vs. not available

See `matrix/verification_matrix.csv` for the full machine-readable matrix (27 rows). Summary
counts by this audit's classification:

| Classification | Meaning used here | Count in matrix |
|---|---|---|
| DOCUMENTED + LIVE | Specified in the yellowpaper, AND Appendix H's own text states it is implemented | 9 |
| DOCUMENTED + PARTIAL | Specified, with Appendix H's own text describing a gap between spec and deployed code | 11 |
| DOCUMENTED + PLANNED | Specified as a requirement, but Appendix H's own text says it is designed/not wired | 2 |
| DOCUMENTED + GAP/PENDING | Specified as an open problem the yellowpaper itself has not resolved | 4 |
| Editorial-only (not a new rule) | A 2026-10-13 text clarification the authors themselves flag as non-normative | 1 |

**Every value in the matrix's `implemented_status` column is a direct quotation or close
paraphrase of FLOP Labs's own Appendix H self-assessment** — it is not an independent runtime
audit by this report. This audit had no access to the private `flop-core` runtime source and
performed no independent verification of any `LIVE`/`PARTIAL`/`PLANNED`/`GAP` label against
actually running code. Every row's citation (`source_citation` column) points to the exact
Appendix H line making that claim, so a reader can trace each label back to its origin and judge
its reliability themselves. This limitation is repeated in §7 below.

### 5.1 Matrix line-reference consistency review

As part of this revision, every `source_citation` line number in all 27 matrix rows was
re-verified against the actual committed `official-yellowpaper/yellowpaper.md` text (`git log -1`
confirms `HEAD` is still `70e691c758e53eed17a016a02b0a2ae1200d3744`, matching the matrix's
`commit` column throughout). Method: for each cited line number, `sed -n '<N>p' yellowpaper.md`
was run and its content compared against the row's claimed mechanism/requirement text.

**Result: all 27 rows' line citations were confirmed accurate** on this pass — each cited line
number contains the text the row claims it contains (requirement text, Appendix H status-table
row, or diff context, as applicable). No row was found pointing at the wrong line or an
unrelated passage.

### 5.2 Test-script false-positive review

The reproducible test script (`tests/test_reward_accounting.py`) was re-read in full for
potential false positives — logic that would report PASS even when the underlying claim is
wrong. One issue was found and fixed in this revision:

- **`test_bft_quorum_threshold`** computed the quorum ceiling via
  `math.ceil(active_count * float(threshold))`. Converting the exact rational threshold
  (`666666666 / 1e9`) to a binary `float` before multiplying introduces a (tiny) risk that, at
  some `active_count`, the float product lands just below an integer boundary where the exact
  value is just above it (or vice versa), silently producing an off-by-one `quorum` that the five
  original spot-check cases (`active_count` ∈ {1, 3, 4, 100, 200}) would not necessarily catch.
  **Fix:** replaced the float-based ceiling with exact integer ceiling division
  (`-(-numerator // denominator)` on the exact integer product), and added a new check that
  sweeps every `active_count` from 1 to 3,000 (3× `validator_active_set_cap`) comparing the
  exact-integer result against an independently-computed `Decimal`-with-`ROUND_CEILING` ceiling.
  This sweep found **zero mismatches**, so the original spot-checks happened not to have hidden a
  real bug in this case — but the float path was still a latent correctness risk worth removing
  rather than merely confirming absent-by-luck.

No other false-positive risk was identified: every other test either (a) compares an exact
`Decimal` computation against an exact `Decimal` expected value with no intermediate float
conversion, or (b) captures the verbatim exit code and stdout of an external script without
reinterpreting its result.

## 6. Reproducible tests performed

All tests are in `tests/test_reward_accounting.py` (standard library + `pyyaml` only, no network
access, no identity). Two kinds of checks:

1. **Independent re-derivation** of yellowpaper-published formulas/constants from
   `params/flop-protocol-params.yaml`, checked against the values stated in the prose (emission
   halving schedule, four-way reward split, genesis-supply bucket sum, subsidy total, Miner/Agent
   grant unlock formulas, `R_p²` convexity, `G_n` floor semantics, `force_settle` conservation
   identity, BFT quorum rounding — including an exact-integer sweep of the quorum ceiling over
   every active-validator count from 1 to 3,000, i.e. 3× the documented
   `validator_active_set_cap` of 1,000, specifically to catch any floating-point rounding
   discrepancy that a handful of spot-check cases could miss).
2. **Invocation of the yellowpaper repository's own published reproduction scripts**
   (`evidence/reproduce.py --check`, `evidence/reproduce-audit.py --check`), run unmodified, with
   their verbatim output captured — this audit did not write or alter their logic, only called
   them and recorded the result.

**Actual run, 2026-10-15, this environment (full output in `tests/results.json`):**

```
TOTAL: 18  PASS: 18  FAIL: 0
```

All 18 checks passed. No test result in this report or in `tests/results.json` was fabricated,
pre-written, or adjusted after the fact — the script was executed once after this revision's
changes, its stdout captured, and `results.json` is its direct `json.dump` output. A prior version
of this script ran 17 checks using a float-based ceiling for the BFT quorum test; this revision
replaced that with an exact-integer ceiling and added an explicit sweep test (18th check) to rule
out any floating-point false positive at scale — see §5.2 above for the full description of the
fix. Re-run with:
```bash
cd /root/flop/flop-mining-reward-audit
python3 tests/test_reward_accounting.py
```

**What these tests do NOT establish:**
- They do not test the actual FLOP runtime (no access to `flop-core`'s private source).
- They do not measure real compute, real GPU throughput, or real network behavior.
- `evidence/reproduce-audit.py`'s "5 scenarios, 25 exposure rows" check reproduces the
  yellowpaper's *own* non-deterrence arithmetic for its Tier-3 re-execution economic model — it
  confirms the published numbers are internally consistent, not that the deterrence condition
  holds in practice (the yellowpaper itself states these scenarios are illustrative, not an
  equilibrium proof).

## 7. Uncertainties and limitations (explicit)

- **Upstream source not directly inspected.** Both 2026-10-13 commits are auto-generated mirrors
  of private `flop-core` commits (`a1f3759e`, `5e6e24279`). This audit read only the published
  mirror; it could not check the private repository's commit history, PR discussion, or CI results
  directly.
- **Self-reported implementation status.** Every `LIVE`/`PARTIAL`/`PLANNED`/`GAP` label in
  Appendix H is FLOP Labs's own documentation, not an external code audit. This report
  reproduces and cites that status; it does not independently verify it against running code,
  because no runtime access was available or sought (out of scope, per task instructions).
- **The yellowpaper itself flags unresolved items as "open."** Several of the mechanisms most
  relevant to a would-be miner's actual payout timeline (Validator grant release order, E.38;
  TOPLOC decode-step coverage, E.43; checker-lane wiring, E.53; DA availability model, E.47) are
  explicitly marked open by the source document, not by this audit.
- **No calibration or empirical performance data exists or is claimed.** This audit did not run,
  simulate, or invent any GPU benchmark, throughput measurement, or empirical detection-rate
  result. Every number in §6 is either a protocol *parameter* (from the committed YAML) or a
  *formula* re-derivation; none is an empirical calibration result.
- **Version is draft.** The yellowpaper is explicitly v0.5.0 (draft) — "No version has been
  published yet" per its own `CHANGELOG.md` preamble. Nothing in this report should be read as
  describing a finalized, audited, or mainnet-ready specification.
- **Scope boundary.** This audit focuses on mining-reward accounting and compute verification. It
  does not cover HTLC/cross-chain mechanics, governance, or the paid-storage subsystem in depth,
  even though the 2026-10-13 commits touch all three; those are summarized only where they
  intersect reward accounting (e.g., D-0519, D-0512).

## 8. Files in this contribution

```
flop-mining-reward-audit/
├── README.md                          <- orientation for future readers (start here)
├── report/
│   └── REPORT.md                      <- this file
├── matrix/
│   └── verification_matrix.csv        <- 27-row documented/implemented/provisional/not-available matrix
├── tests/
│   ├── test_reward_accounting.py      <- reproducible, dependency-light verification script
│   └── results.json                   <- actual captured output of the most recent real run (18/18 pass)
├── sources/
│   ├── SOURCES.txt                    <- one-line pointer to the official repo + pinned commit
│   └── official-yellowpaper-HEAD.txt  <- the exact commit hash this audit cites throughout
└── official-yellowpaper/              <- unmodified git clone of github.com/flop-labs/yellowpaper
                                           (HEAD = 70e691c758e53eed17a016a02b0a2ae1200d3744;
                                           gitignored — not tracked by this repo's own git history)
```

Note: `official-yellowpaper/` is a full git clone kept locally for citation traceability and to
run its own `evidence/` scripts. It is **not** modified, **not** re-pushed, and **not** a fork
published anywhere. It is deliberately excluded from this repository's own git history via
`.gitignore` (see `sources/SOURCES.txt` and `sources/official-yellowpaper-HEAD.txt` for the pinned
commit reference that stands in for it in the committed tree). If a reviewer wants it included
verbatim in an eventual publication, that is a separate decision to be made before any
publication step.

## 9. Explicit statement of compliance with constraints

- **No GitHub publication occurred.** This repository has one or more **local** git commits
  (`git log` in this directory shows them) — it is not merely uncommitted work-in-progress, and
  this report does not claim otherwise. What has *not* happened is any `git push`, any remote
  configuration (`git remote -v` returns nothing), or any publication to GitHub or any other
  external host.
- No Technocore message was sent. No `say`/`proof` command from any Technocore client was
  invoked.
- No private key or DID was used, read, or referenced. `identity.pem` was not accessed.
- No test result, calibration figure, or benchmark number was invented. Every number in §6 is
  either a cited yellowpaper constant/formula or the literal stdout of a script run in this
  session, captured in `tests/results.json`.
- This contribution was not produced merely to generate activity: it exists specifically to
  answer the two questions asked (reward-calculation rules; compute-verification rules) with
  explicit DOCUMENTED/IMPLEMENTED/PROVISIONAL/NOT-AVAILABLE labeling and cited sources.

**This report is held for human review. No publication, announcement, or commit push will occur
without explicit further authorization.**
