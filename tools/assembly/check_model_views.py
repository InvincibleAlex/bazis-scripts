import copy,tempfile,unittest
from pathlib import Path
from pypdf import PdfReader
from model_views import view_layout,write_model_views,insert_model_views
from export_assembly import box_edges


class ModelViews(unittest.TestCase):
    def test_four_views_are_aligned_and_chain_excludes_drill_edges(self):
        from model_views import detail_coordinates
        scale,views=view_layout(([0,0,0],[800,2000,500]),(0,0,800,650),four=True)
        side,front,top,left=views
        self.assertEqual(front[2],top[2]);self.assertEqual(left[3],front[3])
        self.assertGreater(left[2],front[2]+800*scale)
        p={'bounds':{'min':[0,0,0],'max':[800,2000,500]},'edges':[[[127.5,20,0],[135.5,20,0]]]}
        self.assertEqual(detail_coordinates([p],0,0,800),[0,800])

    def test_axis_depth_mask_hides_rear_edges_and_keeps_cutouts(self):
        from visibility import DepthMask
        mask=DepthMask((0,0,100,100),lambda p:(p[0],p[1]),1,depth_function=lambda p:p[2])
        mask.polygon([[0,0,10],[100,0,10],[100,100,10],[0,100,10]],
                     [[[40,40,10],[60,40,10],[60,60,10],[40,60,10]]])
        self.assertFalse(mask.segments([10,20,0],[90,20,0]))
        visible=mask.segments([10,50,0],[90,50,0])
        self.assertTrue(visible)
        self.assertGreater(visible[0][0][0],39)
        self.assertLess(visible[-1][1][0],61)

    def test_first_angle_alignment_and_shared_scale(self):
        scale,views=view_layout(([10,20,30],[810,2020,530]),(30,80,570,800))
        side,front,top=views
        self.assertEqual(front[2],top[2]);self.assertEqual(side[3],front[3])
        self.assertLess(side[2]+500*scale,front[2])
        self.assertLess(top[3]+500*scale,front[3])
        self.assertGreater(scale,0)

    def test_native_extents_page_insertion_and_model_unchanged(self):
        p={'bounds':{'min':[10,20,30],'max':[810,2020,530]}}
        p['edges']=box_edges(p)
        report={'panels':[p],'hardware':[]};before=copy.deepcopy(report)
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'views.pdf';write_model_views(report,output)
            text=PdfReader(output).pages[0].extract_text()
            for value in ('800','2000','500','Vedere de sus','Vedere din față','Vedere din dreapta'):self.assertIn(value,text)
            plan={'cartus_contexts':{1:{'corp':'cover'},2:{'_specification':True}},'module_page_ranges':{'m':[3,5]}}
            insert_model_views(report,output,plan)
            self.assertEqual(len(PdfReader(output).pages),2)
            self.assertEqual(plan['cartus_contexts'][1],{'corp':'cover'})
            self.assertTrue(plan['cartus_contexts'][2]['_specification'])
            self.assertEqual(plan['module_page_ranges']['m'],[4,6])
        self.assertEqual(report,before)


if __name__=='__main__':unittest.main()
