# WGUPS Routing Program — C950 Project

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff)
![Nix](https://img.shields.io/badge/Nix-5277C3?logo=nixos&logoColor=fff)
![PyPy](https://img.shields.io/badge/PyPy-3.11-193440?logo=pypy&logoColor=white)
![Ruff](https://custom-icon-badges.demolab.com/badge/Ruff-261230.svg?logo=ruff-logo)
![Typst](https://img.shields.io/badge/Typst-typeset-239dae?logo=typst&logoColor=white)

> 🏆 Awarded the **WGU Excellence Award** for outstanding project quality and technical depth.

A Python implementation of the Western Governors University Parcel Service routing system. It plans, optimizes, and simulates delivery routes for three trucks and forty packages in downtown Salt Lake City using a custom chaining hash table and a Clarke-Wright savings heuristic polished by 2-opt local search.

## Results

| Metric             | Value                          |
| ------------------ | ------------------------------ |
| Total distance     | **89.3 miles** (target: < 140) |
| Packages delivered | **40 / 40**                    |
| Truck capacity     | 16 packages max                |
| Average speed      | 18 mph                         |

## Documentation

Two papers accompany this implementation, both authored in Typst:

- **[Plan (Task 1)](docs/plan.pdf)** — Algorithm and data structure overview submitted before implementation. Describes the Clarke-Wright savings heuristic with 2-opt local search, the chaining hash table design, pseudocode, runtime analysis, and a scenario walkthrough.
- **[Writeup (Task 2)](docs/writeup.pdf)** — Algorithm and data structure justification submitted after implementation. Justifies the chosen approach, verifies all scenario requirements are met, identifies alternative algorithms (Nearest Neighbor, Sweep) and data structures (BST, open-addressing hash table), and includes execution screenshots as evidence.

## Quick Start

```bash
# Enter the dev shell (Nix flake) — provides pypy3, ruff, pyright, just
nix develop --extra-experimental-features "nix-command flakes"

# Run the program with default Salt Lake City data
just run

# Run with a different city dataset
just run --data-dir data/franklin/

# Validate (lint, format, typecheck, test, build)
just validate
```

## Adding a New City

The program is fully city-agnostic. To add a new delivery area, create a data directory with three files and point the program at it with `--data-dir <path>`.

### 1. Create the data directory

```
data/<city>/
  addresses.txt      # one address per line; first line is the hub
  coords.json        # address -> [lat, lon] mapping
  WGUPS Package File.csv
  config.json        # optional: wrong-address correction scenario
```

The sample **Franklin, TN** dataset (`data/franklin/`) can be used as a template.

### 2. Generate the distance table

**Option A — OpenRouteService API (accurate driving distances)**

```bash
export ORS_API_KEY=<your_key>
python3 scripts/generate_distances.py \
    --addresses data/<city>/addresses.txt \
    --coords data/<city>/coords.json \
    --output "data/<city>/WGUPS Distance Table.csv"
```

**Option B — Haversine approximation (no API key)**

```bash
python3 scripts/generate_distances.py \
    --addresses data/<city>/addresses.txt \
    --coords data/<city>/coords.json \
    --approximate \
    --output "data/<city>/WGUPS Distance Table.csv"
```

The generator produces a symmetric distance matrix in the exact WGUPS CSV format the routing program expects. The `--coords` file is required for both modes because the ORS Matrix API needs lat/lon coordinates.

### 3. Run the program

```bash
just run --data-dir data/<city>/
```

## Key Features

- **City-agnostic** — hub address is read from the distance table, and the wrong-address correction is read from `config.json`. Switching cities only requires a new data directory.
- **Distance-table generator** — `scripts/generate_distances.py` builds a WGUPS-style CSV from a list of addresses using either the OpenRouteService Matrix API (accurate driving distances, one API call for the whole matrix) or a Haversine approximation (no API key needed).
- **Custom hash table** — list-based chaining with dynamic resizing; no `dict` or third-party libraries.
- **Self-adjusting heuristic** — Clarke-Wright savings construction dynamically shrinks the merge pool after each combination.
- **2-opt local search** — removes edge crossings in each truck route after construction.
- **Hard-constraint handling** — truck-2-only, flight-delayed arrivals (9:05 a.m.), wrong-address correction (10:20 a.m., package #9), and grouped deliveries.
- **Two-driver dispatching** — Trucks 1 and 2 depart at 8:00 a.m.; Truck 3 departs at 10:30 a.m. after a driver returns.
- **Status queries at any time** — enter `8:40 AM`, `10:00 AM`, `12:30 PM`, or `all` at the CLI prompt.
