"""Inventory / identification accounting methods for DIRECT-IDENTIFICATION claims (19 CFR 190.14).

Citations: 19 CFR 190.14(a),(c). RESEARCH Q7. Assumption A-08.

Scope (A-08): these conventions apply ONLY to direct-identification claims (which imported lot supplies
an exported unit). Substitution drawback does NOT use FIFO tracing — its eligibility is the 8-digit HTS
match + per-unit averaging, and the optimizer's freedom to assign within a bucket is the substitution
analogue. So this module is intentionally narrow in the MVP; it exists to (a) encode the permitted
methods faithfully and (b) order designated lots for any direct-ID matching.

"Low-to-high" is the claimant-favorable convention: consume the LOWEST-drawback units first, preserving
the higher-drawback units to claim (190.14(c)(3)).
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Callable


class AccountingMethod(str, Enum):
    FIFO = "fifo"                # 190.14(c)(1) — first received, first identified
    LIFO = "lifo"               # 190.14(c)(2)
    LOW_TO_HIGH = "low_to_high"  # 190.14(c)(3) — claimant-favorable
    AVERAGE = "average"          # 190.14(c)(4)


def order_lots(
    lots: list,
    method: AccountingMethod,
    received_key: Callable[[object], object],
    per_unit_drawback_key: Callable[[object], Decimal],
) -> list:
    """Return ``lots`` ordered by the chosen accounting method — i.e., the sequence in which they are
    consumed/identified against exported units.

    - FIFO: earliest received first.
    - LIFO: latest received first.
    - LOW_TO_HIGH: lowest per-unit drawback first (preserve high-drawback lots to claim).
    - AVERAGE: order is immaterial (each unit carries the average); we return FIFO order for stability.
    """
    if method is AccountingMethod.FIFO:
        return sorted(lots, key=received_key)
    if method is AccountingMethod.LIFO:
        return sorted(lots, key=received_key, reverse=True)
    if method is AccountingMethod.LOW_TO_HIGH:
        return sorted(lots, key=per_unit_drawback_key)
    return sorted(lots, key=received_key)  # AVERAGE -> stable FIFO order
