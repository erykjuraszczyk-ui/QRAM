from threading import RLock
from typing import Any


class AddressError(ValueError):
    """Raised when an address is outside the configured memory range."""


class MemoryEngine:
    """Thread-safe, in-memory classical addressable store used to simulate QRAM."""

    def __init__(self, capacity: int = 1024) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self.capacity = capacity
        self._cells: dict[int, str] = {}
        self._lock = RLock()

    def _validate_address(self, address: int) -> None:
        if not isinstance(address, int) or isinstance(address, bool):
            raise AddressError("address must be an integer")
        if address < 0 or address >= self.capacity:
            raise AddressError(f"address must be between 0 and {self.capacity - 1}")

    def write(self, address: int, value: str) -> dict[str, Any]:
        self._validate_address(address)
        if not isinstance(value, str) or not value:
            raise ValueError("value must be a non-empty string")
        with self._lock:
            self._cells[address] = value
        return {"address": address, "value": value, "written": True}

    def read(self, address: int) -> dict[str, Any]:
        self._validate_address(address)
        with self._lock:
            if address not in self._cells:
                raise KeyError(f"address {address} is empty")
            return {"address": address, "value": self._cells[address]}

    def list_cells(self) -> list[dict[str, Any]]:
        with self._lock:
            return [{"address": k, "value": v} for k, v in sorted(self._cells.items())]

    def reset(self) -> int:
        with self._lock:
            count = len(self._cells)
            self._cells.clear()
            return count

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {"capacity": self.capacity, "used": len(self._cells), "free": self.capacity - len(self._cells)}
