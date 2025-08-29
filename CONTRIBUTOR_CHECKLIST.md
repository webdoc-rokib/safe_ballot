Contributor checklist — handling real ballots and sensitive data

Before contributing code or changes that touch ballot handling, voting logic, or PII, ensure the following:

1. Understand sensitivity
- Changes that affect how ballots are stored, encrypted, or decrypted are high risk.
- Changes that touch user PII (email/phone) or eligibility lists need careful review.

2. Tests
- Add unit tests covering any change to encryption, decryption, or tally code.
- For database migrations affecting Profile/PII fields, add tests that create and migrate data.

3. Review & approvals
- Submit a PR and tag at least one maintainer for review.
- For cryptographic changes, request an expert review from someone with applied cryptography experience.

4. Secrets & CI
- Never commit secrets to the repository (keys, passwords, tokens). Use a secrets manager and CI secrets.
- If adding CI jobs that require secrets, document required secrets in the PR template (do not store them in code).

5. Deployment & migration
- Document any required migrations and coordinate deploys so migrations are applied before feature toggles are enabled.

6. Auditing
- Record key decisions (key management model, retention policies) in documentation and link them from the PR.

7. Communication
- For production elections, coordinate with stakeholders and have an incident response plan in case of key loss or integrity issues.

If you'd like, I can add a PR template and a CODEOWNERS file to help enforce reviews for sensitive areas.
