"""
Package data loader.

Parses a CSV export of the WGUPS Package File and returns a list of
Package objects.  The expected columns are:
  package_id, address, city, state, zip_code, deadline, weight, special_notes
"""

import csv

from package import Package


def load_data(filename):
    """Read package data from *filename* and return a list of Package objects."""
    packages = []
    with open(filename, "r", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header
        for row in reader:
            if not row or not row[0].strip():
                continue
            (
                package_id,
                address,
                city,
                state,
                zip_code,
                deadline,
                weight,
                special_notes,
            ) = row
            packages.append(
                Package(
                    package_id=int(package_id.strip()),
                    address=address.strip(),
                    city=city.strip(),
                    state=state.strip(),
                    zip_code=zip_code.strip(),
                    deadline=deadline.strip(),
                    weight=float(weight.strip()) if weight.strip() else 0.0,
                    status="at hub",
                    special_notes=special_notes.strip(),
                    truck_id=None,
                    delivery_time=None,
                )
            )
    return packages
