import importlib.util,json,unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('egger_textures',Path(__file__).parents[1]/'tools/materials/egger_textures.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class OfficialTextures(unittest.TestCase):
    def page(self,items):
        return '<egger-decorimagedownloads><script type="application/json">'+json.dumps({'data':{'downloads':{'imageDownloadItems':items}}})+'</script></egger-decorimagedownloads>'

    def item(self,**updates):
        row={'code':'U705 ST9','fileType':'Raport','name':'Use for CAD programmes','anonymous':True,
             'awsSignatureRequired':False,'url':{'url':'https://cdn.egger.com/img/pim/example/original.png'}}
        row.update(updates);return row

    def test_exact_cad_download_ignores_photographs_and_wrong_finish(self):
        self.assertEqual(m.cad_download(self.page([self.item(code='U705 ST12'),self.item()]),'U705','ST9'),self.item()['url']['url'])

    def test_ambiguous_private_or_wrong_finish_download_is_rejected(self):
        for items in ([self.item(),self.item()],[self.item(anonymous=False)],[self.item(awsSignatureRequired=True)],[self.item(code='U705 ST12')]):
            with self.assertRaises(ValueError):m.cad_download(self.page(items),'U705','ST9')

    def test_foreign_or_insecure_download_is_rejected(self):
        for url in ('http://cdn.egger.com/a.png','https://egger.com.example.org/a.png','https://example.org/a.png'):
            with self.assertRaises(ValueError):m.official_url(url)


if __name__=='__main__':unittest.main()
