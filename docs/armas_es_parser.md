# armas.es Parser Notes

These notes describe the sanitized fixtures captured in TASK-006 and the DOM
signals expected to guide TASK-007 and TASK-008. They are not parser
implementations.

## Fixtures

| Fixture | Source Shape | Purpose |
|---|---|---|
| `tests/fixtures/armas_es/listing_page_1.html` | `viewforum.php?f=96` page 1 | Listing parser, announcement exclusion, page 1 pagination. |
| `tests/fixtures/armas_es/listing_page_2.html` | `viewforum.php?f=96&start=18` | Listing parser, page 2 pagination and varied topic rows. |
| `tests/fixtures/armas_es/topic_legal_notice.html` | one-page `viewtopic` | Topic parser with a single post and closed topic controls. |
| `tests/fixtures/armas_es/topic_multipage_page_1.html` | `viewtopic` page 1 | Topic parser with many posts and next-page pagination. |
| `tests/fixtures/armas_es/topic_multipage_page_2.html` | `viewtopic` page 2 | Topic parser with later posts and current page detection. |

## Listing DOM Signals

- The main forum body is under `div#page-body`.
- Announcements appear in `div.forumbg.announcement`.
- Ordinary topics appear after the header whose visible text is `Temas`.
- Topic rows are list items under `ul.topiclist.topics`.
- Topic title links use `a.topictitle`.
- The canonical identity must come from the `t` query parameter.
- The parser must ignore `sid`, `start`, `p`, anchors, row position, and title as
  identity inputs.
- Reply and view counts are in `dd.posts` and `dd.views`.
- Last activity information is in `dd.lastpost`.
- Top and bottom pagination blocks use `div.pagination`.
- The next page is exposed as `li.next a[rel="next"]` when present.
- The page-jump input exposes `data-per-page="18"` and `data-start-name="start"`.
- Listing pagination is page-level data exposed as `ParsedListingPage.next_page_url`;
  individual `TopicListing` rows do not carry page navigation.
- `next_page_url` must stay on the configured host, use `/foros/viewforum.php`,
  match the configured forum id, and keep only the `f` and `start` query
  parameters. It must omit ephemeral or row-specific values such as `sid`, `p`,
  and anchors.

## Topic DOM Signals

- The topic title appears in `h2.topic-title a`.
- Post containers use `div.post` with ids such as `p4461618`.
- The visible post body is under `div.postbody`.
- Individual post content appears in `div.content`.
- The post author/date line appears in `p.author`.
- Pagination appears in `div.pagination`; page 1 exposes a next link and page 2
  exposes the active current page.
- The parser should return only posts visible in the supplied HTML and must not
  fetch additional pages.

## Date Handling

armas.es renders dates without an explicit timezone. Parser tasks should treat
forum-visible dates as `Europe/Madrid` local time at the source adapter boundary
and return timezone-aware UTC datetimes to the rest of the application.

## Sanitization Notes

Fixtures intentionally keep phpBB classes, topic IDs, post IDs, pagination
links, titles, snippets, and visible post content needed by parser tests.
They intentionally remove or replace session IDs, profile identifiers,
usernames, email addresses, phone-like numbers, scripts, iframes, and unrelated
profile metadata.

Any future fixture refresh must repeat the same sanitization checks before
commit.
