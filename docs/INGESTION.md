# INGESTION.md — the real-format ingestion layer

How real delivered data becomes the engine's input contract (`drawback.models.Dataset`).

> **The core fact this layer is built around:** NetSuite (or any ERP) holds the **commercial**
> transaction — item, quantity, value, dates, parties, shipment references — but **not** the duty
> or the customs entry. The duty comes from the **broker / ACE entry summary (CBP Form 7501)**; the
> export proof comes from **AES/EEI (the ITN)**. So ingestion **joins a NetSuite commercial spine to
> a customs overlay**. It never invents duty and never invents export proof.

All NetSuite/CBP connectivity here is **simulated / fixture-mode** and clearly marked. The ingest
core is **standard-library only** (`csv` / `json`), no network, no OCR (structured files only).

```
NetSuite export dir                         Customs overlay dir
  item_receipts_import.csv  ─┐                 ace_entry_summary_7501.csv ─┐
  item_fulfillments_export.csv ─┐│             aes_eei_export_proof.csv  ─┐│
        │ ingest.netsuite       ││                   │ ingest.customs     ││
        ▼                       ▼▼                   ▼                    ▼▼
  CommercialImport[]      CommercialExport[]   CustomsEntryLine[]   AesExportRecord[]
        └──────────────┬───────────┘                 └─────────┬──────────┘
                       ▼                 ingest.join            ▼
                  ImportLine[]  ◄── JOIN on PO/CI ref ──►  ExportLine[]
                       └──────────── ingest.__init__ : validate ───────────┘
                                          ▼
                                   Dataset  ──►  drawback.estimate.build_estimate
```

| File | Role |
|------|------|
| `ingest/records.py`  | Intermediate **commercial** records (`CommercialImport`, `CommercialExport`) — the normalized NetSuite spine output. No duty, no customs data. |
| `ingest/netsuite.py` | Parse NetSuite saved-search / SuiteQL exports (**JSON + CSV**), real field names, two spines. |
| `ingest/customs.py`  | Parse the **7501/ACE** entry summary and the **AES/EEI** proof; defines `CustomsEntryLine`, `AesExportRecord`; maps duty components → `ChargeType`. |
| `ingest/join.py`     | The commercial↔customs **JOIN** → engine `ImportLine`/`ExportLine`, with quantity reconciliation + multi-receipt handling. |
| `ingest/client.py`   | `NetSuiteClient` interface + `StubbedNetSuiteClient` (**the live-API seam**, NOT CONNECTED). |
| `ingest/__init__.py` | `ingest_dataset(netsuite_dir, customs_dir) -> Dataset`; **validates** the contract and **fails loudly** (`IngestionError`) on a hard schema break. |

Assumption tags follow the repo convention (`docs/ASSUMPTIONS.md`):
**[VERIFIED]** = traced to a primary source in `docs/RESEARCH.md`; **[INFERRED]** = defensibly
derived but not stated verbatim; **[GUESS]** = a reasonable choice where research could not confirm,
made conservatively and flagged here.

---

## 1. NetSuite IMPORT spine → `CommercialImport`

Source: a NetSuite saved search / SuiteQL over **Purchase Orders / Item Receipts / Vendor Bills**.
Columns are matched case-insensitively with the cross-account aliases in
`netsuite._FIELD_ALIASES` (a saved-search CSV labels columns by field id or "Label"; SuiteQL
returns the column name). Demo file: `samples/demo_netsuite/item_receipts_import.csv`.

