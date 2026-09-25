"""
Route planner using constraint-aware deadline-first assignment and
Clarke-Wright savings construction polished by 2-opt.

Strategy:
  1. Parse hard constraints from each package's special_notes field.
  2. Deadline-first pass:
       9:00   → T1 only
       10:30  → T1 preferred, T2 if T1 is full, never T3
       EOD    → any truck via greedy marginal cost
  3. Simulate routes and fix any missed deadlines by moving late
     packages to earlier-departing trucks (swapping EOD packages back).
  4. Cost-optimising local search: try moving EOD packages between
     trucks to reduce total closed-loop mileage while keeping all
     deadlines valid.  After each accepted move the search restarts
     so the package lists stay consistent.
  5. Build routes with Clarke-Wright savings + 2-opt.
"""

import re

from truck import Truck

# ---------------------------------------------------------------------------
# Scenario constants (not present in the CSV files; defined by the rubric)
# ---------------------------------------------------------------------------

# Truck departure times in hours.
TRUCK1_DEPARTURE = 8.0  # 8:00 a.m.
TRUCK2_DEPARTURE = 9.0 + 5.0 / 60.0  # 9:05 a.m. (if carrying delayed packages)
TRUCK3_DEPARTURE = 10.5  # 10:30 a.m.

# Keyword patterns that appear in the Package CSV's special_notes column.
TRUCK2_KEYWORD = "truck 2"
DELAYED_KEYWORD = "delayed"
DELAYED_TIME_KEYWORD = "9:05"
WRONG_ADDRESS_KEYWORD = "wrong address"
GROUPED_KEYWORD = "must be delivered with"


def two_opt(route, distance_table):
    """Polish a single route by removing edge crossings."""
    route = list(route)
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


def _savings_list(stops, distance_table, hub_address):
    """Return savings for every unordered pair of stops."""
    savings = []
    n = len(stops)
    for i in range(n):
        for j in range(i + 1, n):
            a = stops[i]
            b = stops[j]
            s = (
                distance_table.get_distance(hub_address, a)
                + distance_table.get_distance(hub_address, b)
                - distance_table.get_distance(a, b)
            )
            savings.append((s, a, b))
    savings.sort(key=lambda x: x[0], reverse=True)
    return savings


def build_route_for_truck(pool, distance_table, hub_address, capacity=16):
    """
    Build a single route through every stop in *pool* using the
    Clarke-Wright savings heuristic polished by 2-opt.

    The heuristic operates on *unique addresses* so duplicated stops
    (multiple packages at the same address) do not inflate mileage.
    All bookkeeping is done with plain lists.
    """
    if not pool:
        return []

    # Group packages by address using plain lists.
    stop_addrs = []
    stop_counts = []
    for pkg in pool:
        found = False
        for idx, addr in enumerate(stop_addrs):
            if addr == pkg.address:
                stop_counts[idx] += 1
                found = True
                break
        if not found:
            stop_addrs.append(pkg.address)
            stop_counts.append(1)

    if len(stop_addrs) == 1:
        return stop_addrs

    # Pairwise savings.
    savings = _savings_list(stop_addrs, distance_table, hub_address)

    # Every stop starts as its own route: [hub, stop, hub].
    routes = []
    counts = []
    for i, addr in enumerate(stop_addrs):
        routes.append([hub_address, addr, hub_address])
        counts.append(stop_counts[i])

    def _inner(route):
        return route[1:-1]

    for _s, a, b in savings:
        route_a_idx = None
        route_b_idx = None
        for idx, r in enumerate(routes):
            if r is None:
                continue
            inner = _inner(r)
            if not inner:
                continue
            if inner[0] == a or inner[-1] == a:
                route_a_idx = idx
            if inner[0] == b or inner[-1] == b:
                route_b_idx = idx
            if route_a_idx is not None and route_b_idx is not None:
                break

        if route_a_idx is None or route_b_idx is None:
            continue
        if route_a_idx == route_b_idx:
            continue

        if counts[route_a_idx] + counts[route_b_idx] > capacity:
            continue

        route_a = routes[route_a_idx]
        route_b = routes[route_b_idx]
        inner_a = _inner(route_a)
        inner_b = _inner(route_b)

        if not (inner_a[0] == a or inner_a[-1] == a):
            continue
        if not (inner_b[0] == b or inner_b[-1] == b):
            continue

        if len(inner_a) > 1 and inner_a[-1] != a:
            inner_a = list(reversed(inner_a))
        if len(inner_b) > 1 and inner_b[0] != b:
            inner_b = list(reversed(inner_b))

        merged = [hub_address] + inner_a + inner_b + [hub_address]

        counts[route_a_idx] += counts[route_b_idx]
        routes[route_a_idx] = merged
        routes[route_b_idx] = None

    best_route = None
    best_len = 0
    for r in routes:
        if r is not None:
            inner_len = len(_inner(r))
            if inner_len > best_len:
                best_len = inner_len
                best_route = r

    route = _inner(best_route) if best_route else []
    route = two_opt([hub_address] + route + [hub_address], distance_table)
    return route[1:-1]


