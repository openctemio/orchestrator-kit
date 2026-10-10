---
name: safe-live-db-query
description: Run a diagnostic query against a production database without side effects or error noise - schema check first, read-only, aggregates only, from a file with ON_ERROR_STOP. Use whenever you are about to query a live or shared database.
---

People read the production database log. A guessed column name leaves an ERROR line that looks like a
production fault and costs someone an investigation. That happened more than once with "quick" queries.

1. Prefer a restored copy or a scratch database. Test any new SQL there first; never on live.
2. Check the schema before writing the query, every time, even for a quick look. Names AND types:
   ```sql
   SELECT column_name, data_type FROM information_schema.columns
   WHERE table_schema = 'public' AND table_name = 'the_table' ORDER BY ordinal_position;
   ```
   Also confirm the table exists in this version (`to_regclass('public.the_table')`): a half-applied deploy can
   run new code against an old schema.
3. Read-only and small:
   - wrap it in `BEGIN READ ONLY; ... ROLLBACK;` or use a read-only role;
   - aggregates and counts, not row dumps; `LIMIT` anything that returns rows;
   - never select secrets, tokens, password hashes or personal data; count them instead;
   - scope by tenant when the question is about one tenant;
   - set `SET statement_timeout = '5s';` so a bad plan cannot load the server.
4. Run it from a file so a typo stops the batch instead of cascading:
   `psql -X -v ON_ERROR_STOP=1 -f query.sql` (copy the file into the container if needed).
5. If an error still reaches the live log, say so at once with the timestamp and the exact statement, so nobody
   mistakes it for a fault.
6. Logs from scratch databases (tests that check negative paths) are not production; tell the reader which log
   they are looking at before diagnosing.

Writes to live data are not diagnostics: they go through a reviewed migration or an approved, backed-up runbook.
