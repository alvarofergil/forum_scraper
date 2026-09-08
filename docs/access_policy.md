# Access Policy For armas.es

This project monitors only public pages from the armas.es forum and must keep
traffic extremely low, sequential, and respectful.

## Checked Source

- Checked on: 2026-09-08
- robots.txt URL: `https://www.armas.es/robots.txt`
- Target forum URL: `https://www.armas.es/foros/viewforum.php?f=96`

The retrieved `robots.txt` disallows `/ajax/`, `/core/`, `/logs/`, `/vendor/`,
`/var/`, and `/modules/`. It does not disallow `/foros/`.

The forum also exposes a public legal notice topic for private buy/sell activity:
`https://www.armas.es/foros/viewtopic.php?f=96&t=882510`.
The notice states that buy/sell operations happen between private users and that
users should consult the competent authorities for legal doubts.

No access rule found during TASK-006 required blocking the task before capturing
the minimal fixtures.

## Allowed Runtime Behavior

- Use only public forum pages.
- Use a clear User-Agent, for example `PersonalForumMonitor/1.0`.
- Make requests sequentially.
- Apply the configured delay between requests.
- Do not log or persist cookies, session IDs, secrets, credentials, or raw
  unsanitized HTML.
- Keep topic downloads limited to candidates and favorites in future runtime
  flows.

## Prohibited Behavior

- No login automation.
- No CAPTCHA bypass.
- No proxy rotation.
- No fingerprint evasion.
- No concurrent scraping in v1.
- No rate-limit bypass.
- No scraping of private or authenticated pages.
- No storage of raw unsanitized pages.

## TASK-006 Capture Log

The following public pages were requested manually for sanitized test fixtures:

| Purpose | URL | Notes |
|---|---|---|
| robots check | `https://www.armas.es/robots.txt` | Confirmed `/foros/` is not disallowed. |
| listing page 1 | `https://www.armas.es/foros/viewforum.php?f=96` | Contains `Anuncios`, `Temas`, topic rows, and pagination. |
| listing page 2 | `https://www.armas.es/foros/viewforum.php?f=96&start=18` | Contains second listing page and next-page link. |
| legal notice topic | `https://www.armas.es/foros/viewtopic.php?f=96&t=882510` | Used for access policy and one-page topic fixture. |
| multipage topic page 1 | `https://www.armas.es/foros/viewtopic.php?f=96&t=1181036` | Used for multipost and pagination fixture. |
| multipage topic page 2 | `https://www.armas.es/foros/viewtopic.php?f=96&t=1181036&start=18` | Used to preserve a second topic page shape. |

Each content page request was made sequentially with a pause between captures.

## Fixture Sanitization

Committed fixtures under `tests/fixtures/armas_es/` are sanitized copies:

- session IDs removed from links and forms;
- scripts, styles, iframes, ad blocks outside the parser-relevant body, and
  profile metadata removed where possible;
- profile user IDs and public usernames replaced with stable placeholders;
- email addresses and phone-like numbers replaced with placeholders;
- topic IDs and post IDs preserved because they are parser inputs.

Raw downloaded HTML must remain outside the repository.