def _route_cost(pool, hub_address, distance_table):
    """Closed-loop cost of the best route through *pool*."""
    route = build_route_for_truck(pool, distance_table, hub_address)
    d = 0.0
    loc = hub_address
    for a in route:
        d += distance_table.get_distance(loc, a)
        loc = a
    d += distance_table.get_distance(loc, hub_address)
    return d


def _simulate_route(pool, hub_address, distance_table, depart_time, speed=18.0):
    """
    Return a dict mapping package_id -> delivery_time for a simulated
    run of *pool* along its optimised route.
    """
    route = build_route_for_truck(pool, distance_table, hub_address)
    addr_to_pids = {}
    for p in pool:
        addr_to_pids.setdefault(p.address, []).append(p.package_id)

    loc = hub_address
    time = depart_time
    delivery_times = {}
    for a in route:
        time += distance_table.get_distance(loc, a) / speed
        for pid in addr_to_pids.get(a, []):
            delivery_times[pid] = time
        loc = a
    return delivery_times


def _dl_hours(pkg):
    """Return the deadline as a float hour value."""
    dl = (pkg.deadline or "").strip()
    if dl == "EOD" or not dl:
        return 17.0
    h, m, _ = dl.split(":")
    return int(h) + int(m) / 60.0


def _find_violation(trucks, hub_address, distance_table, departures):
    """Return (pkg, truck_idx) of the first deadline violation, or None."""
    for t_idx, truck in enumerate(trucks):
        dtimes = _simulate_route(
            truck.packages, hub_address, distance_table, departures[t_idx]
        )
        for pkg in truck.packages:
            actual = dtimes.get(pkg.package_id, 0.0)
            if actual > _dl_hours(pkg) + 1e-6:
                return pkg, t_idx
    return None


def _total_cost(trucks, hub_address, distance_table):
    """Sum of closed-loop route costs for all trucks."""
    return sum(_route_cost(t.packages, hub_address, distance_table) for t in trucks)


def _can_move(pkg, target, trucks, forced_t2, wrong, grouped, delayed):
    """Quick constraint check: can *pkg* be placed on truck *target*?"""
    if len(trucks[target].packages) >= 16:
        return False
    pid = pkg.package_id
    if pid in forced_t2 and target != 1:
        return False
    if pid in wrong and target != 2:
        return False
    if pid in grouped and target != 0:
        return False
    if pid in delayed and target == 0:
        return False
    dl = _dl_hours(pkg)
    if dl == 9.0 and target != 0:
        return False
    return not (dl == 10.5 and target == 2)


def _is_eod_and_unconstrained(pkg, forced_t2, wrong, grouped, delayed):
    """True if *pkg* has an EOD deadline and no hard truck constraint."""
    pid = pkg.package_id
    if pid in forced_t2 or pid in wrong or pid in grouped:
        return False
    if pid in delayed:
        return False
    return _dl_hours(pkg) == 17.0


def _try_move_eod(
    trucks,
    hub_address,
    distance_table,
    departures,
    current_total,
    forced_t2,
    wrong,
    grouped,
    delayed,
):
    """
    Try every single EOD-package move between trucks.  If a move lowers
    total cost and keeps all deadlines valid, apply it and return the
    new total.  Otherwise return None.
    """
    for i in range(3):
        for j in range(3):
            if i == j:
                continue
            for p in list(trucks[i].packages):
                if not _is_eod_and_unconstrained(p, forced_t2, wrong, grouped, delayed):
                    continue
                if len(trucks[j].packages) >= 16:
                    continue
                trucks[i].packages.remove(p)
                trucks[j].packages.append(p)
                if (
                    _find_violation(trucks, hub_address, distance_table, departures)
                    is None
                ):
                    new_total = _total_cost(trucks, hub_address, distance_table)
                    if new_total < current_total - 1e-6:
                        return new_total
                trucks[j].packages.remove(p)
                trucks[i].packages.append(p)
    return None


def _try_swap_eod(
    trucks,
    hub_address,
    distance_table,
    departures,
    current_total,
    forced_t2,
    wrong,
    grouped,
    delayed,
):
    """
    Try every pairwise EOD-package swap between two trucks.  If a swap
    lowers total cost and keeps deadlines valid, apply it and return the
    new total.  Otherwise return None.
    """
    for i in range(3):
        for j in range(i + 1, 3):
            for p in list(trucks[i].packages):
                if not _is_eod_and_unconstrained(p, forced_t2, wrong, grouped, delayed):
                    continue
                for q in list(trucks[j].packages):
                    if not _is_eod_and_unconstrained(
                        q, forced_t2, wrong, grouped, delayed
                    ):
                        continue
                    trucks[i].packages.remove(p)
                    trucks[i].packages.append(q)
                    trucks[j].packages.remove(q)
                    trucks[j].packages.append(p)
                    if (
                        _find_violation(trucks, hub_address, distance_table, departures)
                        is None
                    ):
                        new_total = _total_cost(trucks, hub_address, distance_table)
                        if new_total < current_total - 1e-6:
                            return new_total
                    trucks[i].packages.remove(q)
                    trucks[i].packages.append(p)
                    trucks[j].packages.remove(p)
                    trucks[j].packages.append(q)
    return None


