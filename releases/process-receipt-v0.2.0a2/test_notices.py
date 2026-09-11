"""Offline legacy-notice checks; no real GitHub writes or credentials."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import publish as p


class NoticeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.writes=[]
        self.items={rid:dict(id=rid,tag_name=tag,target_commitish='retained-source',
            body='Original release notes\n',draft=False,prerelease=True,html_url='public-old',
            assets=[dict(id=rid+1,name='old.whl',size=17,digest='retained-hash',state='uploaded')])
            for rid,tag in p.OLD_RELEASES.items()}
        self.original=copy.deepcopy(self.items)
        self.new=dict(tag_name=p.TAG,target_commitish=p.SOURCE,draft=False)
        self.addCleanup(patch.stopall)
        patch.dict(p.os.environ,GITHUB_REPOSITORY=p.REPO,GITHUB_EVENT_NAME='push',
            GITHUB_REF='refs/heads/main',GITHUB_SHA='main-commit').start()
        patch.object(p,'api',self.api).start()

    def api(self,path,*,payload=None,method='GET'):
        if path=='git/ref/heads/main':return {'object':{'sha':'main-commit'}}
        if path=='releases/tags/'+p.TAG:return copy.deepcopy(self.new)
        rid=int(path.split('/')[-1]);obj=self.items[rid]
        if method=='PATCH':
            self.assertEqual(set(payload),{'body'})
            self.writes.append(rid);obj.update(payload)
        return copy.deepcopy(obj)

    def test_append_once_and_keep_assets_source_and_original_text(self):
        p.notices(self.root/'first')
        self.assertEqual(len(self.writes),2)
        for rid,old in self.original.items():
            self.assertEqual(self.items[rid]['body'],old['body']+p.notice_suffix())
            self.assertEqual({k:v for k,v in self.items[rid].items() if k!='body'},
                             {k:v for k,v in old.items() if k!='body'})
        p.notices(self.root/'second')
        self.assertEqual(len(self.writes),2)

    def test_conflicting_notice_is_not_rewritten(self):
        self.items[next(iter(self.items))]['body']+=p.MARK+' changed text'
        with self.assertRaises(ValueError):p.notices(self.root/'try')
        self.assertEqual(self.writes,[])

    def test_unpublished_correction_blocks_notices(self):
        self.new['draft']=True
        with self.assertRaises(ValueError):p.notices(self.root/'try')
        self.assertEqual(self.writes,[])

    def test_wrong_corrective_source_blocks_notices(self):
        self.new['target_commitish']='different-source'
        with self.assertRaises(ValueError):p.notices(self.root/'try')
        self.assertEqual(self.writes,[])

    def test_wrong_old_tag_is_left_untouched(self):
        self.items[next(iter(self.items))]['tag_name']='unrelated-release'
        with self.assertRaises(ValueError):p.notices(self.root/'try')
        self.assertEqual(self.writes,[])

    def test_pr_event_cannot_edit_notices(self):
        with patch.dict(p.os.environ,GITHUB_EVENT_NAME='pull_request'):
            with self.assertRaises(ValueError):p.notices(self.root/'try')
        self.assertEqual(self.writes,[])


if __name__=='__main__':unittest.main()
