import unittest,copy,tempfile
from pathlib import Path
from pypdf import PdfReader
from reportlab.lib.units import mm
from check_dimension_sheets import example
from dimension_sheets import write_sheets,native_bands
from dimension_page_layout import nearest_dimension_sides,dimension_envelope,flow_coordinate_tables,fit_view_regions,grouped_coordinates,DIMENSION_START,DIMENSION_STEP,PADDING

class PageLayout(unittest.TestCase):
    def test_holes_at_top_and_right_get_dimensions_on_their_own_edges(self):
        holes=[{'position':[872,430],'color':'fuchsia'},{'position':[912,430],'color':'fuchsia'},
               {'position':[93,0],'color':'fuchsia'},{'position':[1327,25],'color':'fuchsia'}]
        sides=nearest_dimension_sides(holes,[],lambda p:p,1327,430,'red')
        self.assertEqual([entry[0] for entry in sides['top']],[872,912])
        self.assertNotIn(872,[entry[0] for entry in sides['bottom']])
        self.assertEqual([entry[0] for entry in sides['right']],[25])
    def test_overall_dimensions_are_outside_all_rails(self):
        sides={'bottom':[(93,'f'),(349,'f'),(451,'r'),(872,'f'),(912,'f')],'top':[],'left':[(43,'f'),(68,'f')],'right':[]}
        envelope=dimension_envelope(sides,[],[])
        self.assertGreater(envelope['overall']['bottom'],DIMENSION_START+4*DIMENSION_STEP)
        self.assertGreater(envelope['overall']['left'],DIMENSION_START+DIMENSION_STEP)
        self.assertGreater(DIMENSION_STEP,9)
    def test_table_overflow_uses_columns_at_the_same_font_and_row_height(self):
        rows=[[str(i)] for i in range(100)]
        columns=flow_coordinate_tables([{'title':'Face 1','rows':rows,'colors':['blue']*100}],500,30,lambda rows,title:100)
        self.assertGreater(len(columns),1)
        self.assertEqual([row for col in columns for block in col['chunks'] for row in block['rows']],rows)
        for col in columns:
            for block in col['chunks']:
                self.assertEqual(block['height'],30+10*(len(block['rows'])+1))
                self.assertGreaterEqual(block['top']-block['height'],30)
    def test_unequal_annotation_counts_share_space_without_wasting_half_a_page(self):
        views=[{'width':1327,'height':430,'envelope':{'margins':dict(left=50,right=50,top=30,bottom=70)}},
               {'width':1327,'height':430,'envelope':{'margins':dict(left=100,right=100,top=130,bottom=140)}}]
        result=fit_view_regions((30,100,950,800),views)
        self.assertAlmostEqual(result[0]['scale'],result[1]['scale'])
        self.assertGreater(result[0]['scale'],.3)
        for view,placed in zip(views,result):
            m=view['envelope']['margins'];l,b,r,t=placed['bounds']
            self.assertGreaterEqual(placed['left']-m['left'],l-.0001)
            self.assertLessEqual(placed['left']+view['width']*placed['scale']+m['right'],r+.0001)
            self.assertGreaterEqual(placed['bottom']-m['bottom'],b-.0001)
            self.assertLessEqual(placed['bottom']+view['height']*placed['scale']+m['top'],t+.0001)
        self.assertAlmostEqual(result[0]['bounds'][1]-result[1]['bounds'][3],PADDING)
    def test_banding_numbers_follow_type_and_preserve_edge_association(self):
        p=example();bands=native_bands(p)
        self.assertEqual([b['tag'] for b in bands],['1','1','1','1'])
        self.assertEqual([b['element'] for b in bands],[0,1,2,3])
        p['module_comparison']['bands'][1]['Thickness']=.3
        self.assertEqual([b['tag'] for b in native_bands(p)],['1','2','1','1'])
    def test_empty_tables_and_captions_are_absent(self):
        p=example();p['holes']=[];p['module_comparison']['bands']=[]
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'sheet.pdf';write_sheets({'panels':[p]},out)
            text=PdfReader(out).pages[0].extract_text()
            self.assertNotIn('Canturi',text);self.assertNotIn('Găuri —',text)
            self.assertNotIn('Face 1',text);self.assertNotIn('Face 2',text)
            self.assertNotIn('Adâncime',text)
    def test_band_table_bottom_padding_and_origin_attached_to_table_corner(self):
        from unittest.mock import patch
        import dimension_sheets as sheets
        actual=sheets.table;tables=[]
        def record(*args,**kwargs):
            end=actual(*args,**kwargs);tables.append((args[1],end,args[4]));return end
        with tempfile.TemporaryDirectory() as temp,patch('dimension_sheets.table',side_effect=record),patch('dimension_sheets.draw_axes') as axes:
            write_sheets({'panels':[example()]},Path(temp)/'sheet.pdf')
            hole_tables=[item for item in tables if item[2][0]=='Nr.']
            band_tables=[item for item in tables if item[2][0]=='Reper']
            self.assertAlmostEqual(band_tables[0][1],10*mm)
            self.assertEqual(len(axes.call_args_list),len(hole_tables))
            for call,(x,end,_) in zip(axes.call_args_list,hole_tables):
                self.assertAlmostEqual(call.args[1],x-2);self.assertAlmostEqual(call.args[2],end-2)

    def test_long_hole_table_never_duplicates_the_board_page(self):
        p=example();p['holes']=p['holes']*12
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'sheet.pdf';receipt=write_sheets({'panels':[p]},out)
            self.assertEqual(receipt['pages'],1)
            page=PdfReader(out).pages[0];text=page.extract_text()
            self.assertIn('G48',text);self.assertNotIn('Face 1 /',text)
            spans=[]
            def visitor(text,cm,tm,font,size):
                if text.strip()=='G48':spans.append(size)
            page.extract_text(visitor_text=visitor)
            self.assertTrue(any(abs(size-6.5)<.001 for size in spans))

if __name__=='__main__':unittest.main()
