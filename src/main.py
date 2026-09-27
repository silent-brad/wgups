# Student ID: 012009094
"""WGUPS Routing Program

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
  6. At 10:20 a.m., correct the wrong-address package and rebuild Truck 3's route.
  7. Set departure times (Trucks 1 & 2 at 8:00, Truck 3 at ~10:30).
  8. Simulate deliveries: drive each truck, accumulate mileage, record
     delivery timestamps back into the HashTable.
  9. Enter a CLI loop where the user queries status at any time.

Program flow:
  main() -> _load_distance_table -> _load_packages -> HashTable.insert
         -> build_routes -> correct wrong-address pkg -> rebuild truck 3 route
         -> Truck.depart -> simulate_deliveries -> interactive query loop
"""

import argparse
import csv
import json
import os

from delivery_simulator import simulate_deliveries
from distance_table import DistanceTable
from hash_table import HashTable
from package import Package
from route_planner import (
    TRUCK1_DEPARTURE,
    TRUCK2_DEPARTURE,
    TRUCK3_DEPARTURE,
    build_route_for_truck,
    build_routes,
    two_opt,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# ANSI color helpers for the CLI.
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _status_color(status):
    """Return an ANSI color code based on package status text."""
    if status.startswith("delivered"):
        return GREEN
    if status == "en route":
        return YELLOW
    if status == "delayed":
        return RED
    if status == "at hub":
        return BLUE
    return ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _time_to_float(time_str):
    """Convert '8:00 AM' or '10:30 AM' to a float hour value."""
    time_str = time_str.strip().upper()
    if time_str == "EOD":
        return 17.0  # 5:00 p.m.
    h_m, ampm = time_str.split()
    h, m = map(int, h_m.split(":"))
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
    Returns a (DistanceTable, hub_address) tuple.
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

    return DistanceTable(addresses, matrix), hub_address


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


def _format_time(hours_float):
    """Convert a floating-point hour value (e.g. 8.5) to '8:30 AM'."""
    total_minutes = round(hours_float * 60)
    h = total_minutes // 60
    m = total_minutes % 60
    ampm = "AM" if h < 12 else "PM"
    display_h = h if h <= 12 else h - 12
    if display_h == 0:
        display_h = 12
    return f"{display_h}:{m:02d} {ampm}"


def _format_truck_status(truck, query_time):
    """Return a short status string for a truck at a given query time."""
    if truck.departure_time is None or query_time < truck.departure_time:
        return "at hub"
    # Truck has departed. Determine if all packages are delivered.
    all_delivered = all(
        pkg.delivery_time is not None and query_time >= pkg.delivery_time
        for pkg in truck.packages
    )
    if all_delivered and truck.packages:
        return f"returned to hub at {_format_time(truck.current_time)}"
    return f"en route (departed {_format_time(truck.departure_time)})"


def _print_status_table(
    trucks, packages, hash_table, query_time=None, total_miles=None
):
    """Print a grouped, aligned status table.

    If *query_time* is None, this is the final 'all' view.
    """
    # Group packages by truck.
    truck_packages = {t.truck_id: [] for t in trucks}
    unassigned = []
    for pkg in packages:
        if pkg.truck_id is not None:
            truck_packages[pkg.truck_id].append(pkg)
        else:
            unassigned.append(pkg)

    # Per-truck summary counts for overall tally.
    overall = {"delivered": 0, "en route": 0, "at hub": 0, "delayed": 0}

    for truck in trucks:
        pkgs = truck_packages.get(truck.truck_id, [])
        if not pkgs:
            continue

        # Truck header line.
        if query_time is None:
            print(
                f"\n{BOLD}Truck {truck.truck_id}{RESET}  "
                f"{len(pkgs)} packages  "
                f"{truck.mileage:.1f} miles  "
                f"departed {_format_time(truck.departure_time)}"
            )
        else:
            status = _format_truck_status(truck, query_time)
            print(
                f"\n{BOLD}Truck {truck.truck_id}{RESET}  {len(pkgs)} packages  ({status})"
            )
        print("-" * 90)

        # Print each package in this truck.
        for pkg in sorted(pkgs, key=lambda p: p.package_id):
            if query_time is None:
                status = pkg.status
            else:
                notes = (pkg.special_notes or "").lower()
                if (
                    "delayed" in notes
                    and "9:05" in notes
                    and query_time < TRUCK2_DEPARTURE
                    or pkg.package_id == wrong_pkg_id
                    and query_time < (10.0 + 20.0 / 60.0)
                ):
                    status = "delayed"
                elif truck.departure_time is None or query_time < truck.departure_time:
                    status = "at hub"
                elif pkg.delivery_time and query_time >= pkg.delivery_time:
                    status = pkg.status
                else:
                    status = "en route"

            color = _status_color(status)
            # Canonicalize status for the summary count.
            if status.startswith("delivered"):
                summary_key = "delivered"
            else:
                summary_key = status
            overall[summary_key] = overall.get(summary_key, 0) + 1
            deadline = pkg.deadline or "EOD"
            # Before 10:20 a.m. the wrong-address package still shows
            # the original (incorrect) address; afterwards the corrected one.
            if (
                pkg.package_id == wrong_pkg_id
                and pkg.original_address is not None
                and query_time is not None
                and query_time < (10.0 + 20.0 / 60.0)
            ):
                display_address = pkg.original_address
            else:
                display_address = pkg.address
            print(
                f"  Package {pkg.package_id:2d}  "
                f"{color}{status:<25}{RESET}  "
                f"Deadline: {deadline:<12}  "
                f"{display_address}"
            )

    if unassigned:
        print(f"\n{BOLD}Unassigned{RESET}")
        print("-" * 90)
        for pkg in sorted(unassigned, key=lambda p: p.package_id):
            print(f"  Package {pkg.package_id:2d}  (not assigned to any truck)")

    # Overall summary.
    print(f"\n{BOLD}Summary{RESET}")
    print("-" * 90)
    for label, count in overall.items():
        if count:
            print(f"  {label}: {count}")
    if total_miles is not None:
        print(f"  Total mileage: {total_miles:.1f} miles")
    print()


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="WGUPS Routing Program")
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Directory containing the distance table, package file, and config.json",
    )
    args = parser.parse_args()

    # Resolve data directory.
    if args.data_dir:
        base_dir = os.path.abspath(args.data_dir)
    else:
        _src_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.basename(_src_dir) == "__pycache__":
            _src_dir = os.path.dirname(_src_dir)
        base_dir = os.path.normpath(os.path.join(_src_dir, "..", "data"))

    dist_path = os.path.join(base_dir, "WGUPS Distance Table.csv")
    pkg_path = os.path.join(base_dir, "WGUPS Package File.csv")
    config_path = os.path.join(base_dir, "config.json")

    # 1. Load city-specific configuration.
    if os.path.isfile(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
    else:
        config = {}

    global wrong_pkg_id
    wrong_address_cfg = config.get("wrong_address", {})
    wrong_pkg_id = wrong_address_cfg.get("package_id", 9)
    corrected_address = wrong_address_cfg.get("corrected_address", "")
    corrected_zip = wrong_address_cfg.get("corrected_zip", "")

    # 2. Load distance table and derive hub address.
    distance_table, hub_address = _load_distance_table(dist_path)

    # 3. Load packages and insert into the custom hash table.
    packages = _load_packages(pkg_path)
    if not packages:
        print("No packages loaded. Exiting.")
        return

    hash_table = HashTable(initial_capacity=max(64, len(packages) * 2))
    for pkg in packages:
        hash_table.insert(pkg.package_id, pkg)

    # 4. Apply initial status constraints.
    #    Packages delayed by a late flight are "delayed" until 9:05 a.m.
    #    The wrong-address package is "delayed" until its address is corrected.
    for pkg in packages:
        notes = (pkg.special_notes or "").lower()
        if ("delayed" in notes and "9:05" in notes) or pkg.package_id == wrong_pkg_id:
            pkg.status = "delayed"
            hash_table.insert(pkg.package_id, pkg)

    # 5. Plan routes: assign packages to trucks and optimize stop order.
    trucks = build_routes(packages, distance_table, hub_address)

    # Record which truck each package belongs to.
    for truck in trucks:
        for pkg in truck.packages:
            pkg.truck_id = truck.truck_id
            hash_table.insert(pkg.package_id, pkg)

    # 6. Set departure times respecting the two-driver limit and constraints.
    #    Truck 1 departs at 8:00 a.m.
    trucks[0].depart(TRUCK1_DEPARTURE)
    #    Truck 2 departs at 8:00 a.m. unless it carries packages delayed until 9:05.
    truck2_depart = TRUCK1_DEPARTURE
    for pkg in trucks[1].packages:
        notes = (pkg.special_notes or "").lower()
        if "delayed" in notes and "9:05" in notes:
            truck2_depart = TRUCK2_DEPARTURE
            break
    trucks[1].depart(truck2_depart)

    # 6a. Address correction for the wrong-address package at 10:20 a.m.
    #     The original CSV listed an incorrect address.
    #     At 10:20 a.m. WGUPS receives the correct address. Because
    #     Truck 3 does not depart until 10:30 a.m., the route is rebuilt
    #     now so the truck drives to the corrected destination.
    wrong_pkg = hash_table.lookup(wrong_pkg_id)
    if wrong_pkg and corrected_address and len(trucks) > 2:
        # Preserve the original address so it can be displayed for
        # status queries made before the 10:20 a.m. correction.
        wrong_pkg.original_address = wrong_pkg.address
        wrong_pkg.original_zip_code = wrong_pkg.zip_code
        wrong_pkg.address = corrected_address
        wrong_pkg.zip_code = corrected_zip
        hash_table.insert(wrong_pkg_id, wrong_pkg)
        trucks[2].route = build_route_for_truck(
            trucks[2].packages, distance_table, hub_address, trucks[2].capacity
        )
        trucks[2].route = two_opt(
            [hub_address] + trucks[2].route + [hub_address], distance_table
        )[1:-1]

    #    Truck 3 departs when a driver returns (~10:30 a.m.).
    if len(trucks) > 2:
        trucks[2].depart(TRUCK3_DEPARTURE)

    # 7. Run the delivery simulation.
    total_miles = simulate_deliveries(trucks, distance_table, hash_table, hub_address)

    # 8. CLI for status queries.
    print(BOLD + "=" * 60 + RESET)
    print(BOLD + "WGUPS Routing Program" + RESET)
    print(BOLD + "=" * 60 + RESET)
    print(f"Total mileage for all trucks: {total_miles:.1f} miles\n")

    while True:
        user_input = input(
            "Enter a time (e.g. '8:35 AM', '12:03 PM', '1:12 PM') "
            "or 'all' for final status, or 'q' to quit: "
        ).strip()
        if user_input.lower() in ("q", "quit", "exit"):
            break

        if user_input.lower() == "all":
            _print_status_table(trucks, packages, hash_table, total_miles=total_miles)
            continue

        # Parse query time.
        try:
            query_time = _time_to_float(user_input)
        except (ValueError, IndexError):
            print("Invalid time format. Use '8:35 AM' or '12:03 PM'.")
            continue

        print(f"\n{BOLD}Status at {user_input}{RESET}\n")
        _print_status_table(trucks, packages, hash_table, query_time=query_time)


if __name__ == "__main__":
    main()
