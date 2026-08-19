"""File-backed Single Source of Truth memory for coding agents."""

from memory_ssot.gates import GateError
from memory_ssot.models import ClaimTag, Fact, Tier
from memory_ssot.store import MemoryStore

__version__ = "0.1.0"
__all__ = [
    "ClaimTag",
    "Fact",
    "GateError",
    "MemoryStore",
    "Tier",
    "__version__",
]
