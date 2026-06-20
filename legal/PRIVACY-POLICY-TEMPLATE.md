# Privacy Policy — TEMPLATE

> ⚠️ **DRAFT TEMPLATE — FOR ATTORNEY REVIEW. NOT LEGAL ADVICE.** Public-facing privacy policy starting
> point per `docs/COMPLIANCE.md §2`. Finalize with counsel; confirm CCPA "business" status (likely below
> thresholds today → you act as a *service provider*) and whether GDPR is triggered.

**[Licensor / Product]** ("we") provides duty-drawback decision-support software. This policy explains how
we handle data.

## What we process
- **Account / contact data** of the people who use the Software (name, work email) — to provide and
  support the service.
- **Trade data** you input (import entry / 7501 / ACE data; export / AES-EEI data; bills of lading) —
  **processed to compute your estimate and prepare claim materials.** This is overwhelmingly business/
  commercial data about entities (e.g., EINs), not consumer personal information.

## **[COMPLIANCE] How we handle your trade data**
The Software offers **two modes**, and we describe each truthfully:
- **Local / on-prem:** your import/export data is processed **in your environment and not stored by us** —
  computed ephemerally and deleted after processing.
- **Hosted (multi-tenant):** to maintain your book of claims, claim history, and audit binder (records you
  are required to keep), we **store** your data in a **tenant-isolated, encrypted** account, governed by our
  **Data Processing Addendum**.

In **both** modes we **do not sell or share your data and do not use it to train any model.** Scanned
documents may be read by a document-OCR subprocessor bound to **no-training / zero-retention** terms — or,
at your option, by an **in-tenant local engine** so nothing leaves your account. Confidential export
information (EEI) is handled per **15 CFR § 30.60** as your authorized agent (see our Data Processing
Addendum).

## Why we process
To provide the estimate/claim-preparation service, support it, secure it, and meet legal obligations.

## Sharing
We do not sell personal information. We share data only with subprocessors necessary to run the service
(e.g., cloud hosting; a document-OCR provider on a no-training / zero-retention tier — which you can disable
in favor of in-tenant local OCR), each bound by confidentiality and data-protection terms, and as required
by law.

## Your rights
Depending on your location (e.g., CCPA/CPRA, GDPR), you may have rights to access, delete, correct, or
opt out. Contact us at **[contact]** to exercise them. For business customers, our **Data Processing
Addendum** governs and we act as your service provider/processor.

## Security
We use reasonable, industry-standard safeguards (encryption in transit/at rest for any persisted data,
access controls, audit logging) proportionate to the data.

## Retention
We retain account data for the duration of the relationship. In **local / on-prem** mode we **do not retain
your trade data** beyond the processing session. In **hosted** mode we retain your trade data and claim
records **to maintain your book of claims and audit binder**, per a retention/deletion policy keyed to the
statutory clocks and your instructions; you may export or request deletion (subject to records you must
keep). You remain the keeper of legal record for the statutory periods: **EEI 5 years from export**
(15 CFR § 30.10); **drawback records 3 years from liquidation** (19 U.S.C. § 1508(c)).

## Contact & changes
**[Legal name, address, contact email.]** We will post changes here with an updated date.

*Last updated: [date].*
