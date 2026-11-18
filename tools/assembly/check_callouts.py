import unittest
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from callouts import layout,intersects


class CalloutChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):pdfmetrics.registerFont(TTFont('Body','C:/Windows/Fonts/arial.ttf'))

    def test_labels_avoid_tall_boards_and_each_other(self):
        boards=[[(90,50),(105,50),(105,550),(90,550)],[(160,50),(175,50),(175,550),(160,550)],[(105,570),(175,570),(175,590),(105,590)]]
        result=layout([(str(i),p) for i,p in enumerate(boards)],boards,(20,20,300,620))
        self.assertEqual(len(result),3)
        self.assertTrue(all(p['collisions']==0 for p in result))
        for p in result:
            self.assertTrue(all(not intersects(p['rect'],b) for b in boards))
            a,b,c=p['path'];dx=abs(b[0]-a[0]);dy=abs(b[1]-a[1])
            self.assertGreater(dx,0)
            poly=boards[int(p['label'])]
            self.assertEqual(a,((min(q[0] for q in poly)+max(q[0] for q in poly))/2,(min(q[1] for q in poly)+max(q[1] for q in poly))/2))
            self.assertAlmostEqual(dx,dy)
            self.assertAlmostEqual(b[1],c[1])
            self.assertLess(sum(((v[0]-u[0])**2+(v[1]-u[1])**2)**.5 for u,v in zip(p['path'],p['path'][1:])),100)

    def test_wide_board_uses_space_above_or_below(self):
        board=[(25,150),(595,150),(595,170),(25,170)]
        labels=layout([('27',board)],[board],(20,20,580,300))
        self.assertEqual(len(labels),1)
        self.assertEqual(labels[0]['collisions'],0)
        self.assertFalse(intersects(labels[0]['rect'],board))


if __name__=='__main__':unittest.main()
