"""Intermediate commercial records — the normalized output of the NetSuite spine parsers
and the input to the commercial<->customs join.

These are *not* engine models. They carry only the COMMERCIAL transaction facts NetSuite
actually holds (item / qty / value / dates / parties / shipment refs) — never duty/customs
data, which lives in the broker/ACE overlay (``ingest.customs``). The join (``ingest.join``)
fuses a ``CommercialImport`` with a ``CustomsEntryLine`` to produce an engine ``ImportLine``,
and a ``CommercialExport`` with an ``AesExportRecord`` to produce an engine ``ExportLine``.

Money is ``decimal.Decimal`` (engine convention D-003 / A-16); quantities are int HTSUS units.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass
class CommercialImport:
    """One inbound commercial line from the NetSuite IMPORT spine (PO / Item Receipt / Vendor Bill).

    The ``join_ref`` is the shared key the broker entry summary is reconciled against — in the
    real world this is the PO number or commercial-invoice number the broker keys the 7501 to.
    NetSuite does NOT carry the entry number or the duty; those arrive in the customs overlay.
    """

    join_ref: str                       # PO no. / commercial invoice no. — the customs join key
    item: str                           # NetSuite item name/number (``item``)
    description: str                    # item display name / memo
    quantity: int                       # received qty in commercial UoM (``quantity``)
    unit_of_measure: str                # ``units`` (commercial UoM label)
    unit_cost: Decimal                  # ``rate`` (purchase price per unit) — fallback entered value
    amount: Decimal                     # ``amount`` (extended line cost) — fallback entered value
    transaction_date: date              # ``trandate`` of the receipt/bill
    vendor: str                         # ``entity`` (supplier) — NetSuite display name
    vendor_country: str = "CN"          # supplier country (``shipcountry`` / vendor default)
    tranid: str = ""                    # NetSuite document number (``tranid``) for provenance
    internal_id: str = ""               # NetSuite ``id`` internal id
    record_type: str = "itemreceipt"    # purchaseorder | itemreceipt | vendorbill
    hint_hts: Optional[str] = None      # optional item-master HTS hint (rarely populated cleanly)
    source_row: int = -1


@dataclass
class CommercialExport:
    """One outbound commercial line from the NetSuite EXPORT spine (SO / Item Fulfillment / Invoice).

    ``join_ref`` is the shipment/invoice key the AES/EEI filing is reconciled against (the AES
    record carries the same commercial-invoice or shipment reference). NetSuite holds the sale;
    AES holds the export-proof (ITN) and the country of ultimate destination of record.
    """

    join_ref: str                       # SO no. / commercial invoice no. — the AES join key
    item: str                           # ``item``
    description: str
    quantity: int                       # shipped qty (``quantity``)
    unit_of_measure: str                # ``units``
    unit_price: Decimal                 # ``rate`` (sales price per unit) — value at port of export
    amount: Decimal                     # ``amount`` (extended) — fallback per-unit basis
    transaction_date: date              # ``trandate`` of the fulfillment/invoice (ship date proxy)
    customer: str                       # ``entity`` (sold-to)
    ship_country: str = "US"            # ``shipcountry`` (ISO) — destination of record
    tranid: str = ""                    # NetSuite document number
    internal_id: str = ""
    record_type: str = "itemfulfillment"  # salesorder | itemfulfillment | invoice
    hint_hts: Optional[str] = None      # optional item-master Schedule B / HTS hint
    source_row: int = -1
