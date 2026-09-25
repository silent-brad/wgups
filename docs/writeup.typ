#set document(title: "WGUPS Routing Program: Algorithm and Data Structure Justification")
#set page(paper: "us-letter", margin: 1in)
#set text(size: 11pt)
#set par(justify: true, leading: 0.65em)

#align(center)[
  #text(size: 18pt, weight: "bold")[WGUPS Routing Program]
  #linebreak()
  #text(size: 14pt)[Algorithm and Data Structure Justification]
  #linebreak()
  #v(0.5em)
  Student: bwhi880 \
  #datetime.today().display("[month repr:long] [day], [year]")
]

#v(1em)

= Introduction

The Western Governors University Parcel Service (WGUPS) routes an average of forty packages per day through Salt Lake City using three trucks, two drivers, and a hub located at 4001 South 700 East. Each package carries specific constraints, including delivery deadlines, truck assignments, delayed flight arrivals, grouped deliveries, and a wrong address corrected mid morning, that make manual routing inefficient and error prone. The program described here automates the entire routing process. It loads package data into a custom chaining hash table, builds optimized delivery routes for each truck using a Clarke-Wright savings heuristic polished by 2-opt local search, simulates the trucks' movement, and presents an intuitive command line interface for supervisors to query any package status at any time of day.

The implementation delivers all forty packages, respects every hard constraint, verifies deadlines through explicit route simulation, and keeps the combined total distance under the 140-mile requirement at 89.3 miles. This paper explains why the deadline-aware Clarke-Wright and 2-opt combination was chosen, how the custom hash table satisfies the storage and lookup requirements, what alternative algorithms and data structures could also meet the scenario's needs, and what modifications would be made on a second iteration.

#image("slc_downtown_map.png", width: 60%)

= Algorithm Design and Justification

== Overview of the Chosen Approach

The routing engine is a three-phase pipeline.

*Phase one* assigns every package to a truck. Hard constraints, such as "Can only be on truck 2," "Delayed on flight," "Must be delivered with," and the wrong-address flag for package #9, are parsed dynamically from each package's `special_notes` rather than hard coded. The remaining packages are inserted greedily: packages with 9:00 a.m. deadlines are forced onto Truck 1 (the only truck departing early enough), 10:30 a.m. deadlines are routed to Trucks 1 or 2, and end-of-day packages are placed on whichever truck causes the smallest increase in closed-loop route cost.

*Phase two* simulates each constructed route to verify that every package is delivered before its deadline. If a package would be late, it is moved to an earlier departing truck and an end-of-day package is swapped back to keep capacity balanced. After all deadlines are satisfied, an end-of-day-only local search tries moving or swapping unconstrained end-of-day packages between trucks to reduce total mileage without breaking any deadline.

*Phase three* builds the actual route for each truck using the *Clarke-Wright savings algorithm*, a self-adjusting heuristic that starts with every delivery address as an independent round trip from the hub and greedily merges the pair whose combined route saves the most mileage ("Vehicle routing problem," n.d.). After construction, *2-opt local search* polishes each route by repeatedly examining pairs of edges; if reconnecting them the other way shortens the distance, the segment between them is reversed ("2-opt," n.d.).

This design was selected because it separates feasibility (deadlines and hard constraints) from optimization (mileage), making it easy to verify that requirements are met before the route is ever driven.

== Strengths of the Algorithm

Two properties make this pipeline well suited to the WGUPS scenario.

First, the deadline-first assignment with explicit route simulation guarantees correctness before optimization. Because the program builds a candidate route, simulates driving it, and checks every delivery time against the package's deadline, there is no risk that a low-mileage route will inadvertently violate a time constraint. If a violation is found, the package is automatically reassigned to an earlier truck. This is a significant advantage over pure construction heuristics that optimize distance without looking at clock time.

