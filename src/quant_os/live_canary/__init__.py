"""Tiny-live crypto canary lane.

The package exposes a highly restricted live-canary execution surface. The
default configuration is blocked, the real adapter is unavailable unless a
future local setup supplies one, and tests use only the fake adapter.
"""

