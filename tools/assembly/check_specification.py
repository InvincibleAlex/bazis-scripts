import copy
import tempfile
import unittest
from pathlib import Path
from pypdf import PdfReader
from check_dimension_sheets import example
from specification import specification_rows, write_specification, insert_specification


class Specification(unittest.TestCase):
    def test_native_sides_counts_and_natural_order(self):
        a=example(); a.update(designation='00.10',name='Raft')
        b=copy.deepcopy(a); b['designation']='00.2'
        rows,bands,hardware=specification_rows({'panels':[a,b,b], 'hardware':[{'name':'Șurub','article':'123'}]*3})
        self.assertEqual([r[0] for r in rows],['00.2','00.10'])
        self.assertEqual(rows[0][2],'2')
        self.assertEqual(rows[0][6],'S, J, St, Dr.')
        self.assertEqual(len(bands),1)
        self.assertEqual(hardware[0][-1],'3')

    def test_pagination_repeats_headers_without_shrinking_and_shifts_contexts(self):
        panels=[]
        for i in range(150):
            p=example(); p.update(designation=f'00.{i}',name='Raft cu denumire lungă')
            panels.append(p)
        report={'panels':panels,'hardware':[]}
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'spec.pdf'; count=write_specification(report,out)
            pages=PdfReader(out).pages
            self.assertGreater(count,1)
            self.assertIn('Cod',pages[1].extract_text())
            text='\n'.join(p.extract_text() for p in pages)
            for i in range(150): self.assertIn(f'00.{i}\n',text)
            self.assertGreaterEqual(sum(f'00.{i}\n' in pages[0].extract_text() for i in range(150)),50)
            first_text=pages[0].extract_text()
            plan={'cartus_contexts':{1:{'corp':'Cover'},2:{'corp':'Corp'}},'module_page_ranges':{'m':[2,count]}}
            added=insert_specification(report,out,plan)
            self.assertEqual(plan['cartus_contexts'][added+2],{'corp':'Corp'})
            self.assertEqual(plan['cartus_contexts'][1],{'corp':'Cover'})
            self.assertTrue(plan['cartus_contexts'][2]['_specification'])
            self.assertEqual(plan['module_page_ranges']['m'],[2+added,count+added])
            result=PdfReader(out)
            self.assertEqual(result.pages[0].extract_text(),first_text)
            self.assertEqual(len(result.pages),count+added)


if __name__=='__main__': unittest.main()
