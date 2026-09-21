"""
Route planner implementing a Clarke-Wright savings heuristic with 2-opt
local search.

Process:
  1. Packages are pre-filtered into constraint pools (truck-2-only,
     flight-delayed, wrong-address, grouped, and regular).
  2. Each pool is manually assigned to Trucks 1, 2, or 3 so that hard
     constraints are respected (capacity ≤ 16, two-driver limit).
  3. For each truck, a Clarke-Wright savings route is built by starting
     with every package as its own round-trip and greedily merging pairs
     that yield the highest mileage reduction.
  4. Each constructed route is polished with 2-opt to remove edge
     crossings and shorten the total distance.

Flow:
  build_routes -> constraint filtering -> truck assignment
               -> _build_route_for_truck -> two_opt
               -> return Truck list with .packages and .route set.
"""

import re

from truck import Truck


def two_opt(route, distance_table):
    """
    Polish a single route by removing edge crossings.

    Iteratively examine pairs of edges; if reconnecting them the other way
    shortens the distance, reverse the segment between them.
    """
    route = list(route)  # work on a copy
    improved = True
    while improved:
        improved = False
        for i in range(len(route) - 2):
            for j in range(i + 2, len(route) - 1):
                d_before = distance_table.get_distance(
                    route[i], route[i + 1]
                ) + distance_table.get_distance(route[j], route[j + 1])
                d_after = distance_table.get_distance(
                    route[i], route[j]
                ) + distance_table.get_distance(route[i + 1], route[j + 1])
                if d_after < d_before - 1e-9:
                    route[i + 1 : j + 1] = reversed(route[i + 1 : j + 1])
                    improved = True
    return route


def _savings_list(packages, distance_table, hub_address):
    """
    Compute savings for every unordered pair of packages.

    s = dist(hub,a) + dist(hub,b) - dist(a,b)

    Returns a list of (savings, pkg_a, pkg_b) tuples sorted descending.
    """
    savings = []
    for i in range(len(packages)):
        for j in range(i + 1, len(packages)):
            a = packages[i].address
            b = packages[j].address
            s = (
                distance_table.get_distance(hub_address, a)
                + distance_table.get_distance(hub_address, b)
                - distance_table.get_distance(a, b)
            )
            savings.append((s, packages[i], packages[j]))
    savings.sort(key=lambda x: x[0], reverse=True)
    return savings


def build_route_for_truck(pool, distance_table, hub_address, capacity=16):
    """
    Greedy savings construction for a single truck pool.

    1. Start with each package as its own route (hub -> pkg -> hub).
    2. Merge routes in descending savings order while respecting capacity.
    3. Return the best route found (list of addresses without hub bookends).
    """
    if not pool:
        return []

    # Phase 1: each package is its own route
    routes = []
    pkg_to_route = {}
    for pkg in pool:
        route = [hub_address, pkg.address, hub_address]
        routes.append(route)
        pkg_to_route[pkg] = route

    # Phase 2: compute savings
    savings = _savings_list(pool, distance_table, hub_address)

    # Phase 3: merge routes
    def _is_endpoint(route, address):
        """
        Return whether *address* is at either end of the inner route
        (the addresses between the two hub endpoints).
        """
        inner = route[1:-1]
        if not inner:
            return False
        return address == inner[0] or address == inner[-1]

    def _remove_hub(route):
        """Return the list of stop addresses between the two hub endpoints."""
        return route[1:-1]

    def _merge(route_a, route_b, addr_a, addr_b):
        """
        Merge two routes by connecting them at the specified endpoints.
        Both routes currently start and end at hub.
        """
        stops_a = _remove_hub(route_a)
        stops_b = _remove_hub(route_b)

        # Orient so addr_a is at the tail of stops_a
        if stops_a[0] == addr_a:
            stops_a = list(reversed(stops_a))
        # Orient so addr_b is at the head of stops_b
        if stops_b[-1] == addr_b:
            stops_b = list(reversed(stops_b))

        merged_stops = stops_a + stops_b
        return [hub_address] + merged_stops + [hub_address]

    for s, pkg_a, pkg_b in savings:
        route_a = pkg_to_route.get(pkg_a)
        route_b = pkg_to_route.get(pkg_b)
        if route_a is None or route_b is None or route_a is route_b:
            continue

        addr_a = pkg_a.address
        addr_b = pkg_b.address

        if not (_is_endpoint(route_a, addr_a) and _is_endpoint(route_b, addr_b)):
            continue

        merged_len = len(_remove_hub(route_a)) + len(_remove_hub(route_b))
        if merged_len > capacity:
            continue

        merged = _merge(route_a, route_b, addr_a, addr_b)
        routes.remove(route_a)
        routes.remove(route_b)
        routes.append(merged)

        for pkg in pool:
            if pkg_to_route.get(pkg) is route_a or pkg_to_route.get(pkg) is route_b:
                pkg_to_route[pkg] = merged

    # Pick the longest route (most packages)
    best = max(routes, key=lambda r: len(_remove_hub(r)))
    return _remove_hub(best)


