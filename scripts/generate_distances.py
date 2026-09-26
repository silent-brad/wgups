"""
Generate a WGUPS-style distance table CSV from a list of addresses.

Two modes:
  1. OpenRouteService (ORS) API — accurate driving distances.
     Requires an API key from https://openrouteservice.org/ and a
     coordinates JSON file for every address.
  2. Haversine approximation — fast, free, but less accurate.
     Uses lat/lon coordinates and multiplies by a road-factor.

Both modes require --coords. The ORS mode uses the Matrix API, which
computes all pairwise distances in a single API call (well within
free-tier limits for up to ~50 locations).

Usage (ORS):
  export ORS_API_KEY=<your_key>
  python3 scripts/generate_distances.py \
      --addresses data/franklin/addresses.txt \
      --coords data/franklin/coords.json \
      --output data/franklin/WGUPS Distance Table.csv

Usage (Haversine approximation):
  python3 scripts/generate_distances.py \
      --addresses data/franklin/addresses.txt \
      --coords data/franklin/coords.json \
      --approximate \
      --output data/franklin/WGUPS Distance Table.csv
"""

import argparse
import csv
import json
import math
import os
import sys


def haversine(lat1, lon1, lat2, lon2):
    """Return great-circle distance in miles between two lat/lon points."""
    R = 3959.0  # Earth radius in miles
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def load_addresses(path):
    """Read one address per line. First line is the hub."""
    with open(path, "r") as f:
        return [line.strip() for line in f if line.strip()]


def load_coords(path):
    """Load a JSON dict mapping address -> [lat, lon]."""
    with open(path, "r") as f:
        return json.load(f)


def build_haversine_matrix(addresses, coords, road_factor=1.25):
    """Build a symmetric distance matrix using Haversine * road_factor."""
    n = len(addresses)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        lat_i, lon_i = coords[addresses[i]]
        for j in range(i, n):
            lat_j, lon_j = coords[addresses[j]]
            d = haversine(lat_i, lon_i, lat_j, lon_j) * road_factor
            matrix[i][j] = round(d, 1)
            matrix[j][i] = round(d, 1)
    return matrix


def build_ors_matrix(addresses, coords, api_key):
    """Build a symmetric distance matrix using the ORS Matrix API.

    Sends all locations in a single POST request and receives back a
    full N×N distance matrix.  This uses one API call regardless of
    how many address pairs there are.
    """
    import urllib.request

    n = len(addresses)
    locations = []
    for addr in addresses:
        lat, lon = coords[addr]
        locations.append([lon, lat])

    payload = json.dumps(
        {
            "locations": locations,
            "metrics": ["distance"],
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        "https://api.openrouteservice.org/v2/matrix/driving-car",
        data=payload,
        headers={
            "Authorization": api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        print(f"ORS Matrix API error: {e.code} {e.read().decode()}")
        sys.exit(1)

    # ORS returns distances in metres; convert to miles.
    raw = data["distances"]
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            d = raw[i][j]
            matrix[i][j] = round(d / 1609.344, 1) if d is not None else 0.0
    return matrix


def write_csv(addresses, matrix, output_path):
    """Write the WGUPS-style distance table CSV."""
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        # Header: blank cell then all destination addresses
        writer.writerow([""] + addresses)
        # Data rows: origin address followed by distances
        for i, origin in enumerate(addresses):
            writer.writerow([origin] + matrix[i])


def main():
    parser = argparse.ArgumentParser(description="Generate a WGUPS distance table CSV")
    parser.add_argument(
        "--addresses", required=True, help="File with one address per line"
    )
    parser.add_argument("--output", required=True, help="Output CSV path")
    parser.add_argument(
        "--coords", required=True, help="JSON file with address -> [lat, lon]"
    )
    parser.add_argument(
        "--approximate",
        action="store_true",
        help="Use Haversine approximation instead of ORS API",
    )
    parser.add_argument(
        "--road-factor",
        type=float,
        default=1.25,
        help="Multiplier for Haversine distances (default 1.25)",
    )
    args = parser.parse_args()

    addresses = load_addresses(args.addresses)
    if len(addresses) < 2:
        print("Need at least two addresses (hub + one stop).")
        sys.exit(1)

    coords = load_coords(args.coords)
    missing = set(addresses) - set(coords.keys())
    if missing:
        print(f"Missing coordinates for: {missing}")
        sys.exit(1)

    if args.approximate:
        matrix = build_haversine_matrix(addresses, coords, args.road_factor)
    else:
        api_key = os.environ.get("ORS_API_KEY")
        if not api_key:
            print("Set the ORS_API_KEY environment variable or use --approximate.")
            sys.exit(1)
        matrix = build_ors_matrix(addresses, coords, api_key)

    write_csv(addresses, matrix, args.output)
    print(f"Wrote {len(addresses)}x{len(addresses)} distance table to {args.output}")


if __name__ == "__main__":
    main()
