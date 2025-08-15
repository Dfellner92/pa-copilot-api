from enum import Enum

class PriorAuthStatus(str, Enum):
    requested = "requested"
    pending = "pending"
    approved = "approved"
    denied = "denied"
    not_required = "not_required"
