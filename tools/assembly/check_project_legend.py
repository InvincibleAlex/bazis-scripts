import copy,tempfile,unittest
from pathlib import Path
from pypdf import PdfReader
from check_dimensions import plate
from project_legend import project_sections,write_project_legend


class ProjectLegend(unittest.TestCase):
    def test_native_profiles_deduplicate_and_keep_names(self):
        p=plate();p['machining']['cuts'][0]['properties']={'Name':'Freză LED 6 × 5'}
        report={'panels':[p,copy.deepcopy(p)]};before=copy.deepcopy(report)
        entries=project_sections(report)
        self.assertEqual(len(entries),1)
        self.assertEqual(entries[0]['name'],'Freză LED 6 × 5')
        self.assertTrue(entries[0]['profile'])
        self.assertEqual(report,before)

    def test_legend_and_all_profiles_continue(self):
        p=plate();source=p['machining']['cuts'][0]
        p['machining']['cuts']=[]
        for i in range(15):
            cut=copy.deepcopy(source);cut['properties']={'Name':f'Frezare profil {i:02}'};p['machining']['cuts'].append(cut)
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'legend.pdf';count=write_project_legend({'panels':[p]},out)
            reader=PdfReader(out);self.assertGreater(count,1)
            text='\n'.join(page.extract_text() for page in reader.pages)
            for i in range(15):self.assertIn(f'Frezare profil {i:02}',text)
            for label in ('Albastru','Roșu','Fuchsia','Maro','Gri punctat'):self.assertIn(label,text)


if __name__=='__main__':unittest.main()
