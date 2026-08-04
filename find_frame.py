import json
d=json.load(open('Getting Over It v1/assets/project.json',encoding='utf-8'))
# Find every block whose fields.VARIABLE[1] is the FRAME var id.
frame_id = '(h/zA+h*`trBdxt,jtOV'
hits=[]
for t in d['targets']:
    name=t['name']
    for bid,b in t.get('blocks',{}).items():
        if not isinstance(b,dict): continue
        fld=b.get('fields',{})
        if 'VARIABLE' in fld:
            v=fld['VARIABLE']
            # v can be [name, id] or [name, id, ...]
            if any(frame_id==x for x in v):
                hits.append((name,bid,b.get('opcode'),fld['VARIABLE']))
print('FRAME writers:', len(hits))
for h in hits[:20]: print(' ',h)
