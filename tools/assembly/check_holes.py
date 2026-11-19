import copy
import math
import unittest
from holes import bore_edges,add_hole_edges


class HoleChecks(unittest.TestCase):
    def hole(self):return dict(source='BAZIS NewHoleDrilling',diameter_mm=5,depth_mm=14,position_global_mm=[10,20,30],direction_global=[0,0,1],panel_uid=7,coordinate_space_verified=True)
    def test_native_diameter_and_depth_are_not_screw_dimensions(self):
        hole=self.hole();before=copy.deepcopy(hole);edges=bore_edges(hole)
        self.assertEqual(len(edges),64)
        for i,edge in enumerate(edges):
            for p in edge:
                self.assertAlmostEqual(math.hypot(p[0]-10,p[1]-20),2.5)
                self.assertAlmostEqual(p[2],30 if i<32 else 44)
        self.assertEqual(hole,before)
    def test_panel_links_and_verified_coordinates_are_required(self):
        panel=dict(uid=7,bounds={'min':[0,0,0],'max':[100,100,18]},edges=[],holes=[self.hole()])
        report={'panels':[panel]};add_hole_edges(report)
        self.assertEqual(panel['holes_drawn'],1);self.assertEqual(len(panel['edges']),76)
        add_hole_edges(report);self.assertEqual(len(panel['edges']),76)
        for key,value in [('panel_uid',99),('coordinate_space_verified',False)]:
            p=copy.deepcopy(panel);p.pop('native_hole_edges_added');p['edges']=[];p['holes'][0][key]=value
            add_hole_edges({'panels':[p]});self.assertEqual(p['holes_drawn'],0)
    def test_untrusted_or_invalid_hole_is_not_reconstructed(self):
        h=self.hole();h['source']='bounds inference';self.assertEqual(bore_edges(h),[])
        h=self.hole();h['diameter_mm']=0;self.assertEqual(bore_edges(h),[])


if __name__=='__main__':unittest.main()
