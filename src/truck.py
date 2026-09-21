"""
Truck data model.

Tracks the state of a single delivery truck: which packages are loaded,
how far it has driven, its current location, and elapsed time.
"""


class Truck:
    """
    A WGUPS delivery truck.

    Attributes
    ----------
    truck_id : int
        Truck identifier (1, 2, or 3).
    capacity : int
        Maximum number of packages (default 16).
    speed : float
        Average speed in miles per hour (default 18).
    packages : list[Package]
        Packages currently loaded on this truck.
    mileage : float
        Total miles driven so far.
    current_location : str
        The address where the truck is currently located.
    hub_address : str
        The hub address (trucks start and end here).
    departure_time : float | None
        Hour-fraction when the truck left the hub.
    current_time : float | None
        Elapsed simulation time in hour-fractions.
    route : list[str]
        Ordered list of delivery addresses (no hub bookends).
    """

    def __init__(self, truck_id, capacity=16, speed=18, hub_address=None):
        self.truck_id = truck_id
        self.capacity = capacity
        self.speed = speed
        self.packages = []
        self.mileage = 0.0
        self.current_location = hub_address
        self.hub_address = hub_address
        self.departure_time = None
        self.current_time = None
        self.route = []

    def load_package(self, pkg):
        """Add a package to this truck's load."""
        self.packages.append(pkg)

    def depart(self, departure_time):
        """Seed current_time before the first delivery leg."""
        self.departure_time = departure_time
        self.current_time = departure_time

    def drive_to(self, address, distance_table):
        """
        Drive from the current location to *address*.

        Updates mileage and current_time by distance / speed.
        """
        distance = distance_table.get_distance(self.current_location, address)
        self.mileage += distance
        self.current_time += distance / self.speed
        self.current_location = address

    def return_to_hub(self, distance_table):
        """Drive from the current location back to the hub."""
        distance = distance_table.get_distance(self.current_location, self.hub_address)
        self.mileage += distance
        self.current_time += distance / self.speed
        self.current_location = self.hub_address
