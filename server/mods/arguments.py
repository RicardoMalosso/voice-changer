"""Command-line value parsers for the VCClient server."""

from argparse import ArgumentTypeError


def parse_bool(value: str) -> bool:
    normalized = value.lower()
    if normalized in {"y", "yes", "t", "true", "on", "1"}:
        return True
    if normalized in {"n", "no", "f", "false", "off", "0"}:
        return False
    raise ArgumentTypeError(f"Expected a boolean value, got {value!r}.")
