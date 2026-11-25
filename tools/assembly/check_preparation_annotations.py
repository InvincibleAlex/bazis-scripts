import copy
import math
from preparation_annotations import insertion_arrows
from hierarchical import transform,axial_explode
plate={'id':'p','bounds':{'min':[0,0,0],'max':[100,100,18]}}
f={'id':'h','name':'Diblu lemn 8x30','bounds':{'min':[10,40,-10],'max':[18,48,20]},'edges':[[[10,40,-10],[18,48,20]]],
   'insertion_axis':[0,0,1],'assembly_entry_points':[[14,44,0],[14,44,0]]}
before=copy.deepcopy(f)
original=transform([f],lambda p:[p[0]+5,p[2],-p[1]])
moved=axial_explode(plate,original)
arrows=insertion_arrows(original,moved)
assert len(arrows)==1
assert arrows[0]['end']==[19,0,-44]
assert arrows[0]['source']=='BAZIS receiving-panel hole'
assert arrows[0]['start']!=arrows[0]['end']
assert moved[0]['assembly_entry_points']==original[0]['assembly_entry_points']
assert f==before
print('PASS: bore-mouth targets survive rotations and explosion; arrows point toward panel; no model mutation')
# Regression: holes and entry axes follow the same transforms as the displayed plate.
from preparation_annotations import projected_arrow
from hardware_labels import assign_article_labels
plate_with_hole=dict(plate,holes=[{'position_global_mm':[14,44,0],'direction_global':[0,0,1],'direction_panel_local':[0,0,1]}])
shown=transform([plate_with_hole],lambda p:[p[0]+5,p[2],-p[1]])[0]
assert shown['holes'][0]['position_global_mm']==[19,0,-44]
assert shown['holes'][0]['direction_global']==[0,1,0]
assert shown['holes'][0]['direction_panel_local']==[0,0,1]
assert plate_with_hole['holes'][0]['position_global_mm']==[14,44,0]
for length in [10,50,500]:
 drawing=projected_arrow((0,0),(length,0))
 assert 0<math.dist(drawing['tail'],drawing['tip'])<=18
 assert drawing['tip'][0]>drawing['tail'][0]
 assert drawing['axis_end'][0]>drawing['axis_start'][0]
items=[{'name':'Diblu','article':'A'},{'name':'Diblu','article':'A'},{'name':'Balamaua','article':'B'}]
assign_article_labels(items);assert [p['label'] for p in items]==[1,1,2]
print('PASS: displayed native holes transform consistently; short arrows retain direction; shared article numbering')
