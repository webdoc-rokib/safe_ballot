Privacy notice — SafeBallot (prototype)

Overview

SafeBallot is a privacy-focused voting prototype. This notice explains what personal data the application may collect, why it is collected, and how it is used.

Personal data collected

- Account information: username, first/last name, email, phone (optional). Used for account management and notifications.
- Voter eligibility lists: usernames or identifiers used to gate access to elections.
- Audit logs: administrative actions and important system events.
- Ballots: encrypted ciphertexts representing votes. The system stores only ciphertexts and does not associate ciphertexts with user identifiers.

Purpose and lawful basis

- Account information: required to provide authentication and account recovery.
- Ballots: stored to produce election tallies and audit results. We collect and store ciphertexts so that results can be computed without exposing voter identities.

Retention

Refer to `DATA_RETENTION.md` for retention schedules and deletion procedures.

Sharing and disclosure

- Ballots (ciphertexts) are not shared with third parties except as required for auditing or legal processes, and only under strict controls.
- Aggregate results may be published publicly once elections conclude.

User rights

- Users may request deletion of their account and PII; note that deletion of an account does not retroactively remove a cast ballot if ballots are stored anonymously and cannot be linked to a specific account.
- For any data access or deletion requests, contact the system administrator.

Security

- The project encrypts ballots using AES‑GCM and relies on secure key management in production.
- PII is protected with access control and should be stored in encrypted databases and backups.

Contact

For privacy inquiries, contact the project maintainer via the repository issue tracker.