def build_routes(packages, distance_table, hub_address):
    """
    Build truck routes using constraint-aware deadline-first assignment
    + CW/2-opt.  After the initial assignment routes are simulated;
    missed deadlines are repaired, then an EOD-only local search tries
    to lower total mileage while never breaking a deadline.

    Hard constraints (truck-2-only, delayed, grouped, wrong-address) are
    inferred by scanning each package's special_notes field.
    """
    forced_t2 = set()
    delayed = set()
    wrong = set()
    grouped_ids = set()

    for pkg in packages:
        notes = (pkg.special_notes or "").lower()
        pid = pkg.package_id
        if TRUCK2_KEYWORD in notes:
            forced_t2.add(pid)
        elif DELAYED_KEYWORD in notes and DELAYED_TIME_KEYWORD in notes:
            delayed.add(pid)
        elif pid == 9 or WRONG_ADDRESS_KEYWORD in notes:
            wrong.add(pid)
        elif GROUPED_KEYWORD in notes:
            grouped_ids.add(pid)
            for mid in re.findall(r"(\d+)", notes):
                grouped_ids.add(int(mid))

    grouped = grouped_ids

    trucks = [
        Truck(1, hub_address=hub_address),
        Truck(2, hub_address=hub_address),
        Truck(3, hub_address=hub_address),
    ]

    # 1. Mandatory assignments
    for p in packages:
        pid = p.package_id
        if pid in forced_t2 or pid in delayed:
            trucks[1].packages.append(p)
        elif pid in wrong:
            trucks[2].packages.append(p)
        elif pid in grouped:
            trucks[0].packages.append(p)

    assigned = {p.package_id for t in trucks for p in t.packages}
    remaining = [p for p in packages if p.package_id not in assigned]

    departures = {
        0: TRUCK1_DEPARTURE,
        1: TRUCK2_DEPARTURE,
        2: TRUCK3_DEPARTURE,
    }

    # 2. Deadline-first greedy assignment
    remaining.sort(key=lambda p: (_dl_hours(p), p.package_id))

    for pkg in remaining:
        dl = _dl_hours(pkg)
        feasible = []
        for i, truck in enumerate(trucks):
            if len(truck.packages) >= 16:
                continue
            if pkg.package_id in delayed and i == 0:
                continue
            if dl == 9.0 and i != 0:
                # 9:00 AM deadlines can only be served by Truck 1 (departs 8:00).
                continue
            if dl == 10.5 and i == 2:
                # 10:30 AM deadlines cannot be served by Truck 3 (departs 10:30).
                continue
            feasible.append(i)

        if not feasible:
            for i, truck in enumerate(trucks):
                if len(truck.packages) < 16:
                    feasible.append(i)
                    break

        best = None
        best_cost = float("inf")
        for i in feasible:
            base = _route_cost(trucks[i].packages, hub_address, distance_table)
            cand = _route_cost(trucks[i].packages + [pkg], hub_address, distance_table)
            marginal = cand - base
            if marginal < best_cost:
                best_cost = marginal
                best = i

        if best is None:
            best = 0
        trucks[best].packages.append(pkg)

    # 3. Repair deadline violations
    for _ in range(50):
        viol = _find_violation(trucks, hub_address, distance_table, departures)
        if viol is None:
            break
        late_pkg, late_truck = viol
        moved = False
        for target in range(late_truck):
            if not _can_move(
                late_pkg, target, trucks, forced_t2, wrong, grouped, delayed
            ):
                continue
            swap_idx = None
            for j, sp in enumerate(trucks[target].packages):
                if _is_eod_and_unconstrained(sp, forced_t2, wrong, grouped, delayed):
                    swap_idx = j
                    break
            if swap_idx is not None:
                sp = trucks[target].packages.pop(swap_idx)
                trucks[late_truck].packages.remove(late_pkg)
                trucks[target].packages.append(late_pkg)
                trucks[late_truck].packages.append(sp)
                moved = True
                break
            elif len(trucks[target].packages) < 16:
                trucks[late_truck].packages.remove(late_pkg)
                trucks[target].packages.append(late_pkg)
                moved = True
                break
        if not moved:
            break

    # 4. EOD-only local search (restart from scratch after each accepted move)
    best_total = _total_cost(trucks, hub_address, distance_table)
    improved = True
    while improved:
        improved = False
        new_total = _try_move_eod(
            trucks,
            hub_address,
            distance_table,
            departures,
            best_total,
            forced_t2,
            wrong,
            grouped,
            delayed,
        )
        if new_total is not None:
            best_total = new_total
            improved = True
            continue
        new_total = _try_swap_eod(
            trucks,
            hub_address,
            distance_table,
            departures,
            best_total,
            forced_t2,
            wrong,
            grouped,
            delayed,
        )
        if new_total is not None:
            best_total = new_total
            improved = True
            continue

    # 5. Build optimised routes
    for truck in trucks:
        if truck.packages:
            truck.route = build_route_for_truck(
                truck.packages, distance_table, hub_address, truck.capacity
            )

    return trucks
