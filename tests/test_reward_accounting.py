#!/usr/bin/env python3
"""Reproducible verification tests for the FLOP Mining Reward Audit.

This script performs ONLY arithmetic/logic checks derivable from the
official yellowpaper text and param file committed in
official-yellowpaper/ (a git clone of https://github.com/flop-labs/yellowpaper,
commit 70e691c758e53eed17a016a02b0a2ae1200d3744, the latest 2026-10-13 sync).

It does NOT invent empirical results, calibration data, or network
measurements. Every assertion here is either:
  (a) a direct re-derivation of a published formula/constant, or
  (b) a call into the yellowpaper's OWN published reproduction scripts
      (evidence/reproduce.py, evidence/reproduce-audit.py), which are
      run unmodified and whose output is reported verbatim.

No private key, DID, or network call is used anywhere in this script.
"""
from __future__ import annotations

import json
import subprocess
import sys
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 50

REPO_ROOT = Path(__file__).resolve().parents[1]
YP_DIR = REPO_ROOT / "official-yellowpaper"
PARAMS_FILE = YP_DIR / "params" / "flop-protocol-params.yaml"

RESULTS: list[dict] = []


def record(name: str, ok: bool, detail: str) -> None:
    RESULTS.append({"test": name, "ok": ok, "detail": detail})
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}: {detail}")


def load_params() -> dict:
    import yaml

    data = yaml.safe_load(PARAMS_FILE.read_text())
    return {p["name"]: p for p in data["parameters"]}


def test_emission_schedule(params: dict) -> None:
    """R9.2: 96 -> 48 -> 24 -> 12 -> 6 -> 3, floor at era 5, forever."""
    initial = Decimal(str(params["initial_block_reward"]["value"]))
    floor = Decimal(str(params["floor_reward"]["value"]))
    max_halvings = int(params["max_halvings"]["value"])

    schedule = [initial]
    for _ in range(max_halvings):
        schedule.append(schedule[-1] / 2)
    computed_floor = schedule[-1]

    ok = (
        schedule == [Decimal(96), Decimal(48), Decimal(24), Decimal(12), Decimal(6), Decimal(3)]
        and computed_floor == floor
    )
    record(
        "R9.2 halving schedule 96->3",
        ok,
        f"schedule={[str(s) for s in schedule]} computed_floor={computed_floor} param_floor_reward={floor}",
    )


def test_block_reward_split(params: dict) -> None:
    """R9.1/R9.5/R9.12: four legs sum to 1000 ppt; era-0 absolute split matches text."""
    miner = int(params["miner_share_ppt"]["value"])
    validator = int(params["validator_share_ppt"]["value"])
    agent = int(params["agent_share_ppt"]["value"])
    staker = int(params["staker_share_ppt"]["value"])
    total_ppt = miner + validator + agent + staker
    ok_sum = total_ppt == 1000

    initial = Decimal(str(params["initial_block_reward"]["value"]))
    era0 = {
        "miner": initial * miner / 1000,
        "validator": initial * validator / 1000,
        "agent": initial * agent / 1000,
        "staker": initial * staker / 1000,
    }
    expected_era0 = {
        "miner": Decimal("72"),
        "validator": Decimal("9.6"),
        "agent": Decimal("9.6"),
        "staker": Decimal("4.8"),
    }
    ok_values = era0 == expected_era0
    record(
        "R9.5/R9.12 four-leg split sums to 1000 ppt",
        ok_sum,
        f"miner={miner} validator={validator} agent={agent} staker={staker} sum={total_ppt}",
    )
    record(
        "§9 era-0 absolute block-reward split matches yellowpaper table",
        ok_values,
        f"computed={ {k: str(v) for k, v in era0.items()} } expected={ {k: str(v) for k, v in expected_era0.items()} }",
    )


