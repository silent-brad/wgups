# Student ID: bwhi880
"""
WGUPS Routing Program

This program loads package and distance data, constructs a custom chaining
hash table, plans delivery routes using a Clarke-Wright savings heuristic
polished by 2-opt local search, simulates truck movement, and provides a
CLI for querying package status at any time of day.

Process overview:
  1. Load the WGUPS Distance Table CSV into a DistanceTable object.
  2. Load the WGUPS Package File CSV into Package objects.
  3. Insert every Package into a custom HashTable keyed by package_id.
  4. Apply initial status constraints (flight-delayed, wrong-address).
  5. Plan routes: assign packages to three trucks respecting hard
     constraints (capacity, truck-2-only, delayed arrivals, grouped deliveries).
  6. At 10:20 a.m., correct package #9's address and rebuild Truck 3's route.
  7. Set departure times (Trucks 1 & 2 at 8:00, Truck 3 at ~10:30).
  8. Simulate deliveries: drive each truck, accumulate mileage, record
     delivery timestamps back into the HashTable.
  9. Enter a CLI loop where the user queries status at any time.

Program flow:
  main() -> _load_distance_table -> _load_packages -> HashTable.insert
         -> build_routes -> correct address pkg #9 -> rebuild truck 3 route
         -> Truck.depart -> simulate_deliveries -> interactive query loop
"""

import csv
import os

from delivery_simulator import simulate_deliveries
from distance_table import DistanceTable
from hash_table import HashTable
from package import Package
from route_planner import build_route_for_truck, build_routes, two_opt

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _time_to_float(time_str):
    """Convert '8:00 AM' or '10:30 AM' to a float hour value."""
    time_str = time_str.strip().upper()
    if time_str == "EOD":
        return 17.0  # 5:00 p.m.
    parts = time_str.split()
    hm = parts[0]
    ampm = parts[1] if len(parts) > 1 else "AM"
    h, m = map(int, hm.split(":"))
    if ampm == "PM" and h != 12:
        h += 12
    if ampm == "AM" and h == 12:
        h = 0
    return h + m / 60.0


