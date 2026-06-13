import unittest
from pathlib import Path

from scripts.analyze_historical_twins import analyze


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample-historical-election.json"


class HistoricalTwinsTests(unittest.TestCase):
    def test_candidate_vote_mode_counts_equal_votes(self) -> None:
        result = analyze([FIXTURE], "candidate_votes")
        summary = result["summary"]

        self.assertEqual(summary["yearly_pair_counts"], {2022: 11})
        self.assertEqual(len(summary["findings"]), 4)

        first = summary["findings"][0]
        self.assertEqual(first["candidate_name"], "Alpha")
        self.assertEqual(first["votes"], 100)
        self.assertEqual(first["pair_count"], 3)

    def test_top_two_vector_mode_counts_matching_top_two_patterns(self) -> None:
        result = analyze([FIXTURE], "top2_vector")
        summary = result["summary"]

        self.assertEqual(summary["yearly_pair_counts"], {2022: 3})
        self.assertEqual(len(summary["findings"]), 1)
        self.assertEqual(summary["findings"][0]["signature"], [100, 50])

    def test_full_vector_mode_counts_matching_full_vectors(self) -> None:
        result = analyze([FIXTURE], "full_vector")
        summary = result["summary"]

        self.assertEqual(summary["yearly_pair_counts"], {2022: 1})
        self.assertEqual(len(summary["findings"]), 1)
        self.assertEqual(summary["findings"][0]["signature"], [100, 50, 10])


if __name__ == "__main__":
    unittest.main()
