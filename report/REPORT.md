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

| Tier | Mechanism | Mandatory? | Documented status (Appendix H.2) |
|---|---|---|---|
| 1 | TEE attestation + measured `model_hash` (RTMR3-only as of 2026-10-13) | Optional (raises assurance to HARD tier) | LIVE (on-TDX end-to-end pending; CVM RTMR3 extension itself PLANNED) |
| 2 | TOPLOC activation commitment (top-128 hidden-state values, prefill only) | **Required for every session** | PARTIAL (commitment required; decode-step coverage and end-to-end error bound open, E.43) |
| 3 | Independent optimistic re-execution by 3 bonded "checker" identities, unanimous verdict required | **Required** | PLANNED (shipped checker re-prefill lives inside the validator watchtower only; the specified 3-checker VRF-assigned lane is not wired, E.53) |
| 4 | On-chain validator BFT quorum (≥⌈2/3 × active⌉) crediting | **Required** | LIVE |

Key normative points carried forward unchanged by the 2026-10-13 commits:
- The protocol explicitly disclaims proving *answer quality* — TOPLOC and re-execution detect
  model/precision/prompt substitution, not output correctness (R3.4c, normative).
- `G_n` (billed reference-work) is a **deterministic accounting convention**
  (`G_n = floor(F_eff / 1e9)`), computed by a shared `no_std` primitive — explicitly **not** a
  physical FLOP/instruction count, energy measurement, or latency measurement (R4.1–R4.4).
- A reject-only throughput tripwire exists (never clamps or rewrites a claim) — documented LIVE.

## 4. Reward-accounting mechanics (§8–§9, §11–§12) — summary of documented rules

### Emission (protocol-level, independent of any individual miner's behavior)
- Per-block reward starts at 96 FLOP, halves every 63,072,000 blocks (~2 years) for 5 eras, then
  floors at 3 FLOP/block forever. **Verified by direct recomputation in `tests/` (§6 below).**
- Split 750‑ppt miner / 100‑ppt validator / 100‑ppt agent / 50‑ppt staker (sums to 1000 ppt).
  Agent and staker legs currently accrue in sovereign pool accounts with **no ratified
  distribution policy** (open item E.40) — i.e. documented but not yet distributable.
- A separate Labs/Foundation subsidy (8+8 FLOP/block at era 0) halves on the same schedule and
  terminates at era 5 (not merely floors, like the block reward).
- All of the above (miner leg, validator leg, subsidy) is documented as **liquid on issue** — no
  forced staking or vesting of the reward itself (R9.13, re-ratified by D-0518 on 2026-10-13).

### Mining-specific reward unlock (airdrop/vesting layer, §8.2 — materially changed 2026-10-13)
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
- **Implementation status (Appendix H.4, unchanged conclusion across both 2026-10-13 commits):**
  this entire unlock mechanism is **PARTIAL** — the deployed pallet still vests every tier
  linearly with a *retired* performance adjustment, has no genesis quarter or earn-to-unlock
  credit wired, and lets any tier spend locked principal without the new spend caps. In other
  words: **the 2026-10-13 commits changed the specification text, not (yet) the deployed
  behavior.** This is the single most important finding of this audit for anyone reasoning about
  *current* testnet mining rewards.

### Channel settlement and current public-credit status
- `R11.2b` (unchanged core rule, clarified wording 2026-10-13): current-profile compute-channel
  settlements are **payment-only** — they do not, today, feed public work-vesting credit or block
  reward eligibility. Documented status: **LIVE payment-only**; future audited credit is an open
  item (E.44).
- `R12.1d` (failed/early-close): a documented three-way conservation split
  `P + (1-φ)(E-P) + φ(E-P) = E`, φ = 20%, verified algebraically in this audit's tests (§6).

## 5. Documented vs. implemented vs. provisional vs. not available

See `matrix/verification_matrix.csv` for the full machine-readable matrix (27 rows). Summary
counts by this audit's classification:

| Classification | Meaning used here | Count in matrix |
|---|---|---|
| DOCUMENTED + LIVE | Specified in the yellowpaper AND the appendix states it is implemented in the runtime | 9 |
| DOCUMENTED + PARTIAL | Specified, with the appendix explicitly describing a gap between spec and deployed code | 11 |
| DOCUMENTED + PLANNED | Specified as a requirement, but the appendix states it is designed/not wired | 2 |
| DOCUMENTED + GAP/PENDING | Specified as an open problem the yellowpaper itself has not resolved | 4 |
| Editorial-only (not a new rule) | A 2026-10-13 text clarification the authors themselves flag as non-normative | 1 |

**Every "implemented" status in this matrix is FLOP Labs's own self-reported Appendix H
classification**, not an independent runtime audit by this report. This audit did not have access
to the private `flop-core` runtime source and could not independently verify any `LIVE` claim
against running code. This limitation is stated explicitly in every relevant row of the matrix's
`implemented_status` column and repeated in §7 below.

## 6. Reproducible tests performed

All tests are in `tests/test_reward_accounting.py` (standard library + `pyyaml` only, no network
access, no identity). Two kinds of checks:

1. **Independent re-derivation** of yellowpaper-published formulas/constants from
   `params/flop-protocol-params.yaml`, checked against the values stated in the prose (emission
   halving schedule, four-way reward split, genesis-supply bucket sum, subsidy total, Miner/Agent
   grant unlock formulas, `R_p²` convexity, `G_n` floor semantics, `force_settle` conservation
   identity, BFT quorum rounding).
2. **Invocation of the yellowpaper repository's own published reproduction scripts**
   (`evidence/reproduce.py --check`, `evidence/reproduce-audit.py --check`), run unmodified, with
   their verbatim output captured — this audit did not write or alter their logic, only called
   them and recorded the result.

**Actual run, 2026-10-15, this environment (full output in `tests/results.json`):**

```
TOTAL: 17  PASS: 17  FAIL: 0
```

All 17 checks passed. No test result in this report or in `tests/results.json` was fabricated,
pre-written, or adjusted after the fact — the script was executed once, its stdout captured, and
`results.json` is its direct `json.dump` output. Re-run with:
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
├── report/
│   └── REPORT.md                      <- this file
├── matrix/
│   └── verification_matrix.csv        <- 27-row documented/implemented/provisional/not-available matrix
├── tests/
│   ├── test_reward_accounting.py      <- reproducible, dependency-light verification script
│   └── results.json                   <- actual captured output of the one real run (17/17 pass)
├── official-yellowpaper/              <- unmodified git clone of github.com/flop-labs/yellowpaper
│                                          (HEAD = 70e691c758e53eed17a016a02b0a2ae1200d3744)
└── sources/                           <- (reserved; see note below)
```

Note: `official-yellowpaper/` is a full git clone kept locally for citation traceability and to
run its own `evidence/` scripts. It is **not** modified, **not** re-pushed, and **not** a fork
published anywhere. If a reviewer prefers it excluded from any eventual publication of this audit,
it can be removed and replaced with a pinned commit reference only.

## 9. Explicit statement of compliance with constraints

- No GitHub publication occurred. `git status` in this repository shows only local, uncommitted
  work until a human reviews it.
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
