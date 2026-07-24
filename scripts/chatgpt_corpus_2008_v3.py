import json
import re
import runpy
import zipfile
from pathlib import Path

import requests
import trafilatura

runpy.run_path('scripts/chatgpt_corpus_2008_v2.py', run_name='__main__')

root = Path('2008_O_payload')
manifest_path = root / 'manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))

url = 'https://xbeta.info/input-skills.htm'
title = '深入分析：如何提高打字速度？（1）'
response = requests.get(url, timeout=50, headers={'User-Agent': 'Mozilla/5.0 corpus-research/1.0'})
response.raise_for_status()
response.encoding = response.apparent_encoding or response.encoding
text = trafilatura.extract(
    response.text,
    include_comments=False,
    include_tables=False,
    include_links=False,
    include_images=False,
    favor_precision=True,
    output_format='txt',
) or ''

lines = []
for line in text.replace('\r', '').split('\n'):
    stripped = line.strip()
    if not stripped:
        lines.append('')
        continue
    if stripped in {title, '深入分析:如何提高打字速度？(1)'}:
        continue
    if re.search(r'^(作者|日期|发布时间|来源|本文链接|永久链接|标签|分类)[:：]', stripped):
        continue
    if stripped.startswith('Image:'):
        continue
    lines.append(line)
text = '\n'.join(lines)
for marker in ['\n相关文章', '\n相关链接', '\n参考资料', '\n参考文献', '\n条评论', '\n发表评论']:
    pos = text.find(marker)
    if pos > 700:
        text = text[:pos]
text = re.sub(r'\[(?:\d+|注\d+)\]', '', text)
text = re.sub(r'[①②③④⑤⑥⑦⑧⑨⑩]', '', text)
text = re.sub(r'https?://\S+', '', text)
text = re.sub(r'[ \t]+\n', '\n', text)
text = re.sub(r'\n[ \t]+', '\n', text)
text = re.sub(r'\n{3,}', '\n\n', text).strip()
char_count = len(re.sub(r'\s+', '', text))
if char_count < 650:
    raise RuntimeError(f'Supplemental article extraction too short: {char_count}')

number = len(manifest['records']) + 1
filename = f'2008_O_{number:03d}_input_skills_cleaned.txt'
(root / 'texts' / filename).write_text(text + '\n', encoding='utf-8')
record = {
    '#': number,
    'text_id': f'2008_O_{number:03d}',
    'bin': '2008_O_bin01',
    'first_publication_year': 2008,
    'title': title,
    'author': '张玉新（xbeta）',
    'source_url_or_identifier': url,
    'simplified or traditional Chinese': 'simplified Chinese',
    'char_count': char_count,
    'ocr_quality': 'high (native digital; cleaned)',
    'copyright_status': '2008年采用 CC BY-NC-SA 2.5；作者后续将原创内容置于公共领域',
    'notes': '输入效率与方法评论；原生数字文本；已删除标题、日期/作者、图片图注、页面导航、相关链接与评论区；不含国家政策类评论。',
    'filename': filename,
    'source_name': '善用佳软',
}
manifest['records'].append(record)
manifest['document_count'] = len(manifest['records'])
manifest['sources'] = sorted({row['source_name'] for row in manifest['records']})

combined_path = root / '2008_O_bin01_combined.txt'
combined = combined_path.read_text(encoding='utf-8').rstrip() + '\n\n' + text + '\n'
combined_path.write_text(combined, encoding='utf-8')
actual = len(re.sub(r'\s+', '', combined))
manifest['actual_characters'] = actual
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

zip_path = Path('2008_O_payload.zip')
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in root.rglob('*'):
        if path.is_file():
            archive.write(path, path.relative_to(root.parent))

print('V3_SUPPLEMENT_CHARS', char_count)
print('RESULT_ACTUAL', actual)
print('RESULT_BAND_OK', 106_000 <= actual <= 114_000)
print('RESULT_DOCS', manifest['document_count'])
print('RESULT_SOURCES', manifest['sources'])
print('RESULT_ZIP', zip_path.resolve())
