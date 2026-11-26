import copy
from io import BytesIO
import unittest
from unittest.mock import MagicMock
from reportlab.pdfgen.canvas import Canvas
from assembly_fonts import register_body_font
from dimension_sheets import hatch_closed_opening
from export_dimensions import dimension


class Finishing(unittest.TestCase):
    def test_only_closed_interior_contours_are_hatched_at_45_degrees(self):
        loop={'interior':True,'points':[[10,10],[40,10],[40,30],[10,30],[10,10]]}
        c=MagicMock();hatch_closed_opening(c,loop,lambda p:p,lambda p:p)
        c.clipPath.assert_called_once();self.assertGreater(c.line.call_count,0)
        for call in c.line.call_args_list:
            x1,y1,x2,y2=call.args;self.assertAlmostEqual(x2-x1,y2-y1)
        for variant in [dict(loop,interior=False),dict(loop,points=loop['points'][:-1])]:
            c=MagicMock();hatch_closed_opening(c,variant,lambda p:p,lambda p:p)
            c.clipPath.assert_not_called();c.line.assert_not_called()

    def test_extension_lines_are_half_opacity_and_overall_is_faded(self):
        register_body_font()
        class RecordingCanvas(Canvas):
            def __init__(self):super().__init__(BytesIO());self.lines=[];self.opacity=1
            def setStrokeAlpha(self,value):self.opacity=value;super().setStrokeAlpha(value)
            def line(self,*args):self.lines.append((args,self.opacity));super().line(*args)
        for vertical in [False,True]:
            for overall in [False,True]:
                c=RecordingCanvas()
                dimension(c,[100,100],[100,200] if vertical else [200,100],80,'100',vertical,overall=overall)
                self.assertEqual([alpha for _,alpha in c.lines[:3]],[.5,.5,.5 if overall else 1])
                if overall:self.assertIn('/gRLs', ''.join(c._code))


if __name__=='__main__':unittest.main()
