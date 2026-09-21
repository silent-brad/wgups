# WGUPS Routing Program — C950 Project

A Python implementation of the Western Governors University Parcel Service routing system. It plans, optimizes, and simulates delivery routes for three trucks and forty packages in downtown Salt Lake City using a custom chaining hash table and a Clarke-Wright savings heuristic polished by 2-opt local search.

## Results

| Metric             | Value                           |
| ------------------ | ------------------------------- |
| Total distance     | **103.8 miles** (target: < 140) |
| Packages delivered | **40 / 40**                     |
| Truck capacity     | 16 packages max                 |
| Average speed      | 18 mph                          |

## Quick Start

```bash
# Enter the dev shell (Nix flake)
nix develop --extra-experimental-features "nix-command flakes"

# Run the program
just run

# Or with PyPy
just build && just run-compiled

# Validate (lint, format, typecheck, compile)
just validate
```

## Key Features

- **Custom hash table** — list-based chaining with dynamic resizing; no `dict` or third-party libraries.
- **Self-adjusting heuristic** — Clarke-Wright savings construction dynamically shrinks the merge pool after each combination.
- **2-opt local search** — removes edge crossings in each truck route after construction.
- **Hard-constraint handling** — truck-2-only, flight-delayed arrivals (9:05 a.m.), wrong-address correction (10:20 a.m., package #9), and grouped deliveries.
- **Two-driver dispatching** — Trucks 1 and 2 depart at 8:00 a.m.; Truck 3 departs at 10:30 a.m. after a driver returns.
- **Status queries at any time** — enter `8:40 AM`, `10:00 AM`, `12:30 PM`, or `all` at the CLI prompt.