Second, the Clarke-Wright savings construction is *self-adjusting*. After each merge, the pool of valid merges shrinks: a pair that was a strong candidate before may now exceed the sixteen-package capacity limit or would force a non-endpoint address into the middle of a route, disqualifying it. The algorithm dynamically adapts to this shrinking search space without re-evaluating every pair from scratch, which keeps the overall run time practical. On commodity hardware the forty-package construction finishes in well under one second.

== Verification Against Scenario Requirements

The combined algorithm satisfies every requirement described in the scenario.

*All forty packages are delivered.* The route planner assigns every package to exactly one truck, and the delivery simulator drives each truck to every stop in its optimized order. No package is orphaned or delivered twice.

*Total distance stays under 140 miles.* The combined mileage for all three trucks is 89.3 miles, a 36 percent margin below the threshold.

*Capacity limits are enforced.* The greedy insertion refuses any truck that already carries sixteen packages, and the Clarke-Wright merge logic rejects any combination that would exceed the same limit.

*Hard constraints are respected.* The program scans every package's `special_notes` at runtime to discover constraints. Packages restricted to Truck 2 are pre-filtered into Truck 2's load. Flight-delayed packages are marked "delayed" until 9:05 a.m.; Truck 2 leaves at 9:05 a.m. so those packages are not delivered early. Packages that must be delivered together are collected into a single pool and placed on the same truck. Package #9 loads with the original incorrect address "300 State St." and is marked "delayed." At 10:20 a.m., the address is corrected to "410 S State St." in the hash table, Truck 3's route is rebuilt with the corrected stop using the same savings construction, and Truck 3 departs at 10:30 a.m.

*The two-driver limit is respected.* Trucks 1 and 2 depart at 8:00 a.m. Truck 3 departs at 10:30 a.m., after the first truck has returned to the hub and freed a driver.

*Deadlines are met.* All packages with "9:00 AM" deadlines and "10:30 AM" deadlines are delivered before their cutoff times, verified by explicit route simulation.

== Alternative Algorithms That Could Also Satisfy the Requirements

Any algorithm that respects capacity limits and produces routes under 140 miles would satisfy the scenario. Two other named approaches that meet these criteria are the *Nearest-Neighbor heuristic* and the *Sweep algorithm* ("Vehicle routing problem," n.d.).

*Nearest Neighbor* differs from Clarke-Wright in construction strategy. Rather than evaluating every address pair globally, it starts at the hub and repeatedly visits the closest unvisited stop until the truck is full, then returns to the hub and repeats. This is a greedy local strategy; each decision depends only on the current location's immediate vicinity. In contrast, Clarke-Wright is a global strategy that evaluates all pairs before committing to any merge. Nearest Neighbor tends to produce longer routes because an early greedy choice can strand a distant package on a late leg, and it lacks the self-adjusting merge logic of Clarke-Wright. Once a package is added to a route it is never reconsidered.

*Sweep* differs in how trucks are partitioned. It places the hub at the origin of a polar coordinate system, sorts every delivery address by angle from the hub, and assigns contiguous angular slices to each truck. Each slice is then routed internally. Sweep is fundamentally a geometric partitioner that exploits spatial clustering, whereas Clarke-Wright is a distance-based merger that ignores angular geometry and instead optimizes for raw mileage reduction. Sweep would produce radial wedge-shaped routes rather than the chain-like routes Clarke-Wright creates, and it may underperform when constraints force non-geographic groupings, such as "truck 2 only" packages located at opposite ends of the delivery area.

= Data Structure Design and Verification

== Overview of the Chosen Data Structure

Package records are stored in a *chaining hash table* implemented entirely with Python lists. No built-in dictionaries, sets, or third-party libraries are used. The table maps each package's unique integer ID to a bucket that contains the full composite record: delivery address, delivery deadline, delivery city, delivery ZIP code, package weight, and delivery status (including the delivery time when applicable).

== How the Hash Table Satisfies Scenario Requirements

Insertion takes the package ID as input and stores the complete record. Lookup takes the same package ID and returns each required field. Both operations run in $O(1)$ average time when the hash function distributes keys uniformly.

