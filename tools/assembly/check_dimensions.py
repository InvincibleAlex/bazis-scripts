import copy
import tempfile
import unittest
from pathlib import Path
from export_dimensions import holes_for,milling_for,write_dimensions
from pypdf import PdfReader

def plate():
    corners=[[0,10],[100,10],[100,16],[0,16]]
    def line(a,b):return {'type':'line','start':dict(x=a[0],y=a[1]),'end':dict(x=b[0],y=b[1])}
    profile=[[10,0],[16,0],[16,5],[10,5]]
    p={'id':'p','uid':1,'designation':'TEST','name':'Placă','material':'PAL','width':100,'height':60,'thickness':18,
       'frame':{'origin':[1000,0,0],'axes':[[1,0,0],[0,1,0],[0,0,1]]},
       'local_bounds':{'min':{'x':0,'y':0},'max':{'x':100,'y':60}},
       'native_contour':{'complete':True,'elements':[line(a,b) for a,b in zip([[0,0],[100,0],[100,60],[0,60]],[[100,0],[100,60],[0,60],[0,0]])]},
       'edges':[[[1000+x,y,z],[1000+x,y,z+1]] for x,y in corners for z in [0,5]],'geometry_source':'BAZIS Edges.GVertices',
       'holes':[{'coordinate_space_verified':True,'panel_uid':1,'position_global_mm':[1020,30,18],'direction_global':[0,0,-1],'diameter_mm':5,'depth_mm':12}],
       'machining':{'cuts':[{'properties':{'Name':'Canal'},'params':{'Depth':5,'Width':6,'Offset':10},'trajectory':{'elements':[line([0,0],[100,0])]},'section':{'elements':[line(profile[i],profile[(i+1)%4]) for i in range(4)]}}]}}
    return p

class Dimensions(unittest.TestCase):
    def test_hole_coordinates_use_panel_frame_and_datum(self):
        h=holes_for(plate(),[0,0])[0];self.assertEqual((h['x'],h['y'],h['z'],h['face']),(20,30,18,'Zmax'))
    def test_rectangular_groove_is_confirmed_against_native_geometry(self):
        cut=milling_for(plate(),[0,0])[0];self.assertTrue(cut['verified_rectangle']);self.assertEqual((cut['x'],cut['y'],cut['length'],cut['width'],cut['profile_depth']),(0,10,100,6,5))
    def test_finite_groove_start_and_length(self):
        p=plate();p['machining']['cuts'][0]['trajectory']['elements'][0].update(start={'x':0,'y':20},end={'x':0,'y':45})
        corners=[[-10,20],[-10,45],[-16,45],[-16,20]]
        p['edges']=[[[1000+x,y,0],[1000+x,y,5]] for x,y in corners]
        cut=milling_for(p,[-20,0])[0]
        self.assertTrue(cut['verified_rectangle']);self.assertEqual((cut['x'],cut['y'],cut['length']),(4,20,25))
    def test_hole_on_back_face_and_missing_association(self):
        p=plate();p['holes'][0]['direction_global']=[0,0,1];self.assertEqual(holes_for(p,[0,0])[0]['face'],'Zmin')
        p['holes'][0]['coordinate_space_verified']=False
        with self.assertRaises(ValueError):holes_for(p,[0,0])
    def test_unconfirmed_footprint_is_not_drawn_as_confirmed(self):
        p=plate();p['edges']=[];self.assertFalse(milling_for(p,[0,0])[0]['verified_rectangle'])
    def test_drawing_dimensions_merge_numeric_noise_only(self):
        from export_dimensions import dimension_positions
        self.assertEqual(dimension_positions([3,3.000001,66.999,67,93]),[3,67,93])
        self.assertEqual(dimension_positions([41.343,41.343001,41.4]),[41.3430005,41.4])

    def test_pdf_contains_dimensions_and_never_hardware(self):
        p=plate();before=copy.deepcopy(p)
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'test.pdf';receipt=write_dimensions({'panels':[p],'hardware':[{'name':'HIDDEN HARDWARE'}]},out)
            text='\n'.join(x.extract_text() for x in PdfReader(out).pages)
            self.assertEqual(receipt,{'pages':1,'holes':1,'panels':1,'cuts':1})
            self.assertIn('Xmin=0',text);self.assertIn('Ymin=10',text);self.assertIn('L=100',text);self.assertNotIn('HIDDEN HARDWARE',text)
        self.assertEqual(p,before)

if __name__=='__main__':unittest.main()
