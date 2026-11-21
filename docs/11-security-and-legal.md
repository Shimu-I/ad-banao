# Security, privacy and legal

Controls for accounts, uploads, secrets, privacy and legal wording.

| Area | Control |
| --- | --- |
| Authentication | Provider-managed sign-in, JWT, short-lived tokens. No hand-written password storage |
| Authorisation | Every query filtered by owner. Tests prove user A cannot read user B's brand, product or ad |
| Uploads | Size limit, type check by content (not file name), pixel limit, original bytes stored under a hash name, never executed or served from the app directory |
| Injection | Parameterised queries only (SQLAlchemy). User text sent to the AI is quoted as data. Prompt-injection phrases are flagged |
| Secrets | Environment variables only. `.env` ignored. Secret scanning on GitHub |
| Rate limiting | Per-user limits on generation and upload |
| Transport | HTTPS only in staging and production. CORS limited to the frontend origin |
| Dependencies | Dependabot updates, `pip-audit` and `npm audit` in CI |
| Privacy | Plain notice that free AI providers may use submitted data. Do not upload confidential material on free tiers. Data export and account deletion planned before public launch |
| Legal | The tool flags issues and is not legal advice. Wording is "no issues detected", not "guaranteed compliant". Users confirm they own the images and logos they upload. Restricted products (alcohol, tobacco, medicine) get a warning |
| Audit | Approvals, overrides and who did them are recorded |
