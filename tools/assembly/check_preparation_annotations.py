import copy
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
