import math
import unittest

from simulate import (
    collision_probability,
    local_clt_approximation,
    multiple_comparison_summary,
)


class ProbabilityTests(unittest.TestCase):
    def test_songdo_exact_probability(self) -> None:
        actual = collision_probability(4470, 3030 / 4470)
        self.assertAlmostEqual(actual, 0.0090289582214375, places=12)

    def test_probability_is_symmetric_around_half(self) -> None:
        self.assertAlmostEqual(
            collision_probability(1000, 0.2),
            collision_probability(1000, 0.8),
            places=14,
        )

    def test_degenerate_coin_always_matches(self) -> None:
        self.assertEqual(collision_probability(100, 0.0), 1.0)
        self.assertEqual(collision_probability(100, 1.0), 1.0)

    def test_local_clt_is_close_for_songdo(self) -> None:
        exact = collision_probability(4470, 3030 / 4470)
        approximation = local_clt_approximation(4470, 3030 / 4470)
        self.assertLess(abs(approximation - exact), 2e-7)

    def test_huh_multiple_comparison_numbers(self) -> None:
        probability = collision_probability(4470, 3030 / 4470)
        summary = multiple_comparison_summary(137, 0.01, probability)
        self.assertEqual(summary["all_pairs"], 9316)
        self.assertAlmostEqual(summary["eligible_pairs"], 93.16)
        self.assertAlmostEqual(
            summary["expected_matches"],
            93.16 * probability,
        )
        self.assertAlmostEqual(
            summary["poisson_at_least_one"],
            1 - math.exp(-summary["expected_matches"]),
        )


if __name__ == "__main__":
    unittest.main()
