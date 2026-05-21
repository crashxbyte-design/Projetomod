path = r'C:\Users\Admin\Documents\Robson\sp_dashboard\panel_executivo.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'meses_com_26' in line:
        # Replace just the offending f-string argument
        lines[i] = line.replace(
            'abrevs[max(meses_com_26, default=1)]',
            '(abrevs[[j for j,v in enumerate(v26_flt) if v>0][-1]] if any(v>0 for v in v26_flt) else abrevs[-1])'
        )
        print(f'Fixed line {i+1}')

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Done')