def build_routes(packages, distance_table, hub_address):
    """
    Partition packages among three trucks respecting hard constraints,
    then build and polish a route for each truck.

    Returns a list of Truck objects with their .packages lists populated
    and an optimized delivery order stored in .route (a list of addresses).
    """
    # Parse constraints from special notes
    truck2_only = []
    delayed = []  # packages that cannot leave before 9:05 a.m.
    wrong_address = []  # package #9
    grouped = []
    grouped_ids = set()
    regular = []

    for pkg in packages:
        notes = (pkg.special_notes or "").lower()
        if "truck 2" in notes:
            truck2_only.append(pkg)
        elif "delayed" in notes and "9:05" in notes:
            delayed.append(pkg)
        elif pkg.package_id == 9 or "wrong address" in notes:
            wrong_address.append(pkg)
        elif "must be delivered with" in notes:
            # Grouped packages should travel together; collect IDs for grouping
            grouped.append(pkg)
            grouped_ids.add(pkg.package_id)
            ids = re.findall(r"(\d+)", notes)
            for mid in ids:
                grouped_ids.add(int(mid))
        else:
            regular.append(pkg)

    # Resolve grouped packages: any package whose ID is in grouped_ids joins the group
    still_regular = []
    for pkg in regular:
        if pkg.package_id in grouped_ids:
            grouped.append(pkg)
        else:
            still_regular.append(pkg)
    regular = still_regular

    # ------------------------------------------------------------------
    # Truck assignment (manual pre-allocation to respect constraints)
    # ------------------------------------------------------------------
    # Truck 1 departs 8:00 a.m. – handles early-deadline regular packages.
    # Truck 2 departs 8:00 a.m. (or 9:05 if delayed) – truck-2-only + delayed.
    # Truck 3 departs when a driver returns (~10:30 a.m.) – remaining packages
    #            and package #9 (after address correction at 10:20).
    # ------------------------------------------------------------------

    truck1 = Truck(1, hub_address=hub_address)
    truck2 = Truck(2, hub_address=hub_address)
    truck3 = Truck(3, hub_address=hub_address)

    # Truck 1: regular packages with early deadlines (9:00 a.m., 10:30 a.m.)
    early = []
    later = []
    for pkg in regular:
        dl = (pkg.deadline or "").lower()
        if "9:00" in dl or "10:30" in dl:
            early.append(pkg)
        else:
            later.append(pkg)

    # Fill truck 1 with early-deadline packages up to capacity
    truck1.packages = early[: truck1.capacity]
    leftover_regular = early[truck1.capacity :] + later

    # Truck 2: forced truck-2-only packages + delayed packages + filler
    truck2.packages = truck2_only[: truck2.capacity]
    slots_left = truck2.capacity - len(truck2.packages)
    truck2.packages += delayed[:slots_left]
    slots_left = truck2.capacity - len(truck2.packages)
    # Fill remaining slots with leftover regular packages
    truck2.packages += leftover_regular[:slots_left]
    leftover_regular = leftover_regular[slots_left:]

    # Grouped packages should travel together on the same truck.
    if grouped:
        if len(truck1.packages) + len(grouped) <= truck1.capacity:
            truck1.packages += grouped
        elif len(truck3.packages) + len(grouped) <= truck3.capacity:
            truck3.packages += grouped
        else:
            truck2.packages += grouped[: truck2.capacity - len(truck2.packages)]

    # Truck 3: everything else + package #9
    truck3.packages = leftover_regular + wrong_address
    truck3.packages = truck3.packages[: truck3.capacity]

    trucks = [truck1, truck2, truck3]

    # Build and optimize a route for each truck
    for truck in trucks:
        if truck.packages:
            route = build_route_for_truck(
                truck.packages, distance_table, hub_address, truck.capacity
            )
            # Polish with 2-opt
            route = two_opt([hub_address] + route + [hub_address], distance_table)
            # Store the inner route (without hub bookends) for the simulator
            truck.route = route[1:-1]
        else:
            truck.route = []

    return trucks