| NetSuite field (real) | → `CommercialImport` | Tag | Note |
|---|---|---|---|
| `otherrefnum` / `Other Ref Num` / PO number / `createdfrom` | `join_ref` | **[INFERRED]** | The key the broker reconciles the 7501 to. Brokers vary (PO vs. commercial-invoice no.); we accept several and normalize punctuation/case in the join. |
| `item` | `item` | **[VERIFIED]** | NetSuite item id. |
| `memo` / item display name | `description` | **[INFERRED]** | Line memo is the usual human description on a receipt; falls back to `item`. |
| `quantity` | `quantity` (int HTSUS units) | **[VERIFIED]** | Received qty. Fractional commercial qty → row flagged (HTSUS units are int, A-16). |
| `units` | `unit_of_measure` | **[VERIFIED]** | Commercial UoM label. |
| `rate` | `unit_cost` | **[VERIFIED]** | Purchase price per unit. **Fallback** entered-value basis only; the 7501 `Entered Value` governs. |
| `amount` | `amount` | **[VERIFIED]** | Extended line cost. Derived as `rate × qty` if absent. |
| `trandate` | `transaction_date` | **[VERIFIED]** | Receipt/bill date. *Not* the import date — the **7501 Import Date** starts the 5-yr clock (A-09). |
| `entity` | `vendor` | **[VERIFIED]** | Supplier display name. |
| `shipcountry` / vendor country | `vendor_country` | **[GUESS]** | Country of supply ≈ country of origin in the persona; the **7501 Country of Origin** is authoritative and overrides on join. |
| `tranid` / `id` | `tranid` / `internal_id` | **[VERIFIED]** | Provenance back to the NetSuite document. |
| `custcol_hts` / item-master HTS | `hint_hts` | **[INFERRED]** | Optional item-master harmonized-code custom field; only a hint — the 7501 HTSUS is authoritative for imports. |

The commercial line carries **no duty and no entry number** — those exist only on the customs side.

## 2. NetSuite EXPORT spine → `CommercialExport`

Source: a NetSuite saved search / SuiteQL over **Sales Orders / Item Fulfillments / Invoices**.
Demo file: `samples/demo_netsuite/item_fulfillments_export.csv`.

| NetSuite field (real) | → `CommercialExport` | Tag | Note |
|---|---|---|---|
| `otherrefnum` / commercial-invoice no. / `tranid` | `join_ref` | **[INFERRED]** | The shipment/invoice key the **AES/EEI** filing also carries. |
| `item` | `item` | **[VERIFIED]** | |
| `quantity` | `quantity` (int) | **[VERIFIED]** | Shipped qty. |
| `rate` | `unit_price` | **[INFERRED]** | Sales price per unit ≈ **value at the U.S. port of export** when AES does not price the line (A-21 comparator input). AES `Value at Export` is preferred when present. |
| `trandate` | `transaction_date` | **[INFERRED]** | Fulfillment/invoice date as a ship-date proxy; the **AES Date of Export** is authoritative when matched. |
| `entity` | `customer` | **[VERIFIED]** | Sold-to. |
| `shipcountry` | `ship_country` | **[INFERRED]** | Destination of record; the **AES Country of Ultimate Destination** overrides when matched (Q15). |
| `custcol_hts` / Schedule B custom field | `hint_hts` | **[INFERRED]** | Item-master Schedule B / HTS. Used to classify an export that has **no** AES match, and to disambiguate which AES line to pair on a multi-line invoice. |

## 3. Customs overlay

### 3a. CBP Form 7501 / ACE entry summary → `CustomsEntryLine`  (RESEARCH Q14)

The "ACE Reports / ITRAC CSV/Excel" surface: one row per entry-summary line. Headers follow the
7501 block/column names brokers emit; matched via `customs._norm_header` (case/punctuation-
insensitive) with aliases. Demo file: `samples/demo_customs/ace_entry_summary_7501.csv`.

