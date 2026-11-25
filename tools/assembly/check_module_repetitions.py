import copy
import tempfile
import unittest
from pathlib import Path
from export_assembly import box_edges
from module_repetitions import find_repetitions


def fixture():
    report={'model':'test.b3d','nodes':[],'panels':[],'hardware':[]};modules=[]
    for i,shift in enumerate((0,1000)):
        root='m'+str(i);pid='p'+str(i)
        frame={'origin':[shift,0,0],'axes':[[1,0,0],[0,1,0],[0,0,1]],'source':'BAZIS ToGlobal'}
        report['nodes'].append({'id':root,'parent':None,'name':'Corp '+str(i),'frame':frame})
        p={'id':pid,'uid':i+1,'parent':root,'ancestors':[root],'name':'Placă','designation':'COD'+str(i),'label':i+1,
            'material':'PAL','width':600,'height':300,'thickness':18,'frame':copy.deepcopy(frame),
            'bounds':{'min':[shift,0,0],'max':[shift+600,300,18]},'warnings':[],
            'geometry_source':'BAZIS Edges.GVertices','machining':{'complete':True,'cuts':[]},
            'holes':[],'drilling_source':'BAZIS NewHoleDrilling','duplicate_signature':None,
            'module_comparison':{'version':1,'complete':True,'bands':[],'layers':[],'texture':{'TextureOrientation':2}}}
        p['edges']=box_edges(p);report['panels'].append(p)
        modules.append({'id':root,'name':'Corp '+str(i),'steps':[{'panel_id':pid,'role':'face','offset_mm':[0,0,0],'instruction':'Așază placa.'}]})
    return report,modules


class ModuleRepetitions(unittest.TestCase):
    def test_translation_and_changed_codes_still_match(self):
        r,m=fixture();d=find_repetitions(r,m)
        self.assertEqual(d['m1']['reference_module_id'],'m0');self.assertEqual(d['m1']['panel_mapping'][0]['reference_label'],1)
    def test_differences_and_missing_evidence_keep_pages(self):
        for field,value in [('material','MDF'),('module_comparison',None),('machining',{'complete':False}),('geometry_source','bounding box')]:
            with self.subTest(field=field):
                r,m=fixture();r['panels'][1][field]=value;self.assertEqual(find_repetitions(r,m),{})
        for feature in ['bands','layers','texture']:
            r,m=fixture();r['panels'][1]['module_comparison'][feature]=['different'];self.assertEqual(find_repetitions(r,m),{})
    def test_numerical_noise_and_reordered_native_edges(self):
        r,m=fixture();r['panels'][1]['width']=600.00000000001
        r['panels'][1]['edges']=[list(reversed(e)) for e in reversed(r['panels'][1]['edges'])]
        self.assertIn('m1',find_repetitions(r,m))
    def test_rigid_rotation_of_whole_module_still_matches(self):
        r,m=fixture();p=r['panels'][1]
        def rotate(v):return [-(v[1]),v[0],v[2]]
        p['edges']=[[rotate(v) for v in e] for e in p['edges']]
        for frame in [r['nodes'][1]['frame'],p['frame']]:
            frame['origin']=rotate(frame['origin']);frame['axes']=[rotate(a) for a in frame['axes']]
        self.assertIn('m1',find_repetitions(r,m))
    def test_mirrored_frame_is_not_suppressed(self):
        r,m=fixture();r['nodes'][1]['frame']['axes'][0]=[-1,0,0];self.assertEqual(find_repetitions(r,m),{})
    def test_different_native_holes_keep_pages(self):
        r,m=fixture();r['panels'][1]['holes']=[{'coordinate_space_verified':True,'position_global_mm':[1010,20,0],'direction_global':[0,0,1],'diameter_mm':5,'depth_mm':12}]
        self.assertEqual(find_repetitions(r,m),{})
    def test_hardware_article_and_links_are_compared(self):
        r,m=fixture()
        for i,shift in enumerate((0,1000)):
            h={'id':'h'+str(i),'name':'Diblu','article':'DL830','ancestors':['m'+str(i)],'bounds':{'min':[shift+10,10,0],'max':[shift+18,18,10]},'approximate_components':0,'connected_panel_uids':[i+1]}
            h['edges']=box_edges(h);r['hardware'].append(h)
        self.assertIn('m1',find_repetitions(r,m))
        r['hardware'][1]['article']='OTHER';self.assertEqual(find_repetitions(r,m),{})
    def test_pdf_reference_uses_actual_pages_and_current_labels(self):
        from hierarchical import write_hierarchical
        from pypdf import PdfReader
        r,m=fixture();plan={'modules':m}
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'test.pdf';write_hierarchical(r,out,plan)
            texts=[p.extract_text() for p in PdfReader(out).pages]
            reference=next(t for t in texts if 'Montaj identic' in t)
            start,end=plan['module_page_ranges']['m0']
            self.assertIn(f'paginile {start}–{end}',reference)
            self.assertIn('COD1',reference)
            self.assertFalse(any('Corp 1 | Pasul' in t for t in texts))
            self.assertTrue(any('Corp 0 | Pasul' in t for t in texts))

if __name__=='__main__':unittest.main()
