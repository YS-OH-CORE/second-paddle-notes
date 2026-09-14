"""Synthetic local effects only. A receipt and its label share one SQLite commit.

This is a teaching fixture, not an authorization service or a transaction around
an arbitrary remote API. No SDK import is required by this module.
"""
from __future__ import annotations
from contextlib import closing
import json
from pathlib import Path
import secrets
import sqlite3

KEY = 'confirm-draft'
NOTE = '  원래 답\n    keep whitespace\n'
MODES = ('naive', 'closed_guard', 'receipt')
ARGS = {'label': 'draft-1'}


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def terminal(text: str, error: bool = False) -> dict:
    return {'content': [{'type': 'text', 'text': text}], 'isError': error}


class ReceiptStore:
    def __init__(self, path: Path, mode: str):
        if mode not in MODES:
            raise ValueError('UNKNOWN_MODE')
        self.path, self.mode = path, mode
        with closing(sqlite3.connect(path)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS config (mode TEXT NOT NULL)')
            modes = db.execute('SELECT mode FROM config').fetchall()
            if not modes:
                db.execute('INSERT INTO config VALUES (?)', (mode,))
            elif modes != [(mode,)]:
                raise ValueError('STORE_MODE_CHANGED')
            db.execute('CREATE TABLE IF NOT EXISTS rounds (token TEXT PRIMARY KEY, arguments TEXT, binding TEXT, result TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS effects (id INTEGER PRIMARY KEY, token TEXT, label TEXT)')

    def issue(self, arguments: dict) -> str:
        token = 'fixture-' + secrets.token_hex(16)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('INSERT INTO rounds VALUES (?,?,NULL,NULL)', (token, canonical(arguments)))
        return token

    def complete(self, name: str, arguments: dict, token: str, answers: dict) -> tuple[dict, str]:
        binding = canonical({'name': name, 'arguments': arguments, 'answers': answers})
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT arguments,binding,result FROM rounds WHERE token=?', (token,)).fetchone()
            if row is None:
                return terminal('UNKNOWN_ROUND', True), 'unknown'
            if name != 'preview' or canonical(arguments) != row[0]:
                return terminal('REQUEST_BINDING_DIFFER', True), 'mismatch'
            if row[1] is not None and binding != row[1]:
                return terminal('REQUEST_BINDING_DIFFER', True), 'mismatch'
            if row[1] is not None and self.mode == 'closed_guard':
                return terminal('ROUND_ALREADY_CLOSED', True), 'closed'
            if row[1] is not None and self.mode == 'receipt':
                if row[2] is None:
                    raise ValueError('RECEIPT_MISSING')
                return json.loads(row[2]), 'receipt_replayed'
            if set(answers) != {KEY}:
                return terminal('ANSWER_KEYS_DIFFER', True), 'invalid'
            answer = answers[KEY]
            if not isinstance(answer, dict) or set(answer) != {'action', 'content'}:
                return terminal('ANSWER_SHAPE', True), 'invalid'
            content = answer['content']
            if answer['action'] != 'accept' or not isinstance(content, dict) or set(content) != {'yes', 'note'}:
                return terminal('ANSWER_SHAPE', True), 'invalid'
            if content['yes'] is not True or not isinstance(content['note'], str):
                return terminal('ANSWER_CONTENT', True), 'invalid'
            effect = db.execute('INSERT INTO effects(token,label) VALUES (?,?)', (token, arguments['label']))
            result = terminal('previewed:' + arguments['label'])
            result['structuredContent'] = {'effect_id': effect.lastrowid, 'label': arguments['label']}
            # Deliberate controls: naive re-applies; guard refuses but lacks a result.
            db.execute('UPDATE rounds SET binding=?,result=? WHERE token=?',
                       (binding, canonical(result) if self.mode == 'receipt' else None, token))
            return result, 'effect_committed'

    def snapshot(self) -> dict:
        with closing(sqlite3.connect(self.path)) as db:
            return {'effects': [list(r) for r in db.execute('SELECT id,token,label FROM effects ORDER BY id')],
                    'rounds': [list(r) for r in db.execute('SELECT token,arguments,binding,result FROM rounds ORDER BY rowid')]}
