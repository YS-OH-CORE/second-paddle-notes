# SPDX-License-Identifier: Apache-2.0
"""Executed review examples for mem0 #7452, not a production SDK patch.

Zero (AI collaboration partner), with Youngseok Oh's project direction.
Uses the pinned upstream SQLiteManager and two unchanged scope-builder functions.
Only Python's standard library is needed. No network or model calls.
"""
from __future__ import annotations

import ast
import asyncio
import hashlib
import importlib.util
import json
import platform
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, unquote, unquote_plus


ROOT = Path(__file__).resolve().parent
PIN = "af93b81bc9573be1b78014b5005a0b0d950605bb"
SOURCE_BLOBS = {
    "main.py": "6f4292be9d238420062964d2801a3855f5d08570",
    "storage.py": "0b49c8e8be46779722a7827b2e98319930433d40",
}
KEYS = {"user_id", "agent_id", "run_id"}


def source_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


for filename, expected in SOURCE_BLOBS.items():
    if source_blob((ROOT / "upstream" / filename).read_bytes()) != expected:
        raise RuntimeError("Pinned source mismatch: " + filename)

spec = importlib.util.spec_from_file_location("review_upstream_storage", ROOT / "upstream" / "storage.py")
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
SQLiteManager = storage.SQLiteManager

tree = ast.parse((ROOT / "upstream" / "main.py").read_text(encoding="utf-8"))
names = {"_escape_scope_value", "_build_session_scope"}
selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
assert {node.name for node in selected} == names
helper_globals = {"Any": Any}
exec(compile(ast.Module(body=selected, type_ignores=[]), "pinned_scope_helpers", "exec"), helper_globals)
escape_scope = helper_globals["_escape_scope_value"]
build_scope = helper_globals["_build_session_scope"]


def validate_filter(filters):
    # This review example accepts already validated, nonempty SDK entity IDs.
    # Empty or malformed input must not become a match-all deletion.
    if not isinstance(filters, dict) or not filters or set(filters) - KEYS:
        raise ValueError("Expected a nonempty mapping of supported entity keys")
    if any(not isinstance(value, str) or not value for value in filters.values()):
        raise ValueError("Expected nonempty string entity IDs")


def decode_scope(scope):
    # Structural split FIRST. unquote is deliberately not unquote_plus/parse_qs.
    decoded = {}
    for component in scope.split("&"):
        key, sep, value = component.partition("=")
        if not sep or key not in KEYS or key in decoded or not value:
            raise ValueError("Malformed scope")
        decoded[key] = unquote(value, errors="strict")
    return decoded


def matches(scope, filters):
    try:
        stored = decode_scope(scope)
    except (ValueError, UnicodeError):
        return False
    return all(stored.get(key) == value for key, value in filters.items())


def like_literal(value):
    # Same canonical encoder as save; LIKE metacharacters are a second layer.
    return escape_scope(value).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def prefilter_scopes(connection, filters):
    validate_filter(filters)
    ordered = sorted(filters.items())
    where = " AND ".join("session_scope LIKE ? ESCAPE '\\'" for _ in ordered)
    values = ["%" + key + "=" + like_literal(value) + "%" for key, value in ordered]
    return [row[0] for row in connection.execute("SELECT DISTINCT session_scope FROM messages WHERE " + where, values)]


def reference_delete(manager, filters):
    """Review-only two-stage example; operates on actual upstream SQLite tables.

    Fetch scope keys, not message contents. Select, exact subset match, and
    parameterized scope deletes share the existing manager lock/transaction.
    executemany avoids one unbounded IN list. No SDK methods are monkeypatched.
    """
    validate_filter(filters)
    with manager._lock:
        try:
            manager.connection.execute("BEGIN")
            candidates = prefilter_scopes(manager.connection, filters)
            targets = [scope for scope in candidates if matches(scope, filters)]
            manager.connection.executemany(
                "DELETE FROM messages WHERE session_scope = ?", ((scope,) for scope in targets)
            )
            manager.connection.execute("COMMIT")
        except Exception:
            manager.connection.execute("ROLLBACK")
            raise
    return targets


IDS = [
    "alice", "alice2", "bob", "ALICE", "a+b", "a&b", "a=b", "a%2Bb", "a_b", "aXb",
    "a%b", "a\\b", "앨리스", "o'hara", "a%26b", "alice&run_id=r2", "a%3Db",
]
SCOPES = []
for user in IDS:
    for extra in [{}, {"run_id": "r1"}, {"run_id": "r2"}, {"agent_id": "bot"},
                  {"agent_id": "bot", "run_id": "r1"}, {"agent_id": "other", "run_id": "r1"}]:
        SCOPES.append(dict(user_id=user, **extra))
SCOPES.extend([{"run_id": "r1"}, {"agent_id": "bot"}, {"agent_id": "bot", "run_id": "r1"}])
FILTERS = []
for user in IDS:
    FILTERS.extend([{"user_id": user}, {"user_id": user, "run_id": "r1"},
                    {"user_id": user, "agent_id": "bot"}])
FILTERS.extend([{"agent_id": "bot"}, {"run_id": "r1"}, {"agent_id": "bot", "run_id": "r1"},
                {"user_id": "nobody"}])


def oracle(scope_dict, filters):
    # Gold is determined from the original dictionaries BEFORE serialization.
    return filters.items() <= scope_dict.items()


def seed(manager, scopes=SCOPES):
    for index, fields in enumerate(scopes):
        manager.save_messages(
            [{"role": "user", "content": "synthetic-row-" + str(index)},
             {"role": "assistant", "content": "synthetic-response-" + str(index)}],
            build_scope(fields),
        )


def remaining(manager):
    return {row[0] for row in manager.connection.execute("SELECT DISTINCT session_scope FROM messages")}


