from pathlib import Path
import tempfile
import unittest
from pypdf import PdfReader
from reportlab.lib.units import mm
from check_dimension_sheets import example
from dimension_sheets import write_sheets
from titleblock import bindings,layout,frame_pdf,content_transform


def template():
    def cell(col,text,span=1,rows=1):return {'col':col,'colSpan':span,'rowSpan':rows,'text':text,'font':2.2,'align':'left'}
    return {'schema':2,'page':{'width':210,'height':297,'margins':{'left':15,'right':5,'top':5,'bottom':5}},
        'block':{'width':190,'maxWidth':190,'dynamic':False,'gap':0,'padding':.5,'stroke':.2},'columns':[30,80,80],
        'rows':[{'height':5,'cells':[cell(0,'Firma',1,3),cell(1,'{proiect}',2)]},
            {'height':5,'cells':[cell(1,'{placa}'),cell(2,'{material}')]},
            {'height':5,'cells':[cell(1,'{dimensiuni}'),cell(2,'{pagina} | {client}')]}],
        'parameters':[{'name':'client','value':'Demo, not live data'}],'logo':''}


class TitleBlock(unittest.TestCase):
    def test_landscape_rotates_whole_composition_ccw_inside_frame(self):
        bounds=(40,80,570,820)
        for width,height in [(1191,842),(842,1191)]:
            transform=content_transform(width,height,bounds)
            points=[transform.apply_on(point) for point in [(0,0),(width,0),(width,height),(0,height)]]
            for x,y in points:
                self.assertGreaterEqual(x,bounds[0]-1e-6);self.assertLessEqual(x,bounds[2]+1e-6)
                self.assertGreaterEqual(y,bounds[1]-1e-6);self.assertLessEqual(y,bounds[3]+1e-6)
            if width>height:
                self.assertAlmostEqual(points[0][0],points[1][0]);self.assertGreater(points[1][1],points[0][1])
            else:
                self.assertGreater(points[1][0],points[0][0]);self.assertAlmostEqual(points[1][1],points[0][1])

    def test_template_does_not_change_original_sheet_layout(self):
        report={'panels':[example()]}
        with tempfile.TemporaryDirectory() as temp:
            a=Path(temp)/'original.pdf';b=Path(temp)/'with-context.pdf'
            write_sheets(report,a);write_sheets(dict(report,_titleblock=template()),b)
            original=PdfReader(a).pages[0];with_context=PdfReader(b).pages[0]
            self.assertEqual(original.mediabox,with_context.mediabox)
            self.assertEqual(original.get_contents().operations,with_context.get_contents().operations)

    def test_bindings_use_native_fields_and_separate_manual_values(self):
        p=example();report={'model':r'C:\Work\Proiect.b3d','_cartus_manual':{'client':'Client real','proiectant':'Contributor','verificator':'Contributor'},'_cartus_corp':'Corp 2'}
        values=bindings(report,p)
        self.assertEqual(values['proiect'],'Proiect');self.assertEqual(values['client'],'Client real')
        self.assertEqual(values['proiectant'],'Contributor');self.assertEqual(values['verificator'],'Contributor')
        self.assertEqual(values['dimensiuni'],'600 × 300 × 18 mm');self.assertEqual(values['corp'],'Corp 2')
        self.assertEqual(bindings({'model':'Project.b3d'})['client'],'')

    def test_grid_merged_cells_and_dynamic_height_come_from_template(self):
        t=template();m=layout(t,{'proiect':'Proiect','placa':'P1'})
        self.assertAlmostEqual(m['rows'][0][0]['height'],m['height'])
        self.assertAlmostEqual(m['bounds'][0],15*mm)
        large=layout(t,{'proiect':'Nume proiect foarte lung '*40})
        self.assertGreater(large['height'],m['height'])
        self.assertNotIn('{proiect}',large['rows'][0][1]['text'])

    def test_framing_keeps_entire_existing_landscape_composition(self):
        t=template();r={'model':'Project.b3d','panels':[example()]}
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'layout.pdf';write_sheets(r,out)
            before=PdfReader(out).pages[0];text=before.extract_text()
            self.assertGreater(float(before.mediabox.width),float(before.mediabox.height))
            # The complete old page content remains embedded; framing only adds a transform.
            original=before.get_contents().get_data()
            geometry=[(list(args),op) for args,op in before.get_contents().operations if op in (b'm',b'l',b'c',b're')]
            frame_pdf(out,t,r,{1:bindings(r,r['panels'][0])})
            after=PdfReader(out).pages[0]
            self.assertAlmostEqual(float(after.mediabox.width),210*mm,places=3)
            self.assertAlmostEqual(float(after.mediabox.height),297*mm,places=3)
            self.assertIn('1 / 1',after.extract_text());self.assertNotIn('Demo, not live data',after.extract_text())
            for token in ['Găuri','G01','G02','Canturi']:self.assertEqual(text.count(token),after.extract_text().count(token))
            self.assertEqual(before.get_contents().get_data(),original)
            after_geometry=[(list(args),op) for args,op in after.get_contents().operations if op in (b'm',b'l',b'c',b're')]
            self.assertTrue(any(after_geometry[i:i+len(geometry)]==geometry for i in range(len(after_geometry)-len(geometry)+1)))


if __name__=='__main__':unittest.main()