Collision resolution uses chaining: each bucket is a list of `(key, value)` tuples. When two keys hash to the same bucket they are appended to the list rather than overwriting each other. This avoids the clustering problems that can plague open-addressing schemes.

The table is also self-adjusting. When the load factor exceeds 0.75, the table allocates a new array twice the size, rehashes every existing key, and redistributes the records into the larger bucket array. This guarantees that insertion and lookup remain efficient even if the package count grows from forty to thousands.

During the delivery simulation, the hash table is updated in place. As each truck reaches a destination, the corresponding package's status is overwritten with a string such as "delivered at 10:14 AM" and the delivery timestamp is recorded in the object. Because the record is retrieved by ID in constant time, the supervisor can query any package at any moment and see the exact status and time.

== Alternative Data Structures That Could Also Satisfy the Requirements

Two other structures could meet the same storage and lookup requirements: a *binary search tree* and an *open-addressing hash table*.

A *binary search tree* stores each record in a tree node keyed by package ID. Lookup is $O(log n)$ in the average case (though $O(n)$ if the tree becomes unbalanced). The BST provides in-order traversal for free, so the supervisor could list all packages sorted by deadline or ZIP code simply by walking the tree. The chaining hash table offers no ordering. However, a BST requires extra memory per node for left and right child pointers plus any rebalancing metadata, and its logarithmic lookup is slower than the hash table's constant-time average. For a delivery monitoring system where the supervisor issues random ID lookups, the hash table's superior retrieval speed is the better fit.

An *open-addressing hash table* stores every record directly in the bucket array and uses probing (linear, quadratic, or double hashing) to find the next empty slot when a collision occurs. This eliminates the pointer overhead of chaining and improves cache locality, which can speed up small-dataset lookups. However, performance degrades sharply as the load factor approaches 1.0, and deletions become complex because removing an entry can break the probe sequence for later lookups. The chaining approach avoids both problems: performance degrades gracefully even under heavy load, and deletions are as simple as removing a node from a list. In the WGUPS program, where status updates are frequent and table growth is unpredictable, the resilience of chaining outweighs the cache benefits of open addressing.

= Implementation Details and Testing

The program is implemented in Python 3.12 and executed through the interpreter detected at build time (PyPy preferred for its JIT compiler, with CPython as a fallback). The development environment is defined in a Nix flake (`flake.nix`) that provides a reproducible shell containing Python 3.12, PyPy3, `ruff`, `pyright`, `just`, and `git`. Build tasks are orchestrated through a `justfile`. Source code is formatted and linted with `ruff` and type-checked with `pyright`.

Automated unit tests cover the two data structures built from scratch. `tests/test_hash_table.py` verifies insertion, lookup, key overwrite, collision chaining, automatic resizing, and load-factor maintenance. `tests/test_distance_table.py` verifies symmetric distance lookups, zero diagonal entries, and graceful error handling for unknown addresses. All tests are run with `just test` or `just validate`.

The main execution flow proceeds in seven stages:

1. Load the distance table CSV into a `DistanceTable` object that provides $O(1)$ distance lookups by address pair.
2. Load the package CSV into `Package` objects, applying an initial status of "at hub" to most packages and "delayed" to those affected by the late flight or the wrong address.
3. Insert every `Package` into the custom `HashTable` keyed by `package_id`.
4. Plan routes by parsing `special_notes` for constraints, assigning packages with deadline-first greedy insertion, simulating routes to repair missed deadlines, and running an end-of-day-only local search to lower mileage.
5. Set departure times: Truck 1 at 8:00 a.m., Truck 2 at 8:00 a.m. (delayed to 9:05 a.m. if carrying late-arrival packages), Truck 3 at 10:30 a.m.
6. Correct package #9's address at 10:20 a.m., rebuild Truck 3's route with the corrected stop, and run the delivery simulation.
7. Enter the interactive CLI, where the supervisor types a time (for example, "8:35 AM") and sees every package's current status, truck assignment, and deadline. Colours indicate status: green for delivered, yellow for en route, red for delayed, and blue for at hub.

