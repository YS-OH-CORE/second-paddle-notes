"""Offline publication-state tests. No account, network or release mutation."""
import copy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import publish as p


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.notes = Path(p.__file__).with_name('NOTES.md').read_text(encoding='utf-8')
        self.assets = {name: ('fixture '+name).encode() for name in p.NAMES}
        self.previous = dict(id=1, tag_name='older-version', target_commitish='old', body='original',
                             draft=False, prerelease=True, assets=[])
        self.releases = [copy.deepcopy(self.previous)]
        self.stored = {}
        self.writes = []
        self.main = 'publication-commit'
        self.addCleanup(patch.stopall)
        patch.dict(p.os.environ, GITHUB_REPOSITORY=p.REPO, GITHUB_EVENT_NAME='push',
                   GITHUB_REF='refs/heads/main', GITHUB_SHA=self.main).start()
        patch.object(p, 'api', self.api).start()
        patch.object(p, 'gh', self.gh).start()
        patch.object(p, 'prepare_remote', self.prepare).start()

    def prepare(self, out):
        folder = out/'assets'; folder.mkdir(parents=True)
        for n, b in self.assets.items():
            (folder/n).write_bytes(b)
        return folder

    def api(self, path, *, payload=None, method='GET'):
        if path == 'git/ref/heads/main':
            return {'object': {'sha': self.main}}
        if path == 'releases?per_page=100':
            return copy.deepcopy(self.releases)
        if path == 'releases' and method == 'POST':
            self.writes.append(('create', payload['tag_name']))
            obj = dict(payload, id=2, assets=[], html_url='https://github.com/release/2',
                       upload_url=f'https://uploads.github.com/repos/{p.REPO}/releases/2/assets{{?name,label}}')
            self.releases.append(obj)
            return copy.deepcopy(obj)
        obj = next(r for r in self.releases if r['id'] == int(path.split('/')[-1]))
        if method == 'PATCH':
            self.writes.append(('publish', obj['id']))
            obj.update(payload)
        return copy.deepcopy(obj)

    def gh(self, *args, **kwargs):
        if '--method' in args:
            url = args[2]; name = url.split('?name=')[1]
            raw = Path(args[-1]).read_bytes()
            obj = next(r for r in self.releases if r['id'] == 2)
            aid = 100+len(obj['assets'])
            self.stored[aid] = raw
            obj['assets'].append(dict(id=aid, name=name, state='uploaded', size=len(raw), digest='sha256:'+p.sha(raw)))
            self.writes.append(('upload', name))
            return b'{}'
        return self.stored[int(args[-1].split('/')[-1])]

    def test_publish_then_repeat_without_replacing_assets(self):
        p.publish(self.root/'first')
        self.assertEqual(len(self.writes), 5)
        before = copy.deepcopy(self.writes)
        p.publish(self.root/'second')
        self.assertEqual(self.writes, before)
        self.assertEqual(self.releases[0], self.previous)

    def test_existing_conflicting_notes_are_not_modified(self):
        self.releases.append(dict(id=2, tag_name=p.TAG, target_commitish=p.SOURCE,
                                  body='someone changed this', prerelease=True, draft=True, assets=[]))
        with self.assertRaises(ValueError):
            p.publish(self.root/'attempt')
        self.assertEqual(self.writes, [])

    def test_moved_main_rejected_before_artifact_preparation(self):
        self.main = 'different'
        with self.assertRaises(ValueError):
            p.publish(self.root/'attempt')
        self.assertFalse((self.root/'attempt').exists())
        self.assertEqual(self.writes, [])

    def test_pr_event_cannot_publish(self):
        with patch.dict(p.os.environ, GITHUB_EVENT_NAME='pull_request'):
            with self.assertRaises(ValueError):
                p.publish(self.root/'attempt')
        self.assertEqual(self.writes, [])

    def test_published_incomplete_release_is_not_repaired_silently(self):
        self.releases.append(dict(id=2, tag_name=p.TAG, target_commitish=p.SOURCE,
                                  body=self.notes, prerelease=True, draft=False, assets=[]))
        with self.assertRaises(ValueError):
            p.publish(self.root/'attempt')
        self.assertEqual(self.writes, [])

    def test_foreign_asset_blocks_publication(self):
        self.releases.append(dict(id=2, tag_name=p.TAG, target_commitish=p.SOURCE,
            body=self.notes, prerelease=True, draft=True, assets=[{'name': 'foreign-file'}]))
        with self.assertRaises(ValueError):
            p.publish(self.root/'attempt')
        self.assertEqual(self.writes, [])


if __name__ == '__main__':
    unittest.main()