def test_genesis_supply(params: dict) -> None:
    """R9.4/R9.7: four genesis buckets sum exactly to genesis_supply."""
    genesis_supply = Decimal(str(params["genesis_supply"]["value"]))
    miner_ad = Decimal(str(params["genesis_miner_airdrop"]["value"]))
    validator_ad = Decimal(str(params["genesis_validator_airdrop"]["value"]))
    agent_ad = Decimal(str(params["genesis_agent_airdrop"]["value"]))
    reserve = Decimal(str(params["genesis_reserve"]["value"]))

    total = miner_ad + validator_ad + agent_ad + reserve
    ok = total == genesis_supply
    record(
        "R9.4/R9.7 genesis buckets sum to genesis_supply",
        ok,
        f"miner={miner_ad} validator={validator_ad} agent={agent_ad} reserve={reserve} "
        f"sum={total} genesis_supply={genesis_supply}",
    )


def test_subsidy_total(params: dict) -> None:
    """R9.3: subsidy halves 16(8+8) -> 8 -> 4 -> 2 -> 1 per recipient-pair across 5 eras,
    terminating at era 5; total = 1,955,232,000 FLOP."""
    per_recipient = Decimal(str(params["subsidy_per_block_per_recipient"]["value"]))  # 8
    halving_interval = int(params["halving_interval_blocks"]["value"])
    duration = int(params["subsidy_duration_blocks"]["value"])

    ok_duration = duration == 5 * halving_interval
    pair_per_era = [per_recipient * 2]
    for _ in range(4):
        pair_per_era.append(pair_per_era[-1] / 2)
    total = sum(p * halving_interval for p in pair_per_era)
    expected_total = Decimal("1955232000")
    ok_total = total == expected_total
    record(
        "R9.3 subsidy duration = 5 * halving_interval_blocks",
        ok_duration,
        f"duration={duration} halving_interval_blocks={halving_interval}",
    )
    record(
        "R9.3 subsidy total = 1,955,232,000 FLOP",
        ok_total,
        f"pair_per_era={[str(p) for p in pair_per_era]} total={total}",
    )


