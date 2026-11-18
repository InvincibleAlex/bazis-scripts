import copy
import math
import unittest
from hierarchical import transform,in_frame,pack,plate_view,axial_explode,preparation_batches
from export_assembly import project,choose_page

class HierarchyChecks(unittest.TestCase):
    def setUp(self):
        self.panel=dict(id='a',name='Side',label=1,bounds={'min':[10,20,30],'max':[28,620,330]},edges=[])
    def test_display_transforms_never_mutate_original(self):
        before=copy.deepcopy(self.panel)
        moved=transform([self.panel],lambda p:[p[2],p[1],-p[0]])[0]
        self.assertEqual(self.panel,before)
        self.assertEqual(moved['bounds'],{'min':[30,20,-28],'max':[330,620,-10]})
    def test_local_frame_restores_rotated_coordinates(self):
        frame={'origin':[100,0,0],'axes':[[0,0,-1],[0,1,0],[1,0,0]]}
        p=dict(self.panel,bounds={'min':[100,0,-600],'max':[118,300,0]})
        q=in_frame([p],frame)[0]
        self.assertEqual(q['bounds'],{'min':[0,0,0],'max':[600,300,18]})
    def test_twenty_degree_projection(self):
        self.assertAlmostEqual(project([1,0,0])[0],math.cos(math.radians(20)))
        self.assertAlmostEqual(project([0,0,1])[0],math.sin(math.radians(-20)))
    def test_exploded_lineup_keeps_internal_dimensions_and_separates_groups(self):
        groups=pack([('a',[self.panel]),('b',[copy.deepcopy(self.panel)])],100)
        a=groups[0][1][0]['bounds'];b=groups[1][1][0]['bounds']
        self.assertEqual(b['min'][0]-a['max'][0],100)
        self.assertEqual(a['max'][1]-a['min'][1],600)
    def test_plate_display_keeps_fittings_in_same_transform(self):
        fitting=dict(id='f',kind='hardware',bounds={'min':[10,30,40],'max':[20,40,50]},edges=[])
        before=copy.deepcopy([self.panel,fitting]);result=plate_view(self.panel,[fitting])
        self.assertEqual([self.panel,fitting],before)
        self.assertEqual(len(result),2)
    def test_matching_code_alone_defines_one_preparation(self):
        a=dict(self.panel,designation='EXACT');b=dict(self.panel,id='b',designation='EXACT',parent='different',width=123)
        self.assertEqual(len(preparation_batches([a,b])),1)
        self.assertEqual(len(preparation_batches([dict(a,designation=''),dict(b,designation='')])),2)
    def test_axial_motion_has_no_transverse_component(self):
        f=dict(id='f',name='Surub',bounds={'min':[0,0,0],'max':[50,7,7]},edges=[],insertion_axis=[1,1,0])
        q=axial_explode(self.panel,[f])[0];d=q['explosion_offset']
        self.assertAlmostEqual(d[0],d[1]);self.assertEqual(d[2],0)
        moved=transform([f],lambda p:[-p[1]+100,p[0]+50,p[2]])[0]
        self.assertEqual(moved['insertion_axis'],[-1,1,0])
    def test_missing_axis_does_not_cause_arbitrary_displacement(self):
        f=dict(id='f',name='Balama',bounds={'min':[0,0,0],'max':[20,20,20]},edges=[])
        q=axial_explode(self.panel,[f])[0]
        self.assertEqual(q['bounds'],f['bounds']);self.assertNotIn('explosion_offset',q)
    def test_page_orientation_uses_larger_fit(self):
        tall=dict(self.panel,bounds={'min':[0,0,0],'max':[300,2600,18]})
        wide=dict(self.panel,bounds={'min':[0,0,0],'max':[3000,100,18]})
        self.assertEqual(choose_page([tall]),(595,842));self.assertEqual(choose_page([wide]),(842,595))

class VisibilityChecks(unittest.TestCase):
    def test_board_occludes_rear_line_but_not_front_line(self):
        from visibility import DepthMask
        mask=DepthMask((0,0,100,100),lambda p:(p[0],p[1]),1)
        mask.polygon([[0,0,10],[100,0,10],[100,100,10],[0,100,10]])
        self.assertEqual(mask.segments([20,50,0],[80,50,0]),[])
        self.assertTrue(mask.segments([20,50,10],[80,50,10]))

if __name__=='__main__':unittest.main()
