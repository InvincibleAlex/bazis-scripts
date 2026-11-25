import copy,tempfile,unittest
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from pypdf import PdfReader
from check_dimensions import plate
from dimension_sheets import contour_data,milling_for,cross_section,write_sheets,coordinate_table_position
from dimension_sections import section_label

class Sections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):pdfmetrics.registerFont(TTFont('Body','C:/Windows/Fonts/arial.ttf'))
    def test_details_are_top_right_and_share_table_margin(self):
        from dimension_sheets import section_detail_positions
        from dimension_sections import DETAIL_WIDTH
        for count in [1,2,3]:
            positions=section_detail_positions(1191,842,count)
            self.assertAlmostEqual(positions[-1][0]+DETAIL_WIDTH,1191-10*mm)
            self.assertTrue(all(top==760 for _,top in positions))

    def test_native_section_width_depth_thickness_and_side(self):
        p=plate();cut=milling_for(p,[0,0])[0];section=cross_section(p,cut,contour_data(p))
        self.assertEqual((section['width'],section['depth'],section['thickness'],section['face']),(6,5,18,'Zmin'))
        self.assertTrue(section['cropped_left']);self.assertTrue(section['cropped_right'])
    def test_section_rejects_unverified_or_through_profiles(self):
        p=plate();cut=milling_for(p,[0,0])[0]
        cut['verified_rectangle']=False;self.assertIsNone(cross_section(p,cut,contour_data(p)))
        cut['verified_rectangle']=True;cut['through']=True;self.assertIsNone(cross_section(p,cut,contour_data(p)))
    def test_local_material_never_extends_beyond_real_board_edge(self):
        p=plate();cut=milling_for(p,[0,0])[0]
        # Native outer contour stops exactly on the groove's upper footprint edge.
        for e in p['native_contour']['elements']:
            for key in ['start','end']:
                if e[key]['y']==60:e[key]['y']=16
        section=cross_section(p,cut,contour_data(p));self.assertEqual(section['right'],3)
        self.assertFalse(section['cropped_right'])
    def test_coordinate_table_right_padding_tracks_frame(self):
        for width in [842,1191]:
            for frame in [0,15]:
                x,w=coordinate_table_position(width,['Nr.','Adâncime'],[['G01','12']],frame_inset=frame)
                self.assertAlmostEqual(x+w,width-frame-10*mm)
                self.assertLess(w,100)
    def test_section_pdf_has_detail_and_both_matching_markers(self):
        p=plate();before=copy.deepcopy(p)
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'section.pdf';write_sheets({'panels':[p]},out)
            text=PdfReader(out).pages[0].extract_text()
            self.assertIn('A–A',text);self.assertGreaterEqual(text.split().count('A'),2)
            self.assertNotIn('Xmin=',text)
        self.assertEqual(p,before)
    def test_detail_opening_is_up_and_width_is_above_on_both_faces(self):
        from unittest.mock import patch
        from io import BytesIO
        from reportlab.pdfgen.canvas import Canvas
        from dimension_sections import draw_detail
        p=plate();cut=milling_for(p,[0,0])[0];cut['section_detail']=cross_section(p,cut,contour_data(p));cut['section_label']='A'
        for face in ['Zmin','Zmax']:
            cut['section_detail']['face']=face
            with patch('dimension_sections.dimension') as draw:
                draw_detail(Canvas(BytesIO()),cut,100,500)
                width,depth=draw.call_args_list[:2]
                self.assertGreater(width.args[3],width.args[1][1])
                self.assertGreater(depth.args[1][1],depth.args[2][1])

    def test_section_letters_continue_after_z(self):
        self.assertEqual([section_label(i) for i in [0,25,26,27]],['A','Z','AA','AB'])

if __name__=='__main__':unittest.main()
