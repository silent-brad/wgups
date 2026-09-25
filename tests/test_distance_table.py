"""Unit tests for the DistanceTable."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from distance_table import DistanceTable


class TestDistanceTable(unittest.TestCase):
    def setUp(self):
        self.addresses = [
            "4001 South 700 East",
            "195 W Oakland Ave",
            "2530 S 500 E",
        ]
        self.matrix = [
            [0.0, 3.5, 7.2],
            [3.5, 0.0, 4.1],
            [7.2, 4.1, 0.0],
        ]
        self.dt = DistanceTable(self.addresses, self.matrix)

    def test_get_distance(self):
        self.assertEqual(
            self.dt.get_distance("4001 South 700 East", "195 W Oakland Ave"), 3.5
        )
        self.assertEqual(
            self.dt.get_distance("195 W Oakland Ave", "4001 South 700 East"), 3.5
        )

    def test_symmetry(self):
        for a in self.addresses:
            for b in self.addresses:
                self.assertEqual(
                    self.dt.get_distance(a, b),
                    self.dt.get_distance(b, a),
                )

    def test_zero_diagonal(self):
        for a in self.addresses:
            self.assertEqual(self.dt.get_distance(a, a), 0.0)

    def test_get_hub_distance(self):
        # get_hub_distance returns the diagonal entry (address to itself)
        self.assertEqual(self.dt.get_hub_distance("195 W Oakland Ave"), 0.0)

    def test_invalid_address_raises(self):
        with self.assertRaises(ValueError):
            self.dt.get_distance("4001 South 700 East", "Invalid Address")

    def test_repr(self):
        self.assertIn("3 addresses", repr(self.dt))


if __name__ == "__main__":
    unittest.main()
