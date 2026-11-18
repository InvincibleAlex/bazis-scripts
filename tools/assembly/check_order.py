import unittest
from export_assembly import make_plan,role


class MountingOrderChecks(unittest.TestCase):
    def test_decorative_filler_cannot_become_first_structural_side(self):
        nodes=[{'id':'root','name':'Model'},{'id':'m','name':'M2'},{'id':'carcass','name':'Carcasa'},
               {'id':'fals','name':'Fals'},{'id':'inside','name':'Compartimentare'}]
        def board(id,name,x,chain,code,thickness=18):
            return dict(id=id,name=name,ancestors=['root','m']+chain,parent=chain[-1],designation=code,
                        thickness=thickness,material='HDF' if thickness==3 else 'PAL',bounds={'min':[x,0,0],'max':[x+thickness,2500,400]})
        parts=[board('f','Verticală - Fals Decorativ',-100,['carcass','fals'],'11.01.01.01.01.001'),
               board('right','Verticală',500,['carcass'],'11.01.02.00.00.002'),
               board('left','Verticală',0,['carcass'],'11.01.02.00.00.001'),
               board('shelf','Orizontală',20,['inside'],'11.01.01.02.01.001'),
               board('back','Frontal',10,['carcass'],'11.01.02.00.00.005',3)]
        report={'nodes':nodes,'panels':parts}
        parts[-1]['bounds']={'min':[10,0,0],'max':[600,2500,3]}
        parts[3]['bounds']={'min':[20,0,0],'max':[600,18,400]}
        steps=make_plan(report)['modules'][0]['steps'];ids=[s['panel_id'] for s in steps]
        self.assertEqual(ids[0],'left')
        self.assertLess(ids.index('right'),ids.index('shelf'))
        self.assertLess(ids.index('shelf'),ids.index('f'))
        self.assertEqual(role(parts[-1],{n['id']:n for n in nodes}),'back')
        self.assertEqual(set(ids),{p['id'] for p in parts})
        # The same hierarchy and geometry must retain its order after renaming
        # every board and subgroup, while retaining the same designation.
        for index,node in enumerate(nodes):
            if node['id'] not in ['root','m']:node['name']='Grup arbitrar '+str(index)
        for index,p in enumerate(parts):
            p['name']='Piesa arbitrara '+str(index)
        renamed=make_plan(report)['modules'][0]['steps']
        self.assertEqual([s['panel_id'] for s in renamed],ids)
        parts[1]['designation']='2';parts[2]['designation']='10';parts[0]['designation']='0'
        numeric=make_plan(report)['modules'][0]['steps']
        self.assertEqual(numeric[0]['panel_id'],'right','numeric 2 precedes 10 within the same structural role')
        self.assertEqual(numeric[-1]['panel_id'],'f','nested filler code 0 cannot override hierarchy')


if __name__=='__main__':unittest.main()