def test_miner_grant_unlock_formula() -> None:
    """R8.7: Miner grant unlocked = min(P - S, floor(P/4) + credit).
    This checks the FORMULA'S documented algebraic properties, not a live
    on-chain value (no network access, no identity). Spot cases from the
    yellowpaper text."""
    def unlocked(p: Decimal, s: Decimal, credit: Decimal) -> Decimal:
        return min(p - s, p // 4 + credit)

    cases = [
        # (P, S, credit, expected)
        (Decimal(1000), Decimal(0), Decimal(0), Decimal(250)),   # quarter at start, no credit yet
        (Decimal(1000), Decimal(0), Decimal(100), Decimal(350)),  # quarter + credit
        (Decimal(1000), Decimal(0), Decimal(1000), Decimal(1000)),  # credit saturates at P-S
        (Decimal(1000), Decimal(200), Decimal(1000), Decimal(800)),  # slash reduces the ceiling P-S
    ]
    all_ok = True
    details = []
    for p, s, credit, expected in cases:
        got = unlocked(p, s, credit)
        ok = got == expected
        all_ok = all_ok and ok
        details.append(f"P={p} S={s} credit={credit} -> got={got} expected={expected} ok={ok}")
    record("R8.7 Miner grant unlock formula spot-checks", all_ok, "; ".join(details))


def test_agent_grant_unlock_formula() -> None:
    """R8.7: Agent grant unlocked = floor(K/3), locked spend C capped at floor(3P/4)."""
    def agent_unlocked(k: Decimal) -> Decimal:
        return k // 3

    cases = [
        (Decimal(0), Decimal(0)),
        (Decimal(3), Decimal(1)),
        (Decimal(9), Decimal(3)),
        (Decimal(10), Decimal(3)),  # floor
    ]
    all_ok = True
    details = []
    for k, expected in cases:
        got = agent_unlocked(k)
        ok = got == expected
        all_ok = all_ok and ok
        details.append(f"K={k} -> got={got} expected={expected} ok={ok}")
    record("R8.7 Agent grant unlock formula floor(K/3) spot-checks", all_ok, "; ".join(details))

    # spend cap check: C <= floor(3P/4)
    p = Decimal(1000)
    cap = (3 * p) // 4
    ok_cap = cap == Decimal(750)
    record("R8.7 Agent locked-spend cap floor(3P/4)", ok_cap, f"P={p} cap={cap}")


def test_performance_vesting_convexity() -> None:
    """§8 work-vesting grant (R_p^2): R_p clamped to [0,1], unlock rate = R_p^2 <= R_p."""
    def unlock_rate(g_actual: Decimal, b_p: Decimal) -> tuple[Decimal, Decimal]:
        r_p = min(g_actual / b_p, Decimal(1))
        return r_p * r_p, r_p

    cases = [
        (Decimal(50), Decimal(100)),  # R_p = 0.5 -> unlock 0.25 (yellowpaper's own worked example)
        (Decimal(100), Decimal(100)),  # R_p = 1 -> unlock 1
        (Decimal(150), Decimal(100)),  # overperformance clamped to R_p=1 -> unlock 1
    ]
    all_ok = True
    details = []
    for g, b in cases:
        rate, r_p = unlock_rate(g, b)
        convex_ok = rate <= r_p
        details.append(f"G_actual={g} B_p={b} R_p={r_p} unlock_rate={rate} convex_le_Rp={convex_ok}")
        all_ok = all_ok and convex_ok
    # explicit worked example from the yellowpaper text: R_p=0.5 -> unlock 0.25
    worked_rate, worked_rp = unlock_rate(Decimal(50), Decimal(100))
    ok_worked = worked_rp == Decimal("0.5") and worked_rate == Decimal("0.25")
    record("§8 R_p^2 convexity holds (unlock_rate <= R_p) for sampled ratios", all_ok, "; ".join(details))
    record("§8 worked example R_p=0.5 -> unlock=0.25 matches yellowpaper text", ok_worked,
           f"R_p={worked_rp} unlock_rate={worked_rate}")


def test_gn_unit_floor() -> None:
    """R4.1/R4.4: G_n = floor(F_eff / 1e9), whole-unit, no rounding up."""
    cases = [
        (Decimal("999999999"), 0),
        (Decimal("1000000000"), 1),
        (Decimal("1999999999"), 1),
        (Decimal("2000000000"), 2),
    ]
    all_ok = True
    details = []
    for f_eff, expected in cases:
        g_n = int(f_eff // Decimal(10**9))
        ok = g_n == expected
        all_ok = all_ok and ok
        details.append(f"F_eff={f_eff} -> G_n={g_n} expected={expected}")
    record("R4.1/R4.4 G_n = floor(F_eff/1e9), floors (never rounds up)", all_ok, "; ".join(details))


def test_force_settle_conservation() -> None:
    """R12.1d: P + (1-phi)(E-P) + phi(E-P) = E, for P <= E, phi=20%."""
    phi = Decimal("0.20")
    cases = [
        (Decimal(1000), Decimal(300)),  # E, P
        (Decimal(500), Decimal(500)),   # P == E, no refund/penalty
        (Decimal(1000), Decimal(0)),    # non-delivery-like (though phi=0 case is separate text rule)
    ]
    all_ok = True
    details = []
    for e, p in cases:
        refund = (1 - phi) * (e - p)
        penalty = phi * (e - p)
        total = p + refund + penalty
        ok = total == e
        all_ok = all_ok and ok
        details.append(f"E={e} P={p} refund={refund} penalty={penalty} total={total} ok={ok}")
    record("R12.1d force_settle conservation P+(1-phi)(E-P)+phi(E-P)=E", all_ok, "; ".join(details))


def test_bft_quorum_threshold(params: dict) -> None:
    """R3.6b: ceil(active_count * validator_attestation_threshold).max(1), threshold default 2/3.

    Uses exact integer arithmetic throughout (no float), so the ceiling cannot be
    perturbed by binary floating-point rounding at any active_count. Cross-checked
    against validator_active_set_cap (1,000) and well beyond it.
    """
    threshold_parts = int(params["validator_attestation_threshold"]["value"])  # perbill, 666_666_666
    threshold = Decimal(threshold_parts) / Decimal(10**9)
    ok_threshold = abs(threshold - Decimal(2) / Decimal(3)) < Decimal("1e-8")

    def quorum(active_count: int) -> int:
        # ceil(active_count * threshold_parts / 1e9) via exact integer ceil division.
        numerator = active_count * threshold_parts
        denominator = 10**9
        return max(-(-numerator // denominator), 1)

    cases = [(1, 1), (3, 2), (4, 3), (100, 67), (200, 134)]
    all_ok = True
    details = []
    for active, expected in cases:
        got = quorum(active)
        ok = got == expected
        all_ok = all_ok and ok
        details.append(f"active_count={active} -> quorum={got} expected={expected}")

    validator_active_set_cap = int(params["validator_active_set_cap"]["value"])  # 1,000
    # Independent cross-check: compare the exact-integer ceil against Decimal's
    # ROUND_CEILING at every active_count from 1 up to 3x the documented cap, to
    # rule out an off-by-one at any boundary a spot-check might miss.
    from decimal import ROUND_CEILING

    mismatches = []
    for active in range(1, validator_active_set_cap * 3 + 1):
        exact_decimal_ceil = int((Decimal(active) * threshold).to_integral_value(rounding=ROUND_CEILING))
        exact_decimal_ceil = max(exact_decimal_ceil, 1)
        if quorum(active) != exact_decimal_ceil:
            mismatches.append((active, quorum(active), exact_decimal_ceil))
    ok_sweep = not mismatches

    record("R3.6b default validator_attestation_threshold ~= 2/3", ok_threshold,
           f"threshold_parts={threshold_parts} threshold={threshold}")
    record("R3.6b quorum = ceil(active_count * threshold).max(1) spot-checks", all_ok, "; ".join(details))
    record(
        f"R3.6b exact-integer quorum matches Decimal ROUND_CEILING for active_count in [1, {validator_active_set_cap * 3}]",
        ok_sweep,
        f"mismatches={mismatches[:5]}" if mismatches else f"0 mismatches over {validator_active_set_cap * 3} values (cap={validator_active_set_cap})",
    )


def run_official_reproduce_scripts() -> None:
    """Run the yellowpaper repo's OWN published reproduction scripts, unmodified,
    with --check (fail if committed artifacts differ from what the script derives).
    Output is reported verbatim; this script does not alter their logic."""
    for script in ("evidence/reproduce.py", "evidence/reproduce-audit.py"):
        path = YP_DIR / script
        if not path.exists():
            record(f"official script present: {script}", False, "missing from clone")
            continue
        try:
            proc = subprocess.run(
                [sys.executable, str(path), "--check"],
                cwd=YP_DIR,
                capture_output=True,
                text=True,
                timeout=120,
            )
            ok = proc.returncode == 0
            out = (proc.stdout.strip() + " " + proc.stderr.strip()).strip()
            record(f"official script `{script} --check`", ok, out or f"exit_code={proc.returncode}")
        except Exception as exc:  # pragma: no cover - defensive
            record(f"official script `{script} --check`", False, f"exception: {exc}")


def main() -> int:
    params = load_params()
    test_emission_schedule(params)
    test_block_reward_split(params)
    test_genesis_supply(params)
    test_subsidy_total(params)
    test_miner_grant_unlock_formula()
    test_agent_grant_unlock_formula()
    test_performance_vesting_convexity()
    test_gn_unit_floor()
    test_force_settle_conservation()
    test_bft_quorum_threshold(params)
    run_official_reproduce_scripts()

    out_path = REPO_ROOT / "tests" / "results.json"
    out_path.write_text(json.dumps(RESULTS, indent=2))

    failed = [r for r in RESULTS if not r["ok"]]
    print()
    print(f"TOTAL: {len(RESULTS)}  PASS: {len(RESULTS) - len(failed)}  FAIL: {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
