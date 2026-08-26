"""Bounded contexts: identity, customers, visits, reports, media, etc.

Each context is a self-contained vertical slice (domain/application/
infrastructure/api) around one business capability. Contexts may depend
on `jobact.shared`, never on each other's internals directly.
"""