== Evidence Screenshots

The following figures show the program output at the times required by the scenario.

*Figure 1. Package status at 8:35 a.m.* All forty packages are visible on their assigned trucks. Packages 6, 9, 25, 28, and 32 appear in "delayed" status. Packages 2, 7, 14, 15, 16, 29, 33, and 34 are already delivered. Trucks 1 and 2 are en route, while Truck 3 packages remain at the hub because that truck has not yet departed.

#image("screenshots/status-835am.png", width: 70%)

*Figure 2. Package status at 9:10 a.m.* Package 9 is still "delayed" because its address is not corrected until 10:20 a.m. Packages 6, 25, 28, and 32 are now "en route" or already delivered because Truck 2 departed at 9:05 a.m. Truck 3 packages remain "at hub" pending the 10:30 a.m. departure.

#image("screenshots/status-935am.png", width: 70%)

*Figure 3. Package status at 12:30 p.m.* All forty packages show "delivered at <time>" with no pending deliveries. Truck 3's last deliveries occurred around 11:10 a.m. to 11:46 a.m., confirming that the day ends only when every package has been served.

#image("screenshots/status-1203pm.png", width: 70%)

*Figure 4. Total mileage after complete execution.* The output header reads "Total mileage for all trucks: 89.3 miles," which is below the 140-mile requirement. Every package shows its final delivered status, truck assignment, and timestamp.

#image("screenshots/status-total-mileage.png", width: 70%)

= Future Modifications

If this project were done again, two modifications would improve robustness and maintainability.

First, the deadline-repair logic would be moved into the greedy assignment phase itself. Currently, the program assigns all packages first and then simulates routes to find violations, moving late packages afterward. A more integrated approach would simulate the route *before* committing each new package to a truck, rejecting any insertion that would cause a missed deadline. This would reduce the need for a separate repair loop and would produce better mileage because end-of-day packages would be placed with full knowledge of which deadline-sensitive packages are already locked in.

Second, the end-of-day-only local search would be expanded into a full simulated-annealing search that also considers moving 10:30-deadline packages between Trucks 1 and 2. Currently, the local search only moves end-of-day packages because deadline packages are anchored by their time constraints. However, a 10:30 package on Truck 2 might actually arrive earlier if moved to Truck 1, freeing space on Truck 2 for an end-of-day package that is currently on Truck 3. A temperature-based search would temporarily accept deadline-package moves that increase cost if they enable later cost-saving end-of-day swaps, escaping local minima that the current greedy search cannot.

= Conclusion

The WGUPS Routing Program demonstrates that a self-adjusting heuristic combined with a custom hash table can solve a real-world vehicle routing problem efficiently, correctly, and within tight constraints. The deadline-aware assignment pipeline, Clarke-Wright savings algorithm, and 2-opt local search deliver all forty packages in 89.3 miles, well under the 140-mile ceiling, while honoring every truck restriction, deadline, and mid-flight address correction. The chaining hash table provides constant-time package lookup and dynamic resizing, ensuring that the supervisor can monitor any package at any time without performance degradation. Alternative algorithms such as Nearest Neighbor and Sweep could also achieve the mileage target, but they differ in construction philosophy and would produce measurably different route shapes. Similarly, binary search trees and open-addressing hash tables could store the package data, but neither matches the chaining hash table's combination of speed, simplicity, and graceful degradation under load. Future iterations should integrate deadline simulation directly into the greedy assignment and expand the local search to consider time-sensitive package moves for further mileage reduction.

= References

Vehicle routing problem. (n.d.). In *Wikipedia*. https://en.wikipedia.org/wiki/Vehicle_routing_problem

2-opt. (n.d.). In *Wikipedia*. https://en.wikipedia.org/wiki/2-opt

Hash table. (n.d.). In *Wikipedia*. https://en.wikipedia.org/wiki/Hash_table
