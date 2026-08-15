"""Read-only dashboard boundary.

The package projects stored bot data to public JSON. Browser code lives in the
separate top-level ``dashboard`` application.
"""

from .projection import DashboardProjection

__all__ = ["DashboardProjection"]