def _load_distance_table(csv_path):
    """
    Parse a distance CSV where:
      - Row 0 is a header with destination addresses.
      - Column 0 of every row is the origin address.
      - Remaining cells are float distances (symmetric matrix).
    Returns a DistanceTable instance.
    """
    with open(csv_path, "r", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Header row gives destination addresses (skip first blank/header cell)
    addresses = [cell.strip() for cell in rows[0][1:]]
    # Prepend the hub address from the first data row
    hub_address = rows[1][0].strip()
    if hub_address not in addresses:
        addresses.insert(0, hub_address)

    n = len(addresses)
    matrix = [[0.0] * n for _ in range(n)]

    for i, row in enumerate(rows[1:]):
        origin = row[0].strip()
        row_idx = addresses.index(origin)
        for j, cell in enumerate(row[1:], start=0):
            if cell.strip():
                matrix[row_idx][j] = float(cell)
                matrix[j][row_idx] = float(cell)

    return DistanceTable(addresses, matrix)


def _load_packages(csv_path):
    """
    Parse a package CSV.
    Expected columns (in order):
      package_id, address, city, state, zip_code, deadline, weight, special_notes
    """
    packages = []
    with open(csv_path, "r", newline="") as f:
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


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


def main():
    # Resolve data directory regardless of whether main.py or a .pyc is running.
    _src_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(_src_dir) == "__pycache__":
        _src_dir = os.path.dirname(_src_dir)
    base_dir = os.path.join(_src_dir, "..", "data")
    base_dir = os.path.normpath(base_dir)
    dist_path = os.path.join(base_dir, "WGUPS Distance Table.csv")
    pkg_path = os.path.join(base_dir, "WGUPS Package File.csv")

    # 1. Load distance table.
    distance_table = _load_distance_table(dist_path)
    hub_address = "4001 South 700 East"  # WGUPS hub

    # 2. Load packages and insert into the custom hash table.
    packages = _load_packages(pkg_path)
    hash_table = HashTable(initial_capacity=64)
    for pkg in packages:
        hash_table.insert(pkg.package_id, pkg)

    # 3. Apply initial status constraints.
    #    Packages delayed by a late flight are "delayed" until 9:05 a.m.
    #    Package #9 has a wrong address and is "delayed" until 10:20 a.m.
    for pkg in packages:
        notes = (pkg.special_notes or "").lower()
        if ("delayed" in notes and "9:05" in notes) or pkg.package_id == 9:
            pkg.status = "delayed"
            hash_table.insert(pkg.package_id, pkg)

    # 4. Plan routes: assign packages to trucks and optimize stop order.
    trucks = build_routes(packages, distance_table, hub_address)

    # Record which truck each package belongs to.
    for truck in trucks:
        for pkg in truck.packages:
            pkg.truck_id = truck.truck_id
            hash_table.insert(pkg.package_id, pkg)

    # 5. Set departure times respecting the two-driver limit and constraints.
    #    Truck 1 departs at 8:00 a.m.
    trucks[0].depart(8.0)
    #    Truck 2 departs at 8:00 a.m. unless it carries packages delayed until 9:05.
    truck2_depart = 8.0
    for pkg in trucks[1].packages:
        notes = (pkg.special_notes or "").lower()
        if "delayed" in notes and "9:05" in notes:
            truck2_depart = 9.0 + 5.0 / 60.0  # 9:05 a.m.
            break
    trucks[1].depart(truck2_depart)

    # 5a. Address correction for package #9 at 10:20 a.m.
    #     The original CSV listed the wrong address (300 State St).
    #     At 10:20 a.m. WGUPS receives the correct address.  Because
    #     Truck 3 does not depart until 10:30 a.m., the route is rebuilt
    #     now so the truck drives to the corrected destination.
    pkg9 = hash_table.lookup(9)
    if pkg9 and len(trucks) > 2:
        pkg9.address = "410 S State St"
        pkg9.zip_code = "84111"
        hash_table.insert(9, pkg9)
        trucks[2].route = build_route_for_truck(
            trucks[2].packages, distance_table, hub_address, trucks[2].capacity
        )
        trucks[2].route = two_opt(
            [hub_address] + trucks[2].route + [hub_address], distance_table
        )[1:-1]

    #    Truck 3 departs when a driver returns (~10:30 a.m.).
    if len(trucks) > 2:
        trucks[2].depart(10.5)

    # 6. Run the delivery simulation.
    total_miles = simulate_deliveries(trucks, distance_table, hash_table, hub_address)

    # 7. CLI for status queries.
    print("=" * 60)
    print("WGUPS Routing Program")
    print("=" * 60)
    print(f"Total mileage for all trucks: {total_miles:.1f} miles\n")

    while True:
        user_input = input(
            "Enter a time (e.g. '8:35 AM', '12:03 PM', '1:12 PM') "
            "or 'all' for final status, or 'q' to quit: "
        ).strip()
        if user_input.lower() in ("q", "quit", "exit"):
            break

        if user_input.lower() == "all":
            # Print final delivered status of every package.
            for pid in range(1, 41):
                pkg = hash_table.lookup(pid)
                if pkg:
                    print(
                        f"Package {pid:2d}: {pkg.status:<25} "
                        f"(Truck {pkg.truck_id}, {pkg.address})"
                    )
            print(f"\nTotal mileage: {total_miles:.1f} miles")
            continue

        # Parse query time.
        try:
            query_time = _time_to_float(user_input)
        except (ValueError, IndexError):
            print("Invalid time format. Use '8:35 AM' or '12:03 PM'.")
            continue

        # Display each package's status at query_time.
        print(f"\nStatus at {user_input}:\n")
        for pid in range(1, 41):
            pkg = hash_table.lookup(pid)
            if not pkg:
                continue

            # Determine status at query_time by evaluating constraints in order:
            #   1. Delayed by flight (until 9:05 a.m.)
            #   2. Delayed by wrong address (package #9 until 10:20 a.m.)
            #   3. At hub (truck not yet departed)
            #   4. Delivered (already dropped off)
            #   5. En route (on truck, driving)
            truck = trucks[pkg.truck_id - 1] if pkg.truck_id else None
            notes = (pkg.special_notes or "").lower()

            if (
                "delayed" in notes
                and "9:05" in notes
                and query_time < (9.0 + 5.0 / 60.0)
                or pkg.package_id == 9
                and query_time < (10.0 + 20.0 / 60.0)
            ):
                status = "delayed"
            elif (
                truck is None
                or truck.departure_time is None
                or query_time < truck.departure_time
            ):
                status = "at hub"
            elif pkg.delivery_time and query_time >= pkg.delivery_time:
                status = pkg.status  # already contains "delivered at ..."
            else:
                status = "en route"

            print(
                f"Package {pid:2d}: {status:<30} "
                f"(Truck {pkg.truck_id}, Deadline: {pkg.deadline})"
            )
        print()


if __name__ == "__main__":
    main()
