"""Custom SQLAlchemy column types.

``Money`` stores ``decimal.Decimal`` losslessly as its exact decimal string. We do NOT use
SQLAlchemy's ``Numeric`` because the SQLite (pysqlite) driver cannot bind ``Decimal`` natively and
SQLAlchemy falls back to float there — silent rounding. Money correctness is load-bearing in this
system (engine assumption A-16: money is ``Decimal``), and a refund that is a cent wrong is a
compliance defect, so we keep every amount exact across both backends (SQLite dev, Postgres prod).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import String
from sqlalchemy.types import TypeDecorator


class Money(TypeDecorator):
    """A Decimal-exact money type stored as a canonical decimal string (VARCHAR/TEXT)."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect) -> Optional[str]:
        if value is None:
            return None
        return str(Decimal(value))

    def process_result_value(self, value, dialect) -> Optional[Decimal]:
        if value is None:
            return None
        return Decimal(value)
