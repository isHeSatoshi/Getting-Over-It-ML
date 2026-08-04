import json
d=json.load(open('Getting Over It v1/assets/project.json',encoding='utf-8'))
for t in d['targets']:
    if t['name']=='Player':
        b=t['blocks']
        print('l control_if_else:', b['l'])
        print('l% broadcast:', b['l%'])
        bk = b['l(']
        print('l-paren broadcast:', bk)
        print('an repeat_until:', b['an'])
        print('  CONDITION ref:', b['an']['inputs']['CONDITION'])
        print('ao control_if:', b['ao'])
        print('l? broadcast:', b['l?'])
        print('ma forever:', b['ma'])
