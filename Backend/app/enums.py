from enum import Enum

class PackageStatus(str, Enum):
    REGISTERED = "REGISTERED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