| 7501 field (block/col) | header examples | → `CustomsEntryLine` | Tag |
|---|---|---|---|
| Entry Number (blk 1) | `Entry Number`, `Entry No` | `entry_number` (engine join key) | **[VERIFIED]** |
| Line (col 31) | `Line`, `ES Line` | `line_number` | **[VERIFIED]** |
| Importer of Record (blk 27) | `Importer of Record`, `IOR` | `importer_of_record` (claimant EIN) | **[VERIFIED]** |
| HTSUS (col 33A) | `HTSUS`, `HTS`, `Tariff` | `hts10` (normalized 10-digit) | **[VERIFIED]** |
| Description (col 32) | `Description` | `description` | **[VERIFIED]** |
| Import Date (blk 11) | `Import Date`, `Date of Importation` | `import_date` (starts 5-yr clock, A-09) | **[VERIFIED]** |
| Entry Date (blk 7) | `Entry Date` | `entry_date` | **[VERIFIED]** |
| Net Quantity (col 35) | `Net Quantity`, `HTS Quantity` | `quantity` (int HTSUS units) | **[VERIFIED]** |
| UOM (col 35) | `UOM`, `Unit` | `unit_of_measure` | **[VERIFIED]** |
| Entered Value (col 36A) | `Entered Value`, `Customs Value` | `entered_value` (ad-valorem basis) | **[VERIFIED]** |
| Country of Origin (blk 10) | `Country of Origin`, `COO` | `country_of_origin` | **[VERIFIED]** |
| Liquidation status | `Liquidation Status` | `liquidated` (`OPEN`/`UNLIQUIDATED`/… → False, A-14) | **[INFERRED]** |
| PO / commercial invoice | `PO Number`, `Commercial Invoice` | `join_ref` (commercial join key) | **[INFERRED]** |

**Duty/fee component → `ChargeType`** (`customs._CHARGE_HEADER_MAP`). Fees are read **by column /
accounting code**, never inferred from a single block-44 total (Q14).

