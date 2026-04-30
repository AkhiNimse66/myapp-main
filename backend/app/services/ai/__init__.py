"""AI service namespace.

All creator/brand/compliance intelligence + the risk decision engine live here.
The contract is in :mod:`app.services.ai.interfaces`; concrete providers
(mock or real) are wired in :mod:`app.services.ai.factory`.

Routers and deal services depend ONLY on the Protocol types — never on a
concrete provider class. This keeps mock ↔ real swaps to a single env var.
"""
