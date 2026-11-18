import copy
import unittest
from export_assembly import display_steps

class Repetitions(unittest.TestCase):
    def setUp(self):
        self.panels=[]
        self.steps=[]
        for i in range(3):
            self.panels.append(dict(id=str(i),parent='shelves',designation='001',name='Raft',material='PAL alb',width=600,height=300,thickness=18,
                bounds={'min':[0,i*100,0],'max':[600,i*100+18,300]},duplicate_signature={'bands':[],'cuts':0},edges=[]))
            self.steps.append(dict(panel_id=str(i),role='horizontal',offset_mm=[180,0,0],instruction='Insert'))
    def groups(self):return display_steps({'panels':self.panels},{'steps':self.steps})
    def test_translation_repeats_and_coverage(self):
        g=self.groups();self.assertEqual(len(g),1)
        self.assertEqual([s['panel_id'] for op in g for s in op['instances']],['0','1','2'])
    def test_no_cross_parent_or_direction(self):
        self.panels[1]['parent']='other';self.assertEqual(len(self.groups()),3)
        self.panels[1]['parent']='shelves';self.steps[1]['offset_mm']=[0,0,180];self.assertEqual(len(self.groups()),3)
    def test_same_code_is_authoritative_even_without_feature_snapshot(self):
        self.panels[1]['duplicate_signature']={'bands':['different'],'cuts':0};self.assertEqual(len(self.groups()),1)
        self.panels[1]['duplicate_signature']=None;self.assertEqual(len(self.groups()),1)
    def test_different_code_separate_and_same_code_authoritative(self):
        self.panels[1]['designation']='002';self.assertEqual(len(self.groups()),2)
        self.panels[1]['designation']='001';self.panels[1]['material']='MDF';self.assertEqual(len(self.groups()),1)
    def test_instance_pose_does_not_split_same_code(self):
        self.panels[1]['bounds']['max']=[300,118,600];self.assertEqual(len(self.groups()),1)
    def test_initial_base_not_folded(self):
        self.steps[0]['offset_mm']=[0,0,0];self.assertEqual(len(self.groups()),2)
    def test_numeric_noise_does_not_split_identical_boards(self):
        self.panels[1]['bounds']['max'][1]+=1e-10
        self.panels[1]['width']=600.0
        self.assertEqual(len(self.groups()),1)
    def test_seven_boards_rendered_in_one_operation(self):
        for i in range(3,7):
            p=copy.deepcopy(self.panels[0]);p['id']=str(i);p['bounds']={'min':[0,i*100,0],'max':[600,i*100+18,300]};self.panels.append(p)
            s=copy.deepcopy(self.steps[0]);s['panel_id']=str(i);self.steps.append(s)
        self.assertEqual(len(self.groups()),1);self.assertEqual(len(self.groups()[0]['instances']),7)

if __name__=='__main__':unittest.main()
