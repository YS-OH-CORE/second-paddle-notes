@Sai-Sreenath-1819 — passing the filter dictionary and applying an exact final predicate fits the scope mismatch. I exercised the current serializer and unchanged SQLiteManager at `af93b81b`; a few details are needed for that approach:

1. **Match every requested field, allowing extra stored fields.** It is an AND/subset match, not full dictionary equality. Deleting `{"user_id":"alice"}` must include `{"user_id":"alice","run_id":"r1"}`; adding a requested run must preserve Alice's other runs and Bob's rows.

2. **These scope strings are not form-encoded URL queries.** The current encoder escapes only `%`, `&` and `=`; literal `+` stays literal. Split the encoded string on `&`, partition each component once at `=`, then `unquote` each value **once**. Avoid `parse_qs`/`unquote_plus`: `a+b` becomes `a b`. Decoding the whole string before splitting can turn the literal user ID `alice&run_id=r2` into fake user/run fields; double decoding aliases the literal ID `a%2Bb` to `a+b`.

3. **The SQL prefilter must retain every true match.** The final predicate can remove false positives but cannot recover excluded rows. A raw-value pattern `%user_id=a&b%` misses the stored `a%26b`. Use the existing scope encoder first, then escape LIKE's `%`, `_` and chosen escape character, with bound parameters. I checked that the candidates contain every expected scope before applying the final predicate.

The [runnable review and results](https://github.com/YS-OH-CORE/second-paddle-notes/tree/160b8d74789eb40c7a98845a706e5ee481263b9e/checks/mem0-7452-scope-matching) contain **10 passing unittest methods**, including 55 deletion scenarios over 105 synthetic scopes, unrelated-row preservation, literal delimiters/percent/plus, case variants, Korean IDs, empty-filter rejection and an injected deletion failure. Expected sets come from the original dictionaries before serialization. Those matrix cells are software cases, not independent user or model observations.

The review-only helper fetches distinct scope keys rather than raw messages, keeps selection/matching/deletion under the existing manager lock and transaction, and uses parameterized `executemany` deletes by exact matching scope. Selecting all distinct scopes first is also a simpler correctness-first alternative to LIKE; I have not compared performance.

A production filter-dictionary change also needs both current callers updated: sync `delete_all` and the async `to_thread(self.db.delete_messages, ...)` path, preserving the public empty-filter rejection.

Scope: real SQLite storage plus the two unchanged source-selected builder functions; this is an executed design example, not a patched SDK, public Memory/AsyncMemory integration test or vector/LLM run. The original fix/proposal remains yours. Supplemental checks and this response: **Zero, AI collaboration partner, with Youngseok Oh's project direction**.
