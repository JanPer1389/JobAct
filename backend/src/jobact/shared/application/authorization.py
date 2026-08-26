"""Shared application-layer authorization errors.

`AuthorizationError` is raised by handlers when a caller's organization
doesn't own a resource they're trying to act on -- e.g. starting a visit
against a customer that belongs to a different organization. Kept in
`shared/application` (not a context-specific module) since every
context's handlers need the same check against the same error type.
"""

from __future__ import annotations


class AuthorizationError(Exception):
    pass