class ScopeReview(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mem0-scope-review-")
        self.db = SQLiteManager(str(Path(self.temp.name) / "review.sqlite3"))

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_current_exact_key_misses_two_sessions_but_exact_control_deletes(self):
        records = [{"user_id": "alice"}, {"user_id": "alice", "run_id": "r1"},
                   {"user_id": "alice", "run_id": "r2"}, {"user_id": "bob", "run_id": "r1"}]
        seed(self.db, records)
        self.db.delete_messages(build_scope({"user_id": "alice"}))
        self.assertEqual(remaining(self.db), {build_scope(row) for row in records[1:]})

    def test_each_canonical_prefilter_is_a_superset_and_final_match_is_exact(self):
        seed(self.db)
        for filters in FILTERS:
            with self.subTest(filters=filters):
                expected = {build_scope(row) for row in SCOPES if oracle(row, filters)}
                candidates = set(prefilter_scopes(self.db.connection, filters))
                self.assertLessEqual(expected, candidates)
                actual = {scope for scope in candidates if matches(scope, filters)}
                self.assertEqual(expected, actual)

    def test_real_sqlite_deletion_preserves_every_unmatched_scope(self):
        for filters in FILTERS:
            with self.subTest(filters=filters):
                seed(self.db)
                expected_left = {build_scope(row) for row in SCOPES if not oracle(row, filters)}
                reference_delete(self.db, filters)
                self.assertEqual(expected_left, remaining(self.db))
                count = self.db.connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
                self.assertEqual(count, 2 * len(expected_left))
                self.db.connection.execute("DELETE FROM messages")
                self.db.connection.commit()

    def test_double_decode_and_plus_decoders_are_detectably_wrong(self):
        plus_scope = build_scope({"user_id": "a+b"})
        percent_scope = build_scope({"user_id": "a%2Bb"})
        self.assertEqual(decode_scope(plus_scope)["user_id"], "a+b")
        self.assertEqual(decode_scope(percent_scope)["user_id"], "a%2Bb")
        self.assertEqual(dict(parse_qsl(plus_scope))["user_id"], "a b")
        self.assertEqual(unquote_plus("a+b"), "a b")
        self.assertEqual(unquote(unquote(percent_scope.split("=", 1)[1])), "a+b")

    def test_decode_before_split_invents_fields(self):
        scope = build_scope({"user_id": "alice&run_id=r2"})
        wrong = dict(part.split("=", 1) for part in unquote(scope).split("&"))
        self.assertEqual(wrong, {"user_id": "alice", "run_id": "r2"})
        self.assertFalse(matches(scope, {"user_id": "alice"}))
        self.assertTrue(matches(scope, {"user_id": "alice&run_id=r2"}))

    def test_raw_value_like_can_exclude_a_true_match(self):
        fields = {"user_id": "a&b", "run_id": "r1"}
        seed(self.db, [fields])
        naive = self.db.connection.execute(
            "SELECT session_scope FROM messages WHERE session_scope LIKE ?", ("%user_id=a&b%",)
        ).fetchall()
        self.assertEqual(naive, [])
        self.assertEqual(prefilter_scopes(self.db.connection, {"user_id": "a&b"}), [build_scope(fields)])

    def test_dict_equality_would_repeat_partial_scope_failure(self):
        scope = build_scope({"user_id": "alice", "run_id": "r1"})
        filters = {"user_id": "alice"}
        self.assertNotEqual(decode_scope(scope), filters)
        self.assertTrue(matches(scope, filters))

    def test_empty_or_invalid_filter_never_changes_rows(self):
        seed(self.db)
        before = remaining(self.db)
        for bad in [{}, {"user_id": ""}, {"unknown": "alice"}, {"user_id": None}, "user_id=alice"]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    reference_delete(self.db, bad)
                self.assertEqual(before, remaining(self.db))

    def test_threaded_storage_call_preserves_unrelated_rows(self):
        seed(self.db)
        filters = {"user_id": "alice", "run_id": "r1"}
        expected = {build_scope(row) for row in SCOPES if not oracle(row, filters)}
        asyncio.run(asyncio.to_thread(reference_delete, self.db, filters))
        self.assertEqual(remaining(self.db), expected)

    def test_injected_delete_failure_leaves_fixture_intact(self):
        records = [{"user_id": "alice", "run_id": "r1"}, {"user_id": "alice", "run_id": "r2"}]
        seed(self.db, records)
        self.db.connection.execute(
            "CREATE TRIGGER refuse_r2 BEFORE DELETE ON messages WHEN OLD.session_scope = "
            "'run_id=r2&user_id=alice' BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END"
        )
        self.db.connection.commit()
        before = remaining(self.db)
        with self.assertRaises(sqlite3.IntegrityError):
            reference_delete(self.db, {"user_id": "alice"})
        self.assertEqual(remaining(self.db), before)
        self.assertEqual(self.db.connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0], 4)


def main():
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ScopeReview))
    report = {
        "upstream_commit": PIN,
        "upstream_blobs": SOURCE_BLOBS,
        "python": platform.python_version(),
        "sqlite": sqlite3.sqlite_version,
        "test_methods": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skips": len(result.skipped),
        "synthetic_scope_count": len(SCOPES),
        "synthetic_filter_count": len(FILTERS),
        "scope_filter_comparisons_per_matrix": len(SCOPES) * len(FILTERS),
        "scope": "Unmodified upstream SQLite storage and selected canonical builder; review-only deletion helper",
        "not_executed": ["Memory/AsyncMemory public APIs", "vector stores", "LLM/embeddings", "network",
                         "concurrent cross-process writes", "legacy noncanonical scope formats", "performance benchmark"],
    }
    (ROOT / "RESULTS.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
