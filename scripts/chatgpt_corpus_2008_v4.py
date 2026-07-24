import json
import re
import runpy
import zipfile
from pathlib import Path

import requests
import trafilatura

runpy.run_path('scripts/chatgpt_corpus_2008_v3.py', run_name='__main__')

root = Path('2008_O_payload')
manifest_path = root / 'manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
combined_path = root / '2008_O_bin01_combined.txt'
combined = combined_path.read_text(encoding='utf-8').rstrip()

candidates = [
    ('关于介绍软件相关信息', 'https://www.appinn.com/about-soft-info/', 'sfufoet', '软件媒体写作评论'),
    ('讨论：当你使用软件前，希望得到什么信息？', 'https://www.appinn.com/discuss-software-information/', 'scavin', '用户需求与软件评价'),
    ('在使用软件前，我希望获得什么信息', 'https://www.appinn.com/discuss-software-information-result/', 'scavin', '用户需求调查评论'),
]


def extract(url, title):
    response = requests.get(url, timeout=50, headers={'User-Agent': 'Mozilla/5.0 corpus-research/1.0'})
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    text = trafilatura.extract(
        response.text, include_comments=False, include_tables=False,
        include_links=False, include_images=False, favor_precision=True,
        output_format='txt',
    ) or ''
    lines = []
    aliases = {title, title.replace('：', ':'), title.replace('？', '?')}
    for line in text.replace('\r', '').split('\n'):
        stripped = line.strip()
        if not stripped:
            lines.append('')
            continue
        if stripped in aliases:
            continue
        if re.search(r'^(作者|日期|发布时间|来源|本文链接|永久链接|标签|分类|软件类型|软件下载)[:：]', stripped):
            continue
        if stripped.startswith('Image:'):
            continue
        lines.append(line)
    text = '\n'.join(lines)
    for marker in ['\n条留言', '\n留言', '\n评论', '\n相关文章', '\n相关链接', '\n参考资料', '\n参考文献']:
        pos = text.find(marker)
        if pos > 180:
            text = text[:pos]
    text = re.sub(r'\[(?:\d+|注\d+)\]', '', text)
    text = re.sub(r'[①②③④⑤⑥⑦⑧⑨⑩]', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n[ \t]+', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text

actual = len(re.sub(r'\s+', '', combined))
for title, url, author, topic in candidates:
    if actual >= 106_000:
        break
    text = extract(url, title)
    char_count = len(re.sub(r'\s+', '', text))
    if char_count < 180:
        print('SKIP_SHORT', title, char_count)
        continue
    number = len(manifest['records']) + 1
    slug = re.sub(r'[^a-z0-9]+', '_', url.lower().rstrip('/').split('/')[-1]).strip('_')
    filename = f'2008_O_{number:03d}_{slug}_cleaned.txt'
    (root / 'texts' / filename).write_text(text + '\n', encoding='utf-8')
    manifest['records'].append({
        '#': number,
        'text_id': f'2008_O_{number:03d}',
        'bin': '2008_O_bin01',
        'first_publication_year': 2008,
        'title': title,
        'author': author,
        'source_url_or_identifier': url,
        'simplified or traditional Chinese': 'simplified Chinese',
        'char_count': char_count,
        'ocr_quality': 'high (native digital; cleaned)',
        'copyright_status': 'CC BY-NC-SA（网站版权声明：署名-非商业用途-保持一致）',
        'notes': f'{topic}；原生数字文本；已删除标题、日期/作者、图片图注、页面导航、标签和评论区；不含国家政策类评论。',
        'filename': filename,
        'source_name': '小众软件',
    })
    combined += '\n\n' + text
    actual = len(re.sub(r'\s+', '', combined))
    print('APPENDED', title, char_count, 'TOTAL', actual)

if not 106_000 <= actual <= 114_000:
    raise RuntimeError(f'Final corpus character count outside accepted band: {actual}')

combined += '\n'
combined_path.write_text(combined, encoding='utf-8')
manifest['document_count'] = len(manifest['records'])
manifest['actual_characters'] = actual
manifest['sources'] = sorted({row['source_name'] for row in manifest['records']})
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

zip_path = Path('2008_O_payload.zip')
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in root.rglob('*'):
        if path.is_file():
            archive.write(path, path.relative_to(root.parent))

print('FINAL_RESULT_ACTUAL', actual)
print('FINAL_RESULT_DOCS', manifest['document_count'])
print('FINAL_RESULT_SOURCES', manifest['sources'])
print('FINAL_RESULT_ZIP', zip_path.resolve())
