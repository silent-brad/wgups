"""
Custom chaining hash table implemented from scratch using only built-in
Python data structures (lists).

Process:
  Keys (package_id integers) are hashed into bucket indices with modulo
  arithmetic. Collisions are resolved by chaining: each bucket holds a
  list of (key, value) tuples. When the load factor exceeds 0.75 the
  table automatically doubles in size and rehashes all entries. This
  keeps average lookup time O(1).

Flow:
  insert(package_id, package) -> _hash -> find bucket -> append or replace
  lookup(package_id)          -> _hash -> find bucket -> linear search
  resize()                    -> double buckets -> rehash all entries
"""


class HashTable:
    """
    Chaining hash table mapping integer package IDs to Package records.

    Attributes
    ----------
    buckets : list[list[tuple[int, Package]]]
        Array of chain lists.  Each chain holds (package_id, package) tuples.
    size : int
        Number of unique keys currently stored.
    """

    def __init__(self, initial_capacity=40):
        self.buckets = [[] for _ in range(initial_capacity)]
        self.size = 0

    def _hash(self, package_id):
        """Map a package_id to a bucket index."""
        return package_id % len(self.buckets)

    def _insert_no_resize(self, package_id, package):
        """Internal insert used by resize to avoid recursive resizing."""
        bucket = self.buckets[self._hash(package_id)]
        for i, (pid, _) in enumerate(bucket):
            if pid == package_id:
                bucket[i] = (package_id, package)
                return
        bucket.append((package_id, package))
        self.size += 1

    def insert(self, package_id, package):
        """
        Insert a package record keyed by *package_id*.

        If the key already exists, the old record is overwritten.
        After insertion the load factor is checked; if it exceeds 0.75
        the table doubles in capacity and rehashes all entries.
        """
        self._insert_no_resize(package_id, package)
        if self.size / len(self.buckets) > 0.75:
            self.resize()

    def lookup(self, package_id):
        """
        Return the Package record for *package_id*, or None if not found.

        The returned Package contains all required lookup fields:
        delivery address, deadline, city, zip code, weight, and status
        (including delivery time when applicable).
        """
        bucket = self.buckets[self._hash(package_id)]
        for pid, package in bucket:
            if pid == package_id:
                return package
        return None

    def resize(self):
        """Double the bucket count and rehash all entries."""
        old_buckets = self.buckets
        self.buckets = [[] for _ in range(len(old_buckets) * 2)]
        self.size = 0
        for bucket in old_buckets:
            for package_id, package in bucket:
                self._insert_no_resize(package_id, package)

    def __repr__(self):
        return str(self.buckets)
