import copy
import unittest
from export_assembly import make_plan

class MountingOrderChecks(unittest.TestCase):
    def fixture(self):
        nodes=[dict(id='root',name='Model'),dict(id='m',name='M2'),dict(id='shell',name='Arbitrary group'),dict(id='extra',name='Another group')]
        def board(id,x0,x1,thickness=18,z1=400,y1=2500,parent='shell',code='001'):
            return dict(id=id,name='Arbitrary '+id,ancestors=['root','m',parent],parent=parent,designation=code,thickness=thickness,bounds={'min':[x0,0,0],'max':[x1,y1,z1]})
        panels=[board('right',600,618,code='0'),board('shelf',18,600,y1=18,parent='extra',code='200'),board('filler',-30,-12,parent='extra',code='999'),board('left',0,18,code='100'),board('back',0,618,thickness=3,z1=3,code='0'),board('door',0,618,z1=18,code='0')]
        return dict(nodes=nodes,panels=panels)

    def ids(self,report):return [s['panel_id'] for s in make_plan(report)['modules'][0]['steps']]

    def test_sweep_keeps_neighbor_side_before_shelves_and_right_side_after(self):
        report=self.fixture()
        self.assertEqual(self.ids(report),['filler','left','shelf','right','back','door'])
        for p in report['panels']:p['designation']='1'
        self.assertEqual(self.ids(report),['filler','left','shelf','right','back','door'])

    def test_local_sweep_survives_rotation_and_translation(self):
        report=self.fixture();expected=self.ids(report)
        def point(v):return [v[2]+1000,v[1]+100,-v[0]+400]
        for p in report['panels']:
            b=p['bounds'];vertices=[point([b['max'][a] if n&(1<<a) else b['min'][a] for a in range(3)]) for n in range(8)]
            p['bounds']={'min':[min(v[a] for v in vertices) for a in range(3)],'max':[max(v[a] for v in vertices) for a in range(3)]}
            normal=[0,1,0] if p['id']=='shelf' else [0,0,1] if p['id'] in ('back','door') else [1,0,0]
            p['frame']={'axes':[[0,0,0],[0,0,0],[normal[2],normal[1],-normal[0]]]}
        report['nodes'][1]['frame']={'origin':[1000,100,400],'axes':[[0,0,-1],[0,1,0],[1,0,0]]}
        self.assertEqual(self.ids(report),expected)

    def test_names_do_not_affect_order_and_input_is_unchanged(self):
        report=self.fixture();before=copy.deepcopy(report);expected=self.ids(report)
        self.assertEqual(report,before)
        for node in report['nodes'][2:]:node['name']='Renamed'
        for p in report['panels']:p['name']='Renamed'
        self.assertEqual(self.ids(report),expected)

    def test_numeric_codes_break_equal_position_ties(self):
        report=self.fixture();shelf=next(p for p in report['panels'] if p['id']=='shelf')
        other=copy.deepcopy(shelf);other.update(id='shelf2',designation='2');shelf['designation']='10';report['panels'].append(other)
        ids=self.ids(report);self.assertLess(ids.index('shelf2'),ids.index('shelf'))

    def test_inner_face_precedes_outer_closure_regardless_of_code(self):
        report=self.fixture();door=next(p for p in report['panels'] if p['id']=='door')
        door['bounds']={'min':[0,0,380],'max':[618,2500,398]};door['designation']='0'
        inside=copy.deepcopy(door);inside.update(id='inner',name='Arbitrary inside piece',designation='999')
        inside['bounds']={'min':[0,0,362],'max':[618,95,380]};report['panels'].append(inside)
        ids=self.ids(report)
        self.assertLess(ids.index('inner'),ids.index('door'))
        self.assertLess(ids.index('right'),ids.index('inner'))

if __name__=='__main__':unittest.main()
