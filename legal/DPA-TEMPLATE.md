# Data Processing Addendum / Service-Provider Terms — TEMPLATE

> ⚠️ **DRAFT TEMPLATE — FOR ATTORNEY REVIEW. NOT LEGAL ADVICE.** Encodes the data-handling requirements
> in `docs/COMPLIANCE.md §2`. One document doubling as CCPA service-provider terms, GDPR Art. 28 processor
> terms (if EU personal data appears), and confidentiality flow-down. A privacy/trade attorney must finalize.

This Addendum supplements the Software License Agreement between **[Licensor]** ("Provider") and Licensee
("Customer") and governs Provider's processing of Customer data.

## 1. Roles & scope
Provider processes Customer data **solely to perform the Software service for Customer and on Customer's
documented instructions.** Provider is Customer's **service provider** (CCPA/CPRA) and, where EU personal
data is processed, a **processor** (GDPR Art. 28). Customer is the controller/business and the owner of its
data.

## 2. **[COMPLIANCE] Use limitation — CCPA service-provider terms**
Provider shall **not**: (a) retain, use, or disclose Customer personal information for any purpose other
than performing the service; (b) **sell or share** it; (c) **combine** it with other data except as
permitted for a service provider; or (d) use it for Provider's own commercial purposes, including
**training any model**. (Cal. Code Regs. tit. 11 § 7051.)

## 3. **[COMPLIANCE] Default processing posture — local / non-retention**
The Software is designed to process Customer import/export data **locally / in Customer's environment, and
NOT to retain it.** Provider's default posture is: compute ephemerally; do not store Customer trade data,
the generated CATAIR file, or the trace; delete inputs and outputs at session end. Any hosted/server-side
processing requires Customer's separate written instruction and the EEI provisions in Section 4.

## 4. **[COMPLIANCE] Electronic Export Information (EEI) confidentiality**
Customer's EEI (e.g., ITN, Schedule B, export values, parties) is **statutorily confidential** (13 U.S.C.
§ 301; 15 CFR § 30.60). To the extent any EEI is processed: (a) it is processed **only at Customer's
direction for Customer's own official drawback purpose**; (b) Provider acts, where applicable, as
Customer's **representative under written authorization (15 CFR § 30.3)** and is a U.S.-jurisdiction party;
(c) Provider shall **not disclose EEI for any nonofficial purpose** (15 CFR § 30.60(c)); and (d) the
local/non-retention posture in Section 3 is the default to avoid third-party disclosure.

## 5. **[COMPLIANCE] Confidentiality flow-down (broker customers)**
Where Customer is a licensed customs broker, Provider acknowledges Customer's confidentiality duty under
**19 CFR § 111.24** and shall treat all client/entry data as trade-secret-grade confidential information,
used and disclosed only as permitted by this Addendum.

## 6. Security
Provider shall maintain reasonable, industry-standard safeguards proportionate to the data: **encryption
in transit (TLS 1.2+) and at rest (AES-256)** for any data that persists; **access control** (least
privilege, MFA); **access-audit logging** (separate from the correctness trace); and a documented
retention/deletion policy. *(SOC 2 sequenced per COMPLIANCE §2: questionnaire/one-pager now → Type I when
required → Type II at scale.)*

## 7. Subprocessors
Provider shall maintain a current list of subprocessors (cloud host, error tracking, analytics, if any),
bind each to terms no less protective than this Addendum, and notify Customer of changes.

## 8. Data-subject / consumer rights
Provider shall assist Customer in responding to access/deletion/correction requests and, on termination or
request, **delete or return** Customer data.

## 9. **[COMPLIANCE] GDPR Art. 28 (if EU personal data is processed)**
Where EU personal data is processed, the standard Art. 28 processor obligations apply (process on
instructions; confidentiality; security; subprocessor consent; assistance; deletion/return; audit), and
EU→US transfers use Standard Contractual Clauses. *(Generally not triggered for a US-broker/US-transaction
tool unless EU natural persons appear — scope per COMPLIANCE §2.)*

## 10. Breach notification
Provider shall notify Customer without undue delay after becoming aware of a personal-data breach affecting
Customer data and cooperate in remediation.

---
*Schedule 1 — categories of data & processing. Schedule 2 — subprocessors. Schedule 3 — SCCs (if applicable).*
