"""
Package data model.

Represents a single WGUPS package with all fields required by the
hash table (delivery address, deadline, city, zip code, weight,
delivery status) plus auxiliary fields for routing and tracking.
"""


class Package:
    """
    A WGUPS package.

    Attributes
    ----------
    package_id : int
        Unique identifier and hash-table key.
    address : str
        Street address of the delivery destination.
    city : str
        Delivery city.
    state : str
        Delivery state abbreviation.
    zip_code : str
        Delivery ZIP code.
    deadline : str
        Promised delivery time (e.g. "9:00 AM", "10:30 AM", "EOD").
    weight : float
        Package weight in kilograms.
    status : str
        One of: "delayed", "at hub", "en route", "delivered at <time>".
    special_notes : str
        Constraint text from the package file (e.g. truck restrictions).
    truck_id : int | None
        Which truck is carrying this package.
    delivery_time : float | None
        Hour-fraction when the package was delivered (e.g. 10.5 for 10:30).
    """

    def __init__(
        self,
        package_id,
        address,
        city,
        state,
        zip_code,
        deadline,
        weight,
        status,
        special_notes,
        truck_id,
        delivery_time,
    ):
        self.package_id = package_id
        self.address = address
        self.city = city
        self.state = state
        self.zip_code = zip_code
        self.deadline = deadline
        self.weight = weight
        self.status = status
        self.special_notes = special_notes
        self.truck_id = truck_id
        self.delivery_time = delivery_time

    def __repr__(self):
        return (
            f"Package(package_id={self.package_id}, address={self.address}, "
            f"city={self.city}, state={self.state}, zip_code={self.zip_code}, "
            f"deadline={self.deadline}, weight={self.weight}, "
            f"status={self.status}, special_notes={self.special_notes}, "
            f"truck_id={self.truck_id}, delivery_time={self.delivery_time})"
        )
