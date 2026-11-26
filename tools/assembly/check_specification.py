import copy
import tempfile
import unittest
from pathlib import Path
from pypdf import PdfReader
from check_dimension_sheets import example
from specification import specification_rows, write_specification, prepend_specification


class Specification(unittest.TestCase):
    def test_native_sides_counts_and_natural_order(self):
        a=example(); a.update(designation='00.10',name='Raft')
        b=copy.deepcopy(a); b['designation']='00.2'
        rows,bands,hardware=specification_rows({'panels':[a,b,b], 'hardware':[{'name':'Șurub','article':'123'}]*3})
        self.assertEqual([r[0] for r in rows],['00.2','00.10'])
        self.assertEqual(rows[0][2],'2')
        for side in ('Sus','Jos','Stânga','Dreapta'): self.assertIn(side+': 1',rows[0][6])
        self.assertEqual(len(bands),1)
        self.assertEqual(hardware[0][-1],'3')

    def test_pagination_repeats_headers_without_shrinking_and_shifts_contexts(self):
        panels=[]
        for i in range(65):
            p=example(); p.update(designation=f'00.{i}',name='Raft cu denumire lungă')
            panels.append(p)
        report={'panels':panels,'hardware':[]}
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'spec.pdf'; count=write_specification(report,out)
            pages=PdfReader(out).pages
            self.assertGreater(count,1)
            self.assertIn('Cod',pages[1].extract_text())
            text='\n'.join(p.extract_text() for p in pages)
            for i in range(65): self.assertIn(f'00.{i}\n',text)
            plan={'cartus_contexts':{1:{'corp':'Corp'}}}
            added=prepend_specification(report,out,plan)
            self.assertEqual(plan['cartus_contexts'][added+1],{'corp':'Corp'})
            self.assertEqual(len(PdfReader(out).pages),count+added)


if __name__=='__main__': unittest.main()
