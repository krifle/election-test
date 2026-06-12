#!/usr/bin/env python3
"""허명회 교수의 쌍둥이 득표 이항모형을 정확 계산하고 모의실험한다."""

from __future__ import annotations

import argparse
import math
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_N = 4470
DEFAULT_P = 3030 / 4470


def _validate_parameters(n: int, p: float) -> None:
    if n < 1:
        raise ValueError("n은 1 이상이어야 합니다.")
    if not 0.0 <= p <= 1.0:
        raise ValueError("p는 0과 1 사이여야 합니다.")


def binomial_pmf(n: int, p: float) -> list[float]:
    """상대확률 점화식으로 안정적으로 Binomial(n, p) PMF를 만든다."""
    _validate_parameters(n, p)
    if p == 0.0:
        return [1.0] + [0.0] * n
    if p == 1.0:
        return [0.0] * n + [1.0]

    q = 1.0 - p
    mode = min(n, int(math.floor((n + 1) * p)))
    weights = [0.0] * (n + 1)
    weights[mode] = 1.0

    for k in range(mode, n):
        weights[k + 1] = weights[k] * ((n - k) / (k + 1)) * (p / q)

    for k in range(mode, 0, -1):
        weights[k - 1] = weights[k] * (k / (n - k + 1)) * (q / p)

    total = math.fsum(weights)
    return [weight / total for weight in weights]


def collision_probability(n: int, p: float) -> float:
    """독립인 X, Y ~ Binomial(n, p)에 대해 P(X = Y)를 계산한다."""
    pmf = binomial_pmf(n, p)
    return math.fsum(probability * probability for probability in pmf)


def local_clt_approximation(n: int, p: float) -> float:
    """차이 X-Y에 대한 국소 중심극한정리 근사."""
    _validate_parameters(n, p)
    if p in (0.0, 1.0):
        return 1.0
    return 1.0 / math.sqrt(4.0 * math.pi * n * p * (1.0 - p))


def multiple_comparison_summary(
    districts: int,
    similar_pair_rate: float,
    pair_collision_probability: float,
) -> dict[str, float]:
    if districts < 2:
        raise ValueError("행정동 수는 2 이상이어야 합니다.")
    if not 0.0 <= similar_pair_rate <= 1.0:
        raise ValueError("유사한 쌍 비율은 0과 1 사이여야 합니다.")

    all_pairs = districts * (districts - 1) / 2
    eligible_pairs = all_pairs * similar_pair_rate
    expected_matches = eligible_pairs * pair_collision_probability
    poisson_at_least_one = 1.0 - math.exp(-expected_matches)
    return {
        "all_pairs": all_pairs,
        "eligible_pairs": eligible_pairs,
        "expected_matches": expected_matches,
        "poisson_at_least_one": poisson_at_least_one,
    }


def _chunk_sizes(total: int, batch_size: int) -> Iterable[int]:
    remaining = total
    while remaining:
        current = min(batch_size, remaining)
        yield current
        remaining -= current


def _simulate_chunk(payload: tuple[int, int, float, int, int]) -> tuple[int, int]:
    import numpy as np

    size, n, p, seed, chunk_index = payload
    seed_sequence = np.random.SeedSequence([seed, chunk_index])
    rng = np.random.default_rng(seed_sequence)
    first = rng.binomial(n, p, size=size)
    second = rng.binomial(n, p, size=size)
    matches = int(np.count_nonzero(first == second))
    return size, matches


@dataclass
class Checkpoint:
    trials: int
    matches: int
    estimate: float
    elapsed_seconds: float


