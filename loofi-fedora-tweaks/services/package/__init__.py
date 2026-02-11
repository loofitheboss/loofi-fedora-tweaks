"""
Package service module — v23.0 Architecture Hardening.

Provides BasePackageService interface and concrete implementations
for DNF and rpm-ostree package management.
"""

from services.package.base import BasePackageService
from services.package.service import (
    DnfPackageService,
    RpmOstreePackageService,
    get_package_service,
)

__all__ = [
    "BasePackageService",
    "DnfPackageService",
    "RpmOstreePackageService",
    "get_package_service",
]
