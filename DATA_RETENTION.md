Data retention policy — SafeBallot (prototype)

Purpose

This document describes recommended data retention practices for SafeBallot in production. It is intentionally conservative: election data is sensitive and must be managed to preserve voter privacy and legal compliance.

Scope

- Applies to: votes (ciphertexts), user accounts and profiles, audit logs, uploaded voter lists, and backups.
- Does not include: application code or build artifacts.

Retention recommendations

1. Encrypted ballots (ciphertexts)
   - Retain indefinitely only if: key management guarantees decryption when needed, and legal/regulatory requirements mandate archival.
   - If retaining indefinitely, ensure:
     - Keys are stored in a robust KMS with access controls and audited key-use logs.
     - Backups are encrypted and access-restricted.
   - If retention is time-limited, document and implement a secure deletion process where ciphertexts are permanently deleted from DB and backups after the retention period.

2. User accounts and voter eligibility lists
   - Keep voter eligibility lists for a minimal period required for auditing (e.g., 1 year) unless longer retention is required by law.
   - Remove or anonymize PII (email, phone) when no longer necessary: replace PII fields with hashed identifiers or delete rows.

3. Audit logs
   - Retain at least 1 year for incident investigations. Sensitive logs should be redacted where possible.

4. Backups
   - Encrypted backups should follow the same retention policy as source data. Maintain a clear backup rotation (daily, weekly, monthly) and automatic expiration.

Data deletion

- Deletions must be documented and performed via controlled administrative workflows.
- For encrypted ballots, deletion means removing ciphertext records and ensuring backups are expired/rotated so that copies are eventually removed.

Legal & compliance

- Consult legal counsel for jurisdiction-specific retention requirements, especially for public elections.

Operational controls

- Maintain a retention schedule in `DEPLOYMENT.md` and enforce via automated tasks (cron/airflow) where possible.
- Log retention and deletion actions for auditability.

Contact

For assistance implementing retention automation or secure deletion scripts, open an issue or request changes in the repo.
