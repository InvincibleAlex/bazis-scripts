import copy,tempfile,unittest
from pathlib import Path
from pypdf import PdfReader
from check_dimensions import plate
from dimension_sheets import view_transform,classified_holes,face_holes,contour_data,native_bands,grain_vector,write_sheets,FACE,THROUGH,EDGE

def line(a,b):return {'type':'line','start':a,'end':b}
def rectangle(x,y,w,h):
    points=[[x,y],[x+w,y],[x+w,y+h],[x,y+h]]
    return {'complete':True,'elements':[line(points[i],points[(i+1)%4]) for i in range(4)]}

def example():
    p=plate();p.update(width=600,height=300,label=36)
    p['local_bounds']={'min':[0,0],'max':[600,300]};p['native_contour']=rectangle(0,0,600,300)
    hole=rectangle(140,90,100,80)
    circle={'elements':[{'type':'circle','center':[360,160],'radius':25}]}
    p['contour_tree']={'geometry':p['native_contour'],'children':[{'geometry':hole,'children':[]},{'geometry':circle,'children':[]}]}
    p['appearance']={'orientation_name':'Horizontal','orientation_enum':{'None':0,'Horizontal':1,'Vertical':2},'properties':{'TextureOrientation':1}}
    p['module_comparison']={'bands':[{'ElemIndex':i,'Material':'Cant ABS REHAU Negru, 23 X 2 mm','Sign':'2X23_Negru_0190_PE','Thickness':1.5} for i in range(4)]}
    p['holes']=[]
    for x,y,z,d,depth in [(25,30,18,[0,0,-1],12),(60,50,0,[0,0,1],12),(95,70,18,[0,0,-1],18),(0,120,9,[1,0,0],30)]:
        p['holes'].append({'coordinate_space_verified':True,'panel_uid':1,'position_global_mm':[1000+x,y,z],'direction_global':d,'diameter_mm':8,'depth_mm':depth})
    p['machining']['cuts']=[]
    return p

class Sheets(unittest.TestCase):
    def test_table_width_follows_text_instead_of_page(self):
        from dimension_sheets import content_column_widths
        from reportlab.pdfbase import pdfmetrics
        headers=['Nr.','Adâncime'];rows=[['1','12']]
        widths=content_column_widths(headers,rows,6.5,700)
        self.assertLess(sum(widths),100)
        self.assertGreaterEqual(widths[1],pdfmetrics.stringWidth('Adâncime','Body',6.5)+8)

    def test_baseline_dimensions_start_at_one_origin_and_merge_duplicates(self):
        from unittest.mock import Mock,patch
        from dimension_sheets import baseline_dimensions
        for axis in [0,1]:
            with patch('dimension_sheets.dimension') as draw:
                baseline_dimensions(Mock(),lambda p:[200+p[0],200+p[1]],[(75,FACE),(75.001,FACE),(100,EDGE)],axis,200,200)
                self.assertEqual(draw.call_count,2)
                calls=draw.call_args_list
                self.assertEqual(calls[0].args[1],[200,200]);self.assertEqual(calls[1].args[1],[200,200])
                self.assertEqual(calls[0].args[4],'75');self.assertEqual(calls[1].args[4],'100')
                self.assertLess(calls[1].args[3],calls[0].args[3])

    def test_flip_on_longest_edge_and_view_origin(self):
        f,d,axis=view_transform([10,20],[610,320],True)
        self.assertEqual(axis,'y');self.assertEqual(f([30,50]),[20,270]);self.assertEqual(f([10,320]),[0,0]);self.assertEqual(d([1,2,3]),[1,-2,-3])
        f,d,axis=view_transform([-50,10],[50,610],True)
        self.assertEqual(axis,'x');self.assertEqual(f([-30,40]),[80,30]);self.assertEqual(f([50,10]),[0,0])
    def test_native_holes_split_and_through_coloring(self):
        holes=classified_holes(example(),[0,0])
        self.assertEqual([h['color'] for h in holes],[FACE,FACE,THROUGH,EDGE])
        self.assertEqual([h['tag'] for h in face_holes(holes,False)],['G01','G03','G04'])
        self.assertEqual([h['tag'] for h in face_holes(holes,True)],['G02','G03','G04'])
    def test_nested_contours_deduplicate_outer_and_identify_openings(self):
        loops=contour_data(example());self.assertEqual(len(loops),3);self.assertEqual(sum(l['interior'] for l in loops),2)
    def test_disjoint_exteriors_are_not_openings(self):
        p=example();p['contour_tree']['children'].append({'geometry':rectangle(800,0,100,100),'children':[]})
        self.assertEqual(sum(l['interior'] for l in contour_data(p)),2)
    def test_band_fields_and_grain_are_native(self):
        p=example();self.assertEqual(native_bands(p)[0]['thickness'],1.5);self.assertEqual(native_bands(p)[0]['element'],0)
        self.assertEqual(grain_vector(p),[1,0,0]);self.assertIsNone(grain_vector(plate()))
    def test_two_views_tables_and_source_unchanged(self):
        p=example();before=copy.deepcopy(p)
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'sheet.pdf';receipt=write_sheets({'panels':[p]},out)
            reader=PdfReader(out);text=reader.pages[0].extract_text()
            self.assertEqual(receipt['pages'],1);self.assertIn('Face 1',text);self.assertIn('Face 2',text);self.assertIn('D1',text);self.assertIn('D2',text)
            self.assertIn('2X23_Negru_0190_PE',text);self.assertNotIn('nu este program',text)
            self.assertEqual(float(reader.pages[0].mediabox.width),1191)
        self.assertEqual(p,before)
    def test_continuation_preserves_both_faces(self):
        p=example();p['holes']=p['holes']*8
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'sheet.pdf';receipt=write_sheets({'panels':[p]},out)
            self.assertEqual(receipt['pages'],2)
            for page in PdfReader(out).pages:self.assertIn('Face 2',page.extract_text())

if __name__=='__main__':unittest.main()
