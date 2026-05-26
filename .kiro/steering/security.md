---
inclusion: always
---
# Security Rules

## Never Commit Secrets

No agent may write any of the following into files that could be committed to git:

- Passwords, passphrases, or authentication tokens
- SSH private keys or key material
- Login sequences from session logs (the password prompt and anything after it until the next game prompt)
- Player credentials or the contents of `~/Documents/Games/TradeWars/creds`
- Raw session log content that includes the SSH connection handshake or login flow

## When Quoting Session Logs

Session logs at `~/Documents/Games/TradeWars/sessions/` contain sensitive data. When writing to the knowledge base or any committed file:

- NEVER include the password entry sequence
- NEVER include the `script` header line (contains command with key paths and hostname)
- Strip or redact any player-identifying auth data
- It IS safe to quote game output after login (sector displays, port data, trade sequences, chat)

## When In Doubt

If you're unsure whether content is sensitive, do not include it. Describe the pattern instead of quoting it verbatim.
