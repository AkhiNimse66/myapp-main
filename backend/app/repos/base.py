"""Generic async repository base.

All collection-specific repos inherit ``BaseRepo`` which provides the
low-level Motor wrappers. This keeps query-construction boilerplate out of
every subclass and gives us a single place to enforce conventions (e.g.
strip ``_id`` from every result, standardise projection defaults).

Subclasses must set the class-level ``collection_name`` attribute.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase


class BaseRepo:
    collection_name: str  # subclasses must override

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db[self.collection_name]

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def find_one(
        self,
        query: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return the first matching document, ``_id`` stripped by default."""
        proj = projection if projection is not None else {"_id": 0}
        return await self._col.find_one(query, proj)

    async def find_many(
        self,
        query: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
        sort: Optional[List[tuple]] = None,
        limit: int = 0,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:
        """Return a list of matching documents, ``_id`` stripped by default.

        ``limit=0`` means unlimited (Motor default).
        """
        proj = projection if projection is not None else {"_id": 0}
        cursor = self._col.find(query, proj)
        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        return await cursor.to_list(length=limit or None)

    async def count(self, query: Dict[str, Any]) -> int:
        return await self._col.count_documents(query)

    async def exists(self, query: Dict[str, Any]) -> bool:
        return bool(await self._col.find_one(query, {"_id": 1}))

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def insert_one(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Insert *doc* and return it with ``_id`` stripped.

        Motor mutates the dict in-place to add ``_id``, so we work on a
        shallow copy and pop the key before returning.
        """
        copy = {k: v for k, v in doc.items() if k != "_id"}
        await self._col.insert_one(copy)
        copy.pop("_id", None)
        return copy

    async def update_one(
        self,
        query: Dict[str, Any],
        update: Dict[str, Any],
        upsert: bool = False,
    ) -> bool:
        """Returns ``True`` if a document was modified or upserted."""
        result = await self._col.update_one(query, update, upsert=upsert)
        return result.modified_count > 0 or result.upserted_id is not None

    async def delete_one(self, query: Dict[str, Any]) -> bool:
        result = await self._col.delete_one(query)
        return result.deleted_count > 0

    async def delete_many(self, query: Dict[str, Any]) -> int:
        result = await self._col.delete_many(query)
        return result.deleted_count
