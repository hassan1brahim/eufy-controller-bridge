"""
adapters/__init__.py — Controller adapter registry.

_ADAPTERS is the single source of truth for supported controllers.
Adding a new controller: create the adapter file, import it here, append it.
"""

from . import ps5, eightbitdo

_ADAPTERS = [ps5, eightbitdo]


def open_any():
    """Try each registered adapter in priority order.

    Returns (adapter_module, hidapi.Device) for the first controller found.
    Raises RuntimeError listing all failed attempts if none connect.
    """
    errors = []
    for adapter in _ADAPTERS:
        try:
            dev = adapter.open_controller()
            return adapter, dev
        except RuntimeError as e:
            errors.append(str(e))
    raise RuntimeError("No supported controller found:\n  " + "\n  ".join(errors))
