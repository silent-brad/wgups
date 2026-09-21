"""
Delivery simulator.

Drives each truck along its optimized route, updates mileage and elapsed time,
and records delivery status (with timestamp) back into the hash table.

Process:
  For each truck that has a route, the simulator starts at the hub,
  drives to every stop in order, and returns to the hub.  After each
  stop the package(s) destined for that address are marked delivered.

Flow:
  simulate_deliveries iterates over the truck list.
    -> depart: mark every loaded package "en route".
    -> drive_to: move to next stop, update time and mileage.
    -> deliver: update package status and hash table entry.
    -> return_to_hub: add return-leg mileage.
"""


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


def simulate_deliveries(trucks, distance_table, hash_table, hub_address):
    """
    Simulate all truck deliveries.

    Parameters
    ----------
    trucks : list[Truck]
        Trucks already loaded with .packages and .route (ordered addresses).
    distance_table : DistanceTable
        Symmetric distance lookup.
    hash_table : HashTable
        Shared package store; statuses are updated in-place.
    hub_address : str
        The hub location string used by the distance table.

    Returns
    -------
    float
        Combined total mileage for all trucks.
    """
    total_miles = 0.0

    for truck in trucks:
        if not truck.packages or not truck.route:
            continue

        # Ensure the truck is on the road.
        if truck.current_time is None:
            continue  # truck never departed

        # When the truck leaves the hub, every package loaded on it
        # transitions from "delayed" / "at hub" to "en route".
        for pkg in truck.packages:
            if pkg.status in ("delayed", "at hub"):
                pkg.status = "en route"
                hash_table.insert(pkg.package_id, pkg)

        current_location = hub_address

        # Drive to each stop in the optimized route.
        for address in truck.route:
            distance = distance_table.get_distance(current_location, address)
            truck.mileage += distance
            truck.current_time += distance / truck.speed
            total_miles += distance
            current_location = address

            # Find the package(s) destined for this address and mark delivered.
            for pkg in truck.packages:
                if pkg.address == address:
                    pkg.status = f"delivered at {_format_time(truck.current_time)}"
                    pkg.delivery_time = truck.current_time
                    hash_table.insert(pkg.package_id, pkg)

        # Return to hub after the last delivery.
        return_distance = distance_table.get_distance(current_location, hub_address)
        truck.mileage += return_distance
        truck.current_time += return_distance / truck.speed
        total_miles += return_distance

    return total_miles
