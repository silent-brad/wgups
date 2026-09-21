"""
DistanceTable provides O(1) distance lookups between delivery addresses.

The table stores a symmetric distance matrix keyed by full address string.
Because the matrix is square, each address maps to the same row and column
index, so dist(a,b) = matrix[row(a)][col(b)].
"""


class DistanceTable:
    """
    Store a symmetric distance matrix keyed by address.

    Parameters
    ----------
    addresses : list[str]
        Ordered list of location strings (hub must be included).
    matrix : list[list[float]]
        Square 2-D list where matrix[i][j] is the miles from
        addresses[i] to addresses[j].
    """

    def __init__(self, addresses, matrix):
        self.addresses = addresses
        self.distance_table = matrix
        self.address_to_index = {}
        for idx, addr in enumerate(addresses):
            self.address_to_index[addr] = (idx, idx)

    def get_distance(self, address_a, address_b):
        """Return the miles between *address_a* and *address_b*."""
        row_index_a, _ = self.address_to_index[address_a]
        _, col_index_b = self.address_to_index[address_b]
        return self.distance_table[row_index_a][col_index_b]

    def get_hub_distance(self, address):
        """Return the miles from the hub to *address*."""
        row_index, col_index = self.address_to_index[address]
        return self.distance_table[row_index][col_index]

    def __repr__(self):
        return f"DistanceTable({len(self.addresses)} addresses)"
