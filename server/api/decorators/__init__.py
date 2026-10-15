
"""Route annotations used by the custom FastAPI router.

`authenticated()` and `check_permission(...)` remain the public auth annotation
surface. Their decorators only attach metadata; request-time enforcement runs
through FastAPI dependency injection.
"""
