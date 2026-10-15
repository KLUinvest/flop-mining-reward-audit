# FLOP Testnet Mining — Verified Compute & Reward Accounting (draft audit)

This repository is a **publicly available, independent** technical audit of the official FLOP Network Yellow
Paper (`flop-labs/yellowpaper`, v0.5.0 draft), focused specifically on two questions:

1. What are the official rules for computing mining/validator/agent rewards?
2. What are the official rules for verifying that claimed compute actually happened?

It also tracks what changed in the two commits the yellowpaper's own repository published on
**2026-10-13**, and classifies every mechanism it covers as one of: specified-and-self-reported
**LIVE**, specified-but-self-reported **PARTIAL**, specified-but-self-reported **PLANNED**,
specified-as-an-**open problem** by the source document itself, or **editorial-only** (no rule
change).

## Start here

Read, in this order:

1. **`report/REPORT.md`** — the full analysis. Start with §1 (sources, exact commits) and §2
   (what changed on 2026-10-13), then §3–§4 (compute verification / reward accounting rules), §5
   (the matrix summary + a methodology review of the matrix and test script itself), §6 (the
   actual reproducible test run), §7 (limitations, read this before trusting any conclusion), §9
   (what was and was not done, relative to the constraints this audit operated under).
2. **`matrix/verification_matrix.csv`** — 27 rows, one per mechanism, each citing an exact
   `yellowpaper.md` line number and commit hash. Machine-readable; open with any spreadsheet tool
   or `csv` reader.
3. **`tests/test_reward_accounting.py`** — the reproducible verification script. Re-run it
   yourself:
   ```bash
   cd /root/flop/flop-mining-reward-audit
   python3 tests/test_reward_accounting.py
   ```
   It requires `pyyaml` (`pip install pyyaml`) and a populated `official-yellowpaper/` checkout
   (see below). It makes no network calls and touches no private key or identity.
4. **`tests/results.json`** — the literal captured output of the most recent real run of that
   script (not hand-edited).

## The single most important caveat

**Every "LIVE" / "PARTIAL" / "PLANNED" / "GAP" label anywhere in this repository (report, matrix,
or test comments) is FLOP Labs's own self-reported status from the yellowpaper's own
Appendix H** — not an independent runtime audit. This audit had no access to the private
`flop-core` runtime source and verified no claim against actually running code. Formulas and
constants *were* independently re-derived and checked (that is what `tests/` does); deployment
status was *not*. Read §5 and §7 of `report/REPORT.md` for the full statement of this boundary.

## What `official-yellowpaper/` is

A local, read-only `git clone` of `https://github.com/flop-labs/yellowpaper`, pinned at commit
`70e691c758e53eed17a016a02b0a2ae1200d3744` (the latest sync at analysis time). It is:
- **not** tracked by this repository's own git history (see `.gitignore`) — it is a separate
  nested checkout, kept on disk for citation traceability and so `tests/` can invoke its
  `evidence/reproduce*.py` scripts,
- **not** modified in any way,
- **not** re-pushed, forked, or published anywhere by this audit.

If you've cloned/received this repository without that nested checkout, re-create it with:
```bash
git clone https://github.com/flop-labs/yellowpaper.git official-yellowpaper
git -C official-yellowpaper checkout 70e691c758e53eed17a016a02b0a2ae1200d3744
```
then re-run the test script.

## Status of this work

This is a **local draft**, already committed to this repository's own local git history (run
`git log` to see the commit(s)). It has **not** been pushed to any remote, announced on
Technocore, or published anywhere. No private key or DID was used in producing it. It is held
for human review; see `report/REPORT.md` §9 for the explicit statement of what was and was not
done against the constraints this audit operated under.