| Component | header examples (incl. acct code) | → `ChargeType` | Eligible? | Tag |
|---|---|---|---|---|
| Ordinary customs duty (col 38) | `Duty`, `Base Duty` | `BASE_DUTY` | yes | **[VERIFIED]** |
| Section 301 | `Sec 301`, `Section 301`, `301` | `SECTION_301` | yes (CSMS #18-000419) | **[VERIFIED]** |
| Section 232 | `Sec 232`, `Section 232` | `SECTION_232` | **no** | **[INFERRED]** — brokers haven't standardized a 232 column; we map any of these labels. |
| Section 122 | `Sec 122`, `122` | `SECTION_122` | **no** | **[INFERRED]** |
| IEEPA | `IEEPA`, `Reciprocal`, `Fentanyl` | `IEEPA` | **no → CAPE** (A-13) | **[INFERRED]** |
| MPF (acct 499) | `MPF`, `Acct 499`, `499` | `MPF` | yes | **[VERIFIED]** |
| HMF (acct 501) | `HMF`, `Acct 501`, `501` | `HMF` | yes | **[VERIFIED]** |
| AD / CVD (acct 012/013) | `AD/CVD`, `Antidumping`, `Acct 012` | `AD_CVD` | **no** (19 USC 1677h) | **[VERIFIED]** |
| Importation excise (I.R. tax) | `Excise`, `IR Tax` | `EXCISE` | yes (99%) | **[VERIFIED]** |

Eligibility itself is **not** decided here — it stays in `config.tariff_eligibility` (A-12). Ingestion
only routes each dollar to the correct `ChargeType` bucket; the engine excludes the ineligible ones.

### 3b. AES / EEI export proof → `AesExportRecord`  (RESEARCH Q15)

The EEI elements filed in AES (15 CFR 30.6); AES returns the **ITN** as the proof token. A bill of
lading / AWB is the accepted documentary alternative (the CATAIR export record carries a BOL
Indicator + SCAC, Q15/Q17). Demo file: `samples/demo_customs/aes_eei_export_proof.csv`.

| EEI element | header examples | → `AesExportRecord` | Tag |
|---|---|---|---|
| ITN | `ITN`, `Internal Transaction Number` | `itn` (proof token) | **[VERIFIED]** |
| Schedule B / HTSUS (10-digit) | `Schedule B`, `HTSUS` | `hts10` (normalized; authoritative for export classification) | **[VERIFIED]** |
| Date of Export | `Date of Export`, `Departure Date` | `export_date` | **[VERIFIED]** |
| Quantity / UOM | `Quantity`, `UOM` | `quantity` / `unit_of_measure` | **[VERIFIED]** |
| Value at port of export | `Value at Export`, `FOB Value` | `value_at_export` (→ `value_per_unit`, A-21 comparator) | **[VERIFIED]** |
| USPPI ID | `USPPI`, `EIN` | `usppi_id` | **[VERIFIED]** |
| Country of Ultimate Destination | `Country of Ultimate Destination` | `destination_country` (ISO) | **[VERIFIED]** |
| Bill of Lading | `Bill of Lading`, `BOL`, `AWB` | `bill_of_lading` (documentary proof) | **[VERIFIED]** |
| Commercial invoice / shipment ref | `Commercial Invoice`, `Shipment Reference` | `join_ref` (commercial join key) | **[INFERRED]** |

---

## 4. The JOIN  (`ingest/join.py`)

### Import side — `join_imports(commercial, customs) -> ImportLine[]`

The **customs entry line is the unit of a designated import** (duty is assessed per 7501 line), so
the join is driven by the customs lines. For each one we look up NetSuite receipts sharing the
normalized `join_ref`.

| Engine `ImportLine` field | Source | Tag |
|---|---|---|
| `entry_number`, `line_number`, `importer_id`, `import_date`, `entry_date`, `quantity`, `entered_value`, `charges`, `country_of_origin`, `liquidated` | **customs** (7501/ACE) — authoritative | **[VERIFIED]** |
| `description` | **NetSuite** memo if present, else 7501 description | **[INFERRED]** |
| `unit_of_measure` | customs UoM | **[VERIFIED]** |

**Quantity reconciliation [INFERRED]:** commercial received qty (summed across receipts) is compared
to the 7501 net qty. The **customs quantity governs** the `ImportLine` — it is what duty was
assessed on and what the claim designates — and any discrepancy beyond a small tolerance is reported
to the `DataQualityReport`. *Choice made & flagged:* tolerance = **2%** (`_QTY_TOLERANCE`, **[GUESS]**);
below it the drift is treated as rounding/packaging noise, above it it is surfaced as a real mismatch.
Either way the customs qty wins and the discrepancy is visible.

**Multi-receipt-to-one-entry [INFERRED]:** when several NetSuite Item Receipts consolidate under one
7501 line (a container covering multiple receipts), they are grouped by `join_ref`. We attribute the
duty **once** — to the single entry line — producing **one** `ImportLine` (never duplicating the
duty), and flag the consolidation. This prevents the double-count that would arise from emitting one
import per receipt.

**Missing customs [INFERRED]:** a NetSuite receipt with no matching 7501 line has **no duty and no
entry number**, so it cannot be a drawback designated import. It is **dropped** (never fabricated)
and flagged. *Choice: drop, don't mark* — a designated import with no entry would be a guaranteed
filing defect.

**Entry without commercial [INFERRED]:** a 7501 line with no NetSuite match is still a valid
designated import (the duty is real). It is **kept**, using the customs description, and flagged
"customs-only context".

### Export side — `join_exports(commercial, aes) -> ExportLine[]`

Driven by the NetSuite sales/fulfillment lines; each is matched to an AES/EEI record on the
normalized shipment/commercial-invoice ref. On a multi-line invoice, the AES line whose 8-digit
prefix matches the NetSuite item HTS hint is preferred; otherwise the first unused AES line on that
reference.

| Engine `ExportLine` field | Source | Tag |
|---|---|---|
| `quantity`, `unit_of_measure` | NetSuite (the shipped commercial qty) | **[VERIFIED]** |
| `hts10` | **AES Schedule B/HTSUS** when matched, else the NetSuite item HTS hint | **[INFERRED]** |
| `export_date` | **AES Date of Export** when matched, else `trandate` | **[INFERRED]** |
| `value_per_unit` | **AES Value at Export** when priced there, else NetSuite `rate` | **[INFERRED]** (A-21) |
| `destination_country` | **AES** ultimate destination when matched, else `shipcountry` | **[INFERRED]** |
| `has_export_proof`, `proof_kind`, `reference` | **AES**: matched → `True` + ITN (or B/L); no match → `False` | **[VERIFIED]** (A-15) |

**No AES match [VERIFIED]:** the sale still becomes an `ExportLine`, but `has_export_proof=False`.
The engine then **demotes it to "potential — needs review"** (A-15, 19 CFR 190.72) — proof is never
invented. An AES line with no commercial match is flagged and **not used** (proof with no sale to
attach to). Matched export references become the **ITN** (or B/L), so the trace cites the actual
proof token.

---

## 5. Orchestration & validation  (`ingest/__init__.py`)

`ingest_dataset(netsuite_dir, customs_dir) -> Dataset` runs **parse → join → validate**.

Two failure levels, matching the engine's conservatism:
- **Recoverable data-quality issues** (a dropped row, a qty discrepancy, a missing AES match) go to
  the `DataQualityReport` and the pipeline continues — the estimate is simply smaller and honest.
- **Hard schema breaks** (a produced line violates the engine input contract: HTS not 10 digits,
  qty not a positive int, missing required field, wrong type) **raise `IngestionError`** and fail
  loudly, because feeding the engine malformed lines would silently corrupt a money figure. Pass
  `strict=False` to downgrade these to reported errors instead of raising.

The validator enforces, per produced line: non-empty `entry_number`/`reference`; `is_valid_hts10`
(exactly 10 digits, via `rules.hts`); positive-int `quantity`; `Decimal` money; `date` dates; and
`charges` keyed by `ChargeType` with `Decimal` amounts.

---

## 6. The live-API seam  (`ingest/client.py`)

`NetSuiteClient` is the interface (`fetch_imports()` / `fetch_exports()` → the intermediate
commercial records). The shipped `StubbedNetSuiteClient` reads the fixture files and is **clearly
marked NOT CONNECTED**:
- module banner `FIXTURE_MODE_BANNER = "NOT CONNECTED — fixture mode …"`,
- a `connected = False` class attribute (a live client would set `True` once authenticated),
- an instance `.mode` carrying the banner.

It performs **no network I/O and holds no OAuth/TBA credentials**. A production `LiveNetSuiteClient`
would authenticate via NetSuite Token-Based Auth (OAuth 1.0a) against SuiteTalk REST / SuiteQL, run
the two saved searches/queries, page the results, and map each row through `ingest.netsuite` exactly
as the stub does. **This client is the entire NetSuite integration surface** — everything downstream
(customs parse + join + validate + estimate) is identical regardless of source, so swapping the stub
for the live client is the whole job. `ingest_from_client(client, customs_dir)` injects it.

---

## 7. The demo dataset  (`samples/demo_netsuite/` + `samples/demo_customs/`)

A mid-market electronics importer, **Apex Electronics Importing LLC** (EIN 47-3319008), built to
exercise every path. Uses HTS codes present in `engine/drawback/data/hts_reference.py` so the engine
prices them. Files:

- `demo_netsuite/item_receipts_import.csv` — 16 NetSuite Item Receipts (the import spine).
- `demo_netsuite/item_fulfillments_export.csv` — 12 NetSuite Item Fulfillments (the export spine).
- `demo_customs/ace_entry_summary_7501.csv` — 14 ACE/7501 entry-summary lines (duty overlay).
- `demo_customs/aes_eei_export_proof.csv` — 11 AES/EEI export-proof lines (ITN overlay).

Deliberate cases baked in:

| Case | Where | Exercises |
|---|---|---|
| Multi-receipt → one entry | `IR10561A` + `IR10561B` (800+1200) → entry `JXM-2410561-9` (2000) | the multi-receipt rule + qty reconciliation |
| Missing customs | `IR10808` (office chair, `PO-10808`) — no 7501 line | drop-and-flag of a commercial-only receipt |
| Section 232 layer | entries for `PO-10527`, `PO-10637` | ineligible-duty exclusion |
| IEEPA layer | entry for `PO-10604` | CAPE routing (A-13), not drawback |
| Not liquidated | entry `JXM-2510702-5` (`OPEN`) | A-14 exclusion from the headline |
| Out-of-window | entry `JXM-2110455-3` (import 2021-02-10) | the 5-year window (A-09) |
| Missing AES | fulfillment `IF50079` (`CI-50079`) — no AES row | missing-export-proof → potential (A-15) |
| "Other"-basket, substitutable | export `7326.90.8635` (`CI-50055`) ↔ import `7326.90.8635` | the 8→10-digit fallback into the **headline** |
| "Other"-basket, blocked | export `7326.90.8688` (`CI-50094`) | `OTHER_BASKET_NO_MATCH` (10-digit also "other") |
| Lesser-of cap binding | export values per unit > import duty per unit across the motor/PSU/switch pairs | the lesser-of comparator (A-03/A-21) |

**Result (as of `AS_OF` 2026-06-19):** 14 imports + 12 exports → **headline ≈ \$137,696.51**
(range low ≈ \$12,476.26), **potential ≈ \$14,806.03**, against an eligible-duty pool of
≈ \$221,618.02. 10 defensible headline pairs across 6 HTS buckets (including the 10-digit "other"
basket); blocked buckets: missing-export-proof ≈ \$14,806, ineligible-duty (232) ≈ \$15,750,
other-basket-no-match ≈ \$4,045, and unmatched import capacity. Both a defensible bucket and a
needs-review bucket are non-empty, as required. *(Figures are illustrative — duty rates come from the
curated HTS reference fixture, not a licensed HTSUS dataset.)*

### Run it

```bash
cd /Users/achreki/Desktop/drawback-engine
./.venv/bin/python -m pytest engine/tests/test_ingest_*.py -q     # the ingestion suite
./.venv/bin/python -m pytest -q                                   # the full suite (must stay green)
```

```python
from drawback.ingest import ingest_dataset
from drawback.estimate import build_estimate

ds = ingest_dataset("samples/demo_netsuite", "samples/demo_customs")
est = build_estimate(ds)
print(est.headline_point, est.potential_total)
```

---

## 8. Tagged mapping assumptions — summary

The ambiguous calls, all made conservatively and surfaced (never silently guessed):

- **Join key [INFERRED]** — brokers key the 7501 to a PO number *or* a commercial-invoice number;
  we accept several header names and normalize case/punctuation. If neither side carries a shared
  ref, the row cannot join and is flagged (import dropped / export left unproven).
- **Quantity authority [INFERRED]** + **2% tolerance [GUESS]** — the **customs** qty governs the
  designated import; commercial drift beyond 2% is flagged, below it treated as packaging noise.
- **Multi-receipt attribution [INFERRED]** — duty attributed **once** to the entry line; one
  `ImportLine` per 7501 line, never per receipt (prevents double-count).
- **Missing customs → drop [INFERRED]** — a commercial receipt with no entry has no duty to
  designate; dropped, not marked, to avoid a filing defect.
- **Country of origin [GUESS]** — NetSuite supplier country is only a fallback; the 7501 Country of
  Origin overrides on join.
- **Export classification & value [INFERRED]** — AES Schedule B/HTSUS, Date of Export, destination,
  and Value at Export are authoritative when matched; NetSuite item-HTS hint / `rate` / `trandate`
  are fallbacks for an export with no AES filing (so it can still classify and be held as potential).
- **232 / 122 / IEEPA column names [INFERRED]** — no standardized broker column; mapped from common
  labels to the correct (ineligible) `ChargeType`; eligibility itself stays in `config`.
- **No AES → unproven, not dropped [VERIFIED]** — keep the export, set `has_export_proof=False`, let
  the engine demote it (A-15). Proof is never fabricated.
