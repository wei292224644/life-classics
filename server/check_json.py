import json

with open('worflow_parser_kb/rules/content_type_rules.json', encoding='utf-8') as f:
    content = f.read()

try:
    result = json.loads(content)
    print('JSON is VALID')
    print('Content types:', [ct['id'] for ct in result['content_types']])
except json.JSONDecodeError as e:
    print(f'ERROR at line={e.lineno} col={e.colno} pos={e.pos}')
    char_at = content[e.pos] if e.pos < len(content) else 'EOF'
    print(f'Char at pos: {repr(char_at)} ord={ord(char_at) if isinstance(char_at, str) else "N/A"}')
    print(f'Context: {repr(content[max(0,e.pos-50):e.pos+50])}')

    # Also check for problem chars
    for i, ch in enumerate(content):
        if ord(ch) in (0x201C, 0x201D, 0x2018, 0x2019):
            print(f'Curly quote at char pos {i}: {repr(ch)} (U+{ord(ch):04X}), context: {repr(content[max(0,i-10):i+10])}')