def run_simulation(
    *,
    trials: int,
    n: int,
    p: float,
    seed: int,
    batch_size: int,
    workers: int,
) -> tuple[int, list[Checkpoint], float]:
    _validate_parameters(n, p)
    if trials < 1:
        raise ValueError("trials는 1 이상이어야 합니다.")
    if batch_size < 1:
        raise ValueError("batch-size는 1 이상이어야 합니다.")
    if workers < 1:
        raise ValueError("workers는 1 이상이어야 합니다.")

    sizes = list(_chunk_sizes(trials, batch_size))
    payloads = [
        (size, n, p, seed, chunk_index)
        for chunk_index, size in enumerate(sizes)
    ]
    started = time.perf_counter()
    completed_trials = 0
    matches = 0
    checkpoints: list[Checkpoint] = []
    report_every = max(1, len(payloads) // 100)

    if workers == 1:
        results = map(_simulate_chunk, payloads)
        executor = None
    else:
        from concurrent.futures import ProcessPoolExecutor

        executor = ProcessPoolExecutor(max_workers=workers)
        results = executor.map(_simulate_chunk, payloads, chunksize=1)

    try:
        for index, (size, chunk_matches) in enumerate(results, start=1):
            completed_trials += size
            matches += chunk_matches
            elapsed = time.perf_counter() - started
            checkpoint = Checkpoint(
                trials=completed_trials,
                matches=matches,
                estimate=matches / completed_trials,
                elapsed_seconds=elapsed,
            )
            checkpoints.append(checkpoint)

            if index % report_every == 0 or index == len(payloads):
                percent = completed_trials / trials * 100.0
                print(
                    f"\r{percent:6.2f}% | {completed_trials:,}회 | "
                    f"일치 {matches:,}회 | 추정 {checkpoint.estimate:.9f}",
                    end="",
                    flush=True,
                )
    finally:
        if executor is not None:
            executor.shutdown()

    elapsed = time.perf_counter() - started
    print()
    return matches, checkpoints, elapsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="두 독립 Binomial(n, p)의 결과가 같은 확률을 모의실험합니다."
    )
    parser.add_argument("--trials", type=int, default=1_000_000)
    parser.add_argument("--n", type=int, default=DEFAULT_N)
    parser.add_argument("--p", type=float, default=DEFAULT_P)
    parser.add_argument("--seed", type=int, default=20260603)
    parser.add_argument("--batch-size", type=int, default=1_000_000)
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, min(4, os.cpu_count() or 1)),
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="브라우저에서 불러올 결과 JSON 경로",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    exact = collision_probability(args.n, args.p)
    approximation = local_clt_approximation(args.n, args.p)

    print(f"모형: X, Y ~ Binomial(n={args.n}, p={args.p:.12f}), 서로 독립")
    print(f"정확한 P(X=Y): {exact:.12f} ({exact * 100:.6f}%)")
    print(f"국소 CLT 근사:  {approximation:.12f}")
    print(
        f"Monte Carlo: {args.trials:,}회, workers={args.workers}, "
        f"batch={args.batch_size:,}"
    )

    matches, checkpoints, elapsed = run_simulation(
        trials=args.trials,
        n=args.n,
        p=args.p,
        seed=args.seed,
        batch_size=args.batch_size,
        workers=args.workers,
    )
    estimate = matches / args.trials
    standard_error = math.sqrt(estimate * (1.0 - estimate) / args.trials)
    confidence_interval = [
        max(0.0, estimate - 1.96 * standard_error),
        min(1.0, estimate + 1.96 * standard_error),
    ]

    print(f"일치 횟수: {matches:,}")
    print(f"추정 확률: {estimate:.12f} ({estimate * 100:.6f}%)")
    print(
        "95% Monte Carlo 구간: "
        f"[{confidence_interval[0]:.12f}, {confidence_interval[1]:.12f}]"
    )
    print(f"정확값과 차이: {estimate - exact:+.12f}")
    print(f"실행 시간: {elapsed:.2f}초")

    if args.output:
        import json

        result = {
            "schema_version": 1,
            "model": {
                "n": args.n,
                "p": args.p,
                "seed": args.seed,
                "trials": args.trials,
                "batch_size": args.batch_size,
                "workers": args.workers,
            },
            "exact_probability": exact,
            "local_clt_approximation": approximation,
            "matches": matches,
            "estimate": estimate,
            "standard_error": standard_error,
            "confidence_interval_95": confidence_interval,
            "elapsed_seconds": elapsed,
            "checkpoints": [asdict(checkpoint) for checkpoint in checkpoints],
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"JSON 저장: {args.output}")


if __name__ == "__main__":
    main()
