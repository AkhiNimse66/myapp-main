"""Repository layer — one module per collection.

Each repo wraps a single Motor collection and exposes typed async methods.
All methods return plain ``dict`` or ``List[dict]`` — no ORM objects.

Usage::

    from app.repos.users_repo import UsersRepo
    from app.db import get_db

    repo = UsersRepo(get_db())
    user = await repo.find_by_email("alice@example.com")
"""
from app.repos.users_repo import UsersRepo
from app.repos.creators_repo import CreatorsRepo
from app.repos.agencies_repo import AgenciesRepo
from app.repos.brands_repo import BrandsRepo
from app.repos.deals_repo import DealsRepo
from app.repos.transactions_repo import TransactionsRepo
from app.repos.social_repo import SocialRepo
from app.repos.contracts_repo import ContractsRepo
from app.repos.emails_repo import EmailsRepo
from app.repos.events_repo import EventsRepo

__all__ = [
    "UsersRepo",
    "CreatorsRepo",
    "AgenciesRepo",
    "BrandsRepo",
    "DealsRepo",
    "TransactionsRepo",
    "SocialRepo",
    "ContractsRepo",
    "EmailsRepo",
    "EventsRepo",
]
