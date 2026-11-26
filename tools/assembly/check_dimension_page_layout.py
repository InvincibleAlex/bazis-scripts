import unittest,copy,tempfile
from pathlib import Path
from pypdf import PdfReader
from reportlab.lib.units import mm
from check_dimension_sheets import example
from dimension_sheets import write_sheets,native_bands
from dimension_page_layout import nearest_dimension_sides,dimension_envelope,flow_coordinate_tables,fit_view_regions,grouped_coordinates,DIMENSION_START,DIMENSION_STEP,PADDING

class PageLayout(unittest.TestCase):
    def test_multi_notch_contour_has_one_chain_rail_and_one_overall(self):
        from dimension_sheets import CONTOUR,baseline_dimensions
        from unittest.mock import patch,MagicMock
        points=[[0,0],[412,0],[412,2104],[0,2104],[0,1750],[206,1750],[206,1732],[0,1732],[0,1390],[206,1390],[206,1372],[0,1372]]
        sides=nearest_dimension_sides([],points,lambda p:p,412,2104,CONTOUR)
        self.assertFalse(any(src=='contour' for entries in sides.values() for _,_,src in entries))
        entries=sides['left'];self.assertGreater(len(entries),3)
        with patch('dimension_sheets.dimension') as draw:
            baseline_dimensions(MagicMock(),lambda p:p,entries,1,0,0,'left',412,2104)
            self.assertEqual(len({call.args[3] for call in draw.call_args_list}),1)
            self.assertTrue(all(call.kwargs['color']==CONTOUR for call in draw.call_args_list))
            self.assertEqual(sum(float(call.args[4]) for call in draw.call_args_list),2104)
        envelope=dimension_envelope(sides,[],[])
        self.assertEqual(envelope['overall']['left'],DIMENSION_START+DIMENSION_STEP+5)

    def test_shared_coordinates_merge_opposite_colors_but_not_chain_segments(self):
        from dimension_page_layout import merge_opposite_coordinates
        from dimension_sheets import THROUGH,FACE,EDGE,baseline_dimensions
        from unittest.mock import patch,MagicMock
        sides={'bottom':[(663.5,FACE,'hole')],'top':[(663.5,THROUGH,'hole'),(663.5,FACE,'hole')],
               'left':[(43,THROUGH,'hole'),(43,EDGE,'hole')], 'right':[(43,EDGE,'hole')]}
        merge_opposite_coordinates(sides)
        self.assertEqual(sides['bottom'],[]);self.assertEqual(sides['right'],[])
        self.assertEqual(len(sides['top']),2);self.assertEqual(len(sides['left']),2)
        with patch('dimension_sheets.dimension') as draw:
            baseline_dimensions(MagicMock(),lambda p:p,sides['top'],0,0,0,'top',1327,430)
            self.assertEqual(draw.call_count,1)
            self.assertEqual(draw.call_args.kwargs['color'],THROUGH)
            self.assertEqual(draw.call_args.kwargs['secondary_colors'],[FACE])
        # Same printed length is not sufficient to merge different chain spans.
        sides={'bottom':[(18,THROUGH,'step:0')],'top':[(118,THROUGH,'step:100')],'left':[],'right':[]}
        merge_opposite_coordinates(sides)
        self.assertTrue(sides['bottom']);self.assertTrue(sides['top'])

    def test_notch_chain_tracks_rotated_view_and_converts_each_vertex_once(self):
        from dimension_sheets import THROUGH
        from unittest.mock import Mock
        points=[[0,0],[1327,0],[1327,412],[672.5,412],[672.5,206],[654.5,206],[654.5,412],[0,412]]
        for convert,expected in [(lambda p:[p[1],1327-p[0]],'right'),(lambda p:[412-p[1],p[0]],'left')]:
            transform=Mock(side_effect=convert)
            sides=nearest_dimension_sides([],points,transform,412,1327,THROUGH)
            self.assertEqual(transform.call_count,len(points))
            chain=[value-float(source.split(':')[1]) for value,_,source in sides[expected] if source.startswith('step:')]
            self.assertEqual(chain,[654.5,18,654.5])
    def test_empty_contour_does_not_invent_steps(self):
        sides=nearest_dimension_sides([],[],lambda p:p,100,50,None)
        self.assertTrue(all(not entries for entries in sides.values()))

    def test_top_notch_chain_stays_on_top_and_bottom_notch_on_bottom(self):
        from dimension_sheets import THROUGH
        points=[[0,0],[1327,0],[1327,412],[672.5,412],[672.5,206],[654.5,206],[654.5,412],[0,412]]
        for mirrored,side,other in [(False,'top','bottom'),(True,'bottom','top')]:
            shape=[[x,412-y if mirrored else y] for x,y in points]
            sides=nearest_dimension_sides([],shape,lambda p:p,1327,412,THROUGH)
            chain=[v-float(src.split(':')[1]) for v,_,src in sides[side] if src.startswith('step:')]
            self.assertEqual(chain,[654.5,18,654.5])
            self.assertFalse(any(src.startswith('step:') or src=='contour' for _,_,src in sides[other]))

    def test_symmetric_middle_step_uses_chain_without_cumulative_316(self):
        from dimension_sheets import THROUGH
        points=[[0,0],[200,0],[200,298],[400,298],[400,316],[200,316],[200,614],[0,614]]
        sides=nearest_dimension_sides([],points,lambda p:p,400,614,THROUGH)
        entries=sides['left']+sides['right']
        self.assertFalse(any(source=='contour' and value==316 for value,_,source in entries))
        lengths=[value-float(source.split(':')[1]) for value,_,source in entries if source.startswith('step:')]
        self.assertEqual(lengths,[298,18,298])

    def test_shoulders_have_local_lengths_without_duplicate_symmetric_height(self):
        from dimension_sheets import THROUGH,EDGE,baseline_dimensions
        from unittest.mock import patch,MagicMock
        points=[[0,350],[1363,350],[1363,300],[1345,300],[1345,0],[36,0],[36,300],[0,300]]
        holes=[{'position':[36,275],'color':EDGE}]
        sides=nearest_dimension_sides(holes,points,lambda p:p,1363,350,THROUGH)
        heights=[entry for side in ['left','right'] for entry in sides[side] if entry[2]=='contour' and entry[0]==300]
        self.assertEqual(len(heights),0)
        self.assertFalse(any(entry[2]=='contour' and entry[0]==300 for entry in sides['right']))
        self.assertIn((350,THROUGH,'step:300'),sides['left'])
        self.assertIn((1363,THROUGH,'step:1345'),sides['bottom'])
        c=MagicMock()
        with patch('dimension_sheets.dimension') as draw:
            baseline_dimensions(c,lambda p:p,sides['top'],0,0,0,'top',1363,350)
            shared=next(call for call in draw.call_args_list if call.args[4]=='36')
            self.assertEqual(shared.kwargs['color'],THROUGH)
            self.assertEqual(shared.kwargs['secondary_colors'],[EDGE])
        with patch('dimension_sheets.dimension') as draw:
            baseline_dimensions(c,lambda p:p,sides['left'],1,0,0,'left',1363,350)
            step=next(call for call in draw.call_args_list if call.args[4]=='50')
            self.assertEqual(step.args[1],[0,300]);self.assertEqual(step.args[2],[0,350])

    def test_secondary_color_lines_follow_actual_label_center_and_rotation(self):
        from io import BytesIO
        from reportlab.pdfgen.canvas import Canvas
        from dimension_annotations import AnnotationLayout
        from export_dimensions import dimension
        from reportlab.lib.colors import red,blue
        for vertical in [False,True]:
            c=Canvas(BytesIO());c.annotation_layout=AnnotationLayout((0,0,600,600))
            a=[100,100];b=[100,400] if vertical else [400,100]
            dimension(c,a,b,80,'387',vertical,color=red,secondary_colors=[blue])
            record=c.annotation_layout.underlines[0]
            midpoint=[(record['start'][i]+record['end'][i])/2 for i in range(2)]
            if vertical:
                self.assertAlmostEqual(midpoint[1],record['center'][1])
                self.assertAlmostEqual(record['start'][0],record['end'][0])
                self.assertGreater(midpoint[0],record['center'][0])
                self.assertGreater(midpoint[0],80)  # Beyond the main vertical dimension rail.
            else:
                self.assertAlmostEqual(midpoint[0],record['center'][0])
                self.assertAlmostEqual(record['start'][1],record['end'][1])
                self.assertLess(midpoint[1],record['center'][1])
                self.assertLess(midpoint[1],80)  # Below the main horizontal dimension rail.
    def test_secondary_line_follows_label_when_collision_moves_it(self):
        from io import BytesIO
        from reportlab.pdfgen.canvas import Canvas
        from dimension_annotations import AnnotationLayout
        from export_dimensions import dimension
        from reportlab.lib.colors import red,blue
        c=Canvas(BytesIO());layout=AnnotationLayout((0,0,600,600));c.annotation_layout=layout
        layout.reserve((210,80,290,105))
        dimension(c,[100,100],[400,100],80,'451',color=red,secondary_colors=[blue])
        record=layout.underlines[0]
        self.assertNotEqual(record['center'],(250,86))
        self.assertAlmostEqual((record['start'][0]+record['end'][0])/2,record['center'][0])
    def test_plan_groove_width_is_only_in_section_when_detail_exists(self):
        from io import BytesIO
        from reportlab.pdfgen.canvas import Canvas
        from unittest.mock import patch
        from dimension_sheets import draw_milling
        cut={'tag':'F01','verified_rectangle':True,'face':'Zmax','corners':[[0,12],[100,12],[100,18],[0,18]],'length':100,'width':6,'profile_depth':5,'section_detail':{'width':6}}
        with patch('dimension_sheets.dimension') as draw:
            draw_milling(Canvas(BytesIO()),[cut],False,lambda p:p,lambda p:p,100,60,0,0,60,100)
            self.assertEqual([call.args[4] for call in draw.call_args_list],['12'])
        cut['section_detail']=None
        with patch('dimension_sheets.dimension') as draw:
            draw_milling(Canvas(BytesIO()),[cut],False,lambda p:p,lambda p:p,100,60,0,0,60,100)
            self.assertIn('l 6',[call.args[4] for call in draw.call_args_list])

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
            self.assertNotIn('Canturi',text);self.assertNotIn('Găuri -',text)
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
