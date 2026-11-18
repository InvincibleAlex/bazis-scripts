import unittest
from export_assembly import repair_text,assign_hardware,hardware_hosts

class HardwareChecks(unittest.TestCase):
    def test_unicode(self):
        self.assertEqual(repair_text('U\u00c8\u2122\u00c4\u0192'),'U\u0219\u0103')
        self.assertEqual(repair_text('Plint\u00c4\u0192'),'Plint\u0103')
        for s in ['U\u0219\u0103','\u0218urub','Caf\u00e9','9073567']:
            self.assertEqual(repair_text(s),s)
    def test_unique_owner_and_no_duplicate_counts(self):
        panels=[dict(id='a',uid=1,bounds={'min':[0,0,0],'max':[18,300,600]}),dict(id='b',uid=2,bounds={'min':[18,0,0],'max':[600,18,600]})]
        fittings=[dict(id='screw',bounds={'min':[0,5,20],'max':[50,12,27]},connected_panel_uids=[1,2])]
        assign_hardware(fittings,panels)
        self.assertEqual(fittings[0]['host_panel_id'],'b')
        self.assertEqual(len(fittings),1)
        self.assertEqual(hardware_hosts(fittings[0],panels),{'a','b'})
    def test_unmatched_hardware_not_assigned_arbitrarily(self):
        fittings=[dict(id='x',bounds={'min':[100,100,100],'max':[110,110,110]})]
        assign_hardware(fittings,[dict(id='a',bounds={'min':[0,0,0],'max':[18,20,20]})])
        self.assertNotIn('host_panel_id',fittings[0])
    def test_parent_loose_filler_does_not_steal_child_cabinet_screws(self):
        from hierarchical import module_items
        b={'min':[0,0,0],'max':[18,300,600]}
        cabinet=dict(id='board',uid=1,ancestors=['root','front','M1','carcass'],bounds=b)
        filler=dict(id='filler',uid=2,ancestors=['root','front','fals'],bounds=b)
        screw=dict(id='screw',ancestors=['root','front','M1','carcass'],bounds=b,host_panel_id='filler',host_method='old wrong match')
        report={'panels':[cabinet,filler],'hardware':[screw]}
        child={'id':'M1','steps':[{'panel_id':'board'}]}
        parent={'id':'front','steps':[{'panel_id':'filler'}]}
        self.assertEqual(len(module_items(report,child)[1]),1)
        self.assertEqual(module_items(report,parent)[1],[])
        self.assertEqual(screw['host_panel_id'],'board')
        self.assertEqual(len(module_items(report,child)[1]),1)
    def test_explicit_links_are_not_replaced_by_an_unrelated_nearby_board(self):
        f=dict(id='screw',connected_panel_uids=[99],bounds={'min':[0,0,0],'max':[10,10,10]})
        assign_hardware([f],[dict(id='wrong',uid=1,bounds={'min':[0,0,0],'max':[10,10,10]})])
        self.assertNotIn('host_panel_id',f)

if __name__=='__main__':unittest.main()
