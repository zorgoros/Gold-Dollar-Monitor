# Security

## Reporting a vulnerability

Open a [private security advisory](https://github.com/zorgoros/Gold-Dollar-Monitor/security/advisories/new).
Please don't open a public issue for anything exploitable. No bounty; credit given.

## How secrets are handled

- The Telegram bot token and channel id come from the environment or `.env`.
  Nothing else is a secret.
- `.env` and `data/` are gitignored. No credential is committed, and none is
  needed to run the tests.
- The token is never logged, never included in an exception message, and never
  echoed by any error path in `publishers/telegram.py`. A test asserts this
  (`test_the_token_never_appears_in_an_error_message`).
- Logs are structured JSON; only explicit fields are emitted.
- Rotate the token in BotFather, update `.env`, run `market-monitor health`,
  then revoke the old one. No restart or code change needed.

## Trust boundaries

- **Provider responses are untrusted input.** Prices are parsed strictly, and a
  layout change raises rather than producing a number. Values must be finite and
  positive; an implausible jump is flagged `SUSPECT`; a rial/toman unit
  regression is caught by a parity check and blocks publication.
- **No arbitrary code execution.** No `eval`, no pickle, no dynamic import of
  provider data. Responses are parsed as JSON only.
- **SQL is parameterised.** The single interpolated value is a migration
  filename from the repository itself, escaped.
- **The service is write-only outward.** It reads public endpoints and posts to
  one configured channel. It exposes no network listener, and there is no API,
  admin interface, or inbound command handling to attack.

## Deployment notes

- Run as a non-root user. The Docker image does; `deploy/systemd/` sets
  `ProtectSystem=strict` with a writable path only for `data/` and `logs/`.
- `chmod 600 .env`.
- Back up `data/market.db` off-box — the accumulated history cannot be re-fetched.
- CI runs entirely on fixtures, so pull-request jobs need no secrets and
  untrusted PRs can never reach production credentials.

## Dependencies

One runtime dependency (`httpx`); everything else is the standard library.
Versions are pinned in `requirements.lock`, and CI runs `pip-audit --strict`.
