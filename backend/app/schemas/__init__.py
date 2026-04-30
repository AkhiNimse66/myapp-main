"""Pydantic request/response schemas for the API layer.

Kept separate from DB models so the API surface can evolve independently
of the storage schema.  All schemas use ``model_config = ConfigDict(from_attributes=True)``
so they can be hydrated from dicts returned by repos.
"""
