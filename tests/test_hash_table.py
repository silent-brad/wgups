"""Unit tests for the custom chaining hash table."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hash_table import HashTable


class TestHashTable(unittest.TestCase):
    def setUp(self):
        self.ht = HashTable(initial_capacity=4)

    def test_insert_and_lookup(self):
        self.ht.insert(1, "package_a")
        self.assertEqual(self.ht.lookup(1), "package_a")

    def test_lookup_missing_key(self):
        self.assertIsNone(self.ht.lookup(99))

    def test_overwrite_existing_key(self):
        self.ht.insert(1, "package_a")
        self.ht.insert(1, "package_b")
        self.assertEqual(self.ht.lookup(1), "package_b")
        self.assertEqual(self.ht.size, 1)

    def test_collision_handling(self):
        # With capacity 4, keys 1 and 5 both hash to bucket 1
        self.ht.insert(1, "package_1")
        self.ht.insert(5, "package_5")
        self.assertEqual(self.ht.lookup(1), "package_1")
        self.assertEqual(self.ht.lookup(5), "package_5")
        self.assertEqual(self.ht.size, 2)

    def test_collision_overwrite(self):
        self.ht.insert(1, "package_1")
        self.ht.insert(5, "package_5")
        self.ht.insert(5, "updated")
        self.assertEqual(self.ht.lookup(5), "updated")
        self.assertEqual(self.ht.size, 2)

    def test_resize_doubles_capacity(self):
        old_capacity = len(self.ht.buckets)
        # Insert enough items to exceed load factor 0.75
        for i in range(5):
            self.ht.insert(i, f"package_{i}")
        new_capacity = len(self.ht.buckets)
        self.assertGreater(new_capacity, old_capacity)
        self.assertEqual(new_capacity, old_capacity * 2)
        # All data survives resize
        for i in range(5):
            self.assertEqual(self.ht.lookup(i), f"package_{i}")

    def test_resize_preserves_collisions(self):
        self.ht.insert(1, "package_1")
        self.ht.insert(5, "package_5")
        self.ht.resize()
        self.assertEqual(self.ht.lookup(1), "package_1")
        self.assertEqual(self.ht.lookup(5), "package_5")
        self.assertEqual(self.ht.size, 2)

    def test_large_number_of_inserts(self):
        for i in range(100):
            self.ht.insert(i, f"val_{i}")
        for i in range(100):
            self.assertEqual(self.ht.lookup(i), f"val_{i}")
        self.assertEqual(self.ht.size, 100)

    def test_load_factor_after_multiple_resizes(self):
        for i in range(50):
            self.ht.insert(i, f"val_{i}")
        load_factor = self.ht.size / len(self.ht.buckets)
        self.assertLessEqual(load_factor, 0.75)


if __name__ == "__main__":
    unittest.main()
