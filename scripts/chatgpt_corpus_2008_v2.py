import re
import json
import hashlib
import zipfile
import shutil
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag
import trafilatura

TARGET = 110_000
OUT = Path('2008_O_payload')
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
TXT = OUT / 'texts'
TXT.mkdir()

S = requests.Session()
S.headers.update({'User-Agent': 'Mozilla/5.0 corpus-research/1.0'})

POLICY_WORDS = [
    '国家政策', '政府政策', '法规解读', '施政', '国务院', '中央政府',
    '公共政策', '政治制度', '选举制度', '政党', '外交政策', '监管政策',
    '政府工作报告', '行政法规', '政府施政', '人大代表', '政治改革'
]


def nonspace_count(text):
    return len(re.sub(r'\s+', '', text))


def norm_text(text):
    text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\u00a0', ' ')
    text = re.sub(r'\[(?:\d+|注\d+|[一二三四五六七八九十]+)\]', '', text)
    text = re.sub(r'[①②③④⑤⑥⑦⑧⑨⑩]', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n[ \t]+', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def policy_ok(title, text):
    probe = title + '\n' + text[:8000]
    return not any(word in probe for word in POLICY_WORDS)


def cut_footer(text):
    markers = [
        '\n原文地址：', '\n原文地址:', '\n作者：', '\n作者:', '\n编辑：', '\n编辑:',
        '\n相关文章', '\n相关链接', '\n延伸阅读', '\n参考资料', '\n参考文献',
        '\n网友评论', '\n评论列表', '\n我要评论', '\nComments', '\n评论：',
        '\n条留言', '\n登录以回复', '\n本文标签'
    ]
    cuts = []
    for marker in markers:
        pos = text.find(marker)
        if pos > 700:
            cuts.append(pos)
    return text[:min(cuts)] if cuts else text


def clean_rst(raw):
    lines = raw.replace('\r', '').split('\n')
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and lines[0].lstrip().startswith('.. _'):
        lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)
    title = lines.pop(0).strip() if lines else ''
    if lines and re.fullmatch(r'[=\-~^`:#*+]{3,}', lines[0].strip()):
        lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and ('mindhacks.cn' in lines[0] or re.match(r'`[^`]+ <https?://', lines[0].strip())):
        lines.pop(0)
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('.. note::'):
            break
        if stripped.startswith(('.. image::', '.. figure::', '.. |', '.. _')):
            continue
        if re.fullmatch(r'[=\-~^`:#*+]{3,}', stripped):
            continue
        line = re.sub(r'`([^`<]+?)\s*<https?://[^>]+>`__?', r'\1', line)
        line = re.sub(r'`([^`]+?)`__?', r'\1', line)
        line = line.replace('**', '').replace('\\', '')
        line = re.sub(r'^\s*#\.\s*', '', line)
        line = re.sub(r'^\s*\|\s?', '', line)
        line = re.sub(r'\|[A-Za-z0-9_\-]+\|', '', line)
        out.append(line.rstrip())
    text = norm_text(cut_footer('\n'.join(out)))
    if title and text.startswith(title):
        text = text[len(title):].lstrip('\n ')
    return title, text


def html_main(url, title_hint=''):
    response = S.get(url, timeout=50)
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
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append('')
            continue
        if title_hint and stripped == title_hint.strip():
            continue
        if re.search(r'^(作者|日期|发布时间|来源|本文链接|永久链接|标签|分类|软件类型|软件下载)[:：]', stripped):
            continue
        if stripped.startswith('Image:'):
            continue
        lines.append(line)
    return norm_text(cut_footer('\n'.join(lines)))


def add_doc(docs, source, title, author, url, text, license_status, topic, note, mandatory=False):
    text = norm_text(text)
    if not text or nonspace_count(text) < 650:
        return
    if not policy_ok(title, text):
        print('POLICY_DROP', title)
        return
    digest = hashlib.sha256(re.sub(r'\s+', '', text).encode('utf-8')).hexdigest()
    if any(item['hash'] == digest for item in docs):
        return
    docs.append({
        'source': source, 'title': title, 'author': author, 'url': url,
        'text': text, 'char_count': nonspace_count(text), 'license': license_status,
        'topic': topic, 'note': note, 'hash': digest, 'mandatory': mandatory,
    })


docs = []

mind_files = [
    '200804_reading-method.rst', '200806_how-memory-works.rst',
    '200807_learning-habits-part1.rst', '200807_learning-habits-part2.rst',
    '200809_learning-habits-part3.rst', '200812_learning-habits-part4.rst',
    '200812_how-to-think-straight.rst', '200810_methodology-for-programmers.rst',
    '200806_why-is-quicksort-so-quick.rst', '200807_the-importance-of-knowing-why.rst',
    '200804_learning-from-polya.rst', '200809_the-magical-bayesian-method.rst',
    '200809_machine-learning-and-ai-resources.rst',
]
for filename in mind_files:
    raw_url = f'https://raw.githubusercontent.com/me115/read/master/pongba/allpapers/{filename}'
    response = S.get(raw_url, timeout=50)
    if response.status_code != 200:
        print('MIND_FAIL', filename, response.status_code)
        continue
    response.encoding = 'utf-8'
    title, text = clean_rst(response.text)
    match = re.search(r'原文地址[:：]\s*(https?://\S+)', response.text)
    original_url = match.group(1).rstrip() if match else raw_url
    topic = '学习与认知评论'
    if any(key in title for key in ['贝叶斯', '快排', '算法', '波利亚']):
        topic = '数学与算法评论'
    elif '程序员' in title:
        topic = '程序设计方法评论'
    elif '人工智能' in title or '机器学习' in title:
        topic = '人工智能学习评论'
    add_doc(
        docs, 'MindHacks', title, '刘未鹏', original_url, text,
        '作者明确允许转载；须注明作者、出处和原始链接', topic,
        '原始博客正文；镜像仅用于技术恢复；已删除标题、作者/编辑信息、原始链接行、参考资料及数字角标。',
        mandatory=True,
    )

xbeta_items = [
    ('如何选择软件：深度用户与浅层用户的区别', 'https://xbeta.info/software-choice.htm', '软件选择评论', True),
    ('善用佳软博客原则：友情链接', 'https://xbeta.info/policy-links.htm', '博客文化评论', True),
    ('Gmail Labs 新功能不完全手册 v1.4', 'https://xbeta.info/gmail-labs.htm', '互联网产品评测', True),
    ('总结：快速启动程序和文档的好软件', 'https://xbeta.info/tmp1-quick-launch.htm', '效率软件综合评测', False),
    ('IrfanView作者专访：IrfanView、软件、人生', 'https://xbeta.info/irfanview-interview.htm', '软件文化与开发者评论', False),
    ('免费软件限商业用途，那么什么是商业应用？', 'https://xbeta.info/freeware-nonbiz.htm', '软件许可与使用评论', False),
    ('IrfanView看图比ACDSee/XnView慢吗？', 'https://xbeta.info/irfanview-tmp080721.htm', '图像软件比较评测', False),
]
for title, url, topic, mandatory in xbeta_items:
    try:
        text = html_main(url, title)
        if 'tmp1-quick-launch' in url:
            text = re.sub(
                r'2\.2\.2\+\s*国产新秀ALTRun（2010-06-29补充）.*?(?=2\.2\.3\s*小巧强大的Executor)',
                '', text, flags=re.S,
            )
            text = re.sub(r'\n更新于\s*2010-06-29.*$', '', text, flags=re.S)
        for marker in ['更新历史', '版本历史', '条评论', '发表评论']:
            pos = text.find('\n' + marker)
            if pos > 800:
                text = text[:pos]
        add_doc(
            docs, '善用佳软', title, '张玉新（xbeta）', url, text,
            '2008年采用 CC BY-NC-SA 2.5；作者后续将原创内容置于公共领域', topic,
            '原生数字文本；已删除标题、日期/作者、图片图注、页面导航、相关文章、更新后插入内容与评论区。',
            mandatory=mandatory,
        )
    except Exception as exc:
        print('XBETA_FAIL', url, repr(exc))

william_targets = {
    '百度安全中心评测': '互联网安全产品评测',
    '常用的Web 2.0服务和网站': '互联网服务评论',
    '常用的 Web 2.0 服务和网站': '互联网服务评论',
    'Google Chrome的云计算和SaaS': '浏览器与云计算评论',
    '谷歌浏览器Google Chrome的使用率分析': '互联网产品数据评论',
    '电影三国之赤壁观后感': '电影评论',
    '百度左侧广告的分析——公司篇': '搜索广告观察',
    '十个装机必备的免费软件': '软件推荐与评测',
}
for month in range(1, 13):
    archive_url = f'https://info.williamlong.info/2008/{month:02d}/'
    try:
        response = S.get(archive_url, timeout=50)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        for heading in soup.find_all('h3'):
            link = heading.find('a')
            if not link:
                continue
            title = ' '.join(link.get_text(' ', strip=True).split())
            normalized_title = re.sub(r'\s+', '', title)
            matched = None
            for candidate_title, topic in william_targets.items():
                if re.sub(r'\s+', '', candidate_title) == normalized_title:
                    matched = (candidate_title, topic)
                    break
            if not matched:
                continue
            parts = []
            for sibling in heading.next_siblings:
                if isinstance(sibling, Tag) and sibling.name in ('h2', 'h3'):
                    break
                if isinstance(sibling, Tag):
                    for bad in sibling.select('script,style,noscript,img,figure,figcaption'):
                        bad.decompose()
                    segment = sibling.get_text('\n', strip=True)
                    if segment:
                        parts.append(segment)
            text = norm_text('\n\n'.join(parts))
            source_url = urljoin(archive_url, link.get('href', ''))
            mandatory = normalized_title in {
                re.sub(r'\s+', '', '百度安全中心评测'),
                re.sub(r'\s+', '', '常用的Web 2.0服务和网站'),
            }
            add_doc(
                docs, '月光博客', title, 'William Long', source_url, text,
                'CC BY-NC-SA 2.5（网站版权声明）', matched[1],
                '从作者2008年月度存档正文提取；已删除标题、图片/图注、页面导航和非正文元数据。',
                mandatory=mandatory,
            )
    except Exception as exc:
        print('WILLIAM_FAIL', archive_url, repr(exc))

appinn_items = [
    ('Bookmarklet：小书签，实用浏览器小工具补完', 'https://www.appinn.com/bookmarklet/', 'sfufoet', '浏览器工具综合评测'),
    ('常见软件问题两则', 'https://www.appinn.com/soft-faq/', 'sfufoet', '软件使用经验评论'),
    ('关于介绍软件相关信息', 'https://www.appinn.com/about-soft-info/', 'sfufoet', '软件媒体写作评论'),
    ('讨论：当你使用软件前，希望得到什么信息？', 'https://www.appinn.com/discuss-software-information/', 'scavin', '用户需求与软件评价'),
    ('在使用软件前，我希望获得什么信息', 'https://www.appinn.com/discuss-software-information-result/', 'scavin', '用户需求调查评论'),
]
for title, url, author, topic in appinn_items:
    try:
        text = html_main(url, title)
        text = re.split(r'\n(?:\d+\s*条留言|留言|评论)\n', text, maxsplit=1)[0]
        add_doc(
            docs, '小众软件', title, author, url, text,
            'CC BY-NC-SA（网站版权声明：署名-非商业用途-保持一致）', topic,
            '原生数字文本；已删除标题、日期/作者、图片图注、下载框、页面导航、标签和评论区。',
            mandatory=False,
        )
    except Exception as exc:
        print('APPINN_FAIL', url, repr(exc))

docs = [
    item for item in docs
    if 650 <= item['char_count'] <= 45_000
    and not any(word in item['title'] for word in ['国家政策', '政府政策', '法规解读'])
]

print('CANDIDATES_BEGIN')
for index, item in enumerate(docs):
    print(index, item['mandatory'], item['source'], item['char_count'], item['title'])
print('CANDIDATES_END')

mandatory_indices = [i for i, item in enumerate(docs) if item['mandatory']]
optional_indices = [i for i, item in enumerate(docs) if not item['mandatory']]

best = None
for mask in range(1 << len(optional_indices)):
    chosen = mandatory_indices.copy()
    for bit, index in enumerate(optional_indices):
        if mask >> bit & 1:
            chosen.append(index)
    sources = {docs[i]['source'] for i in chosen}
    appinn_count = sum(docs[i]['source'] == '小众软件' for i in chosen)
    if not {'MindHacks', '善用佳软', '月光博客', '小众软件'}.issubset(sources):
        continue
    if appinn_count < 2:
        continue
    total = sum(docs[i]['char_count'] for i in chosen)
    band_penalty = 0 if 106_000 <= total <= 114_000 else min(abs(total - 106_000), abs(total - 114_000)) * 8
    diversity_bonus = len(chosen) * 4 + len(sources) * 100
    score = band_penalty + abs(total - TARGET) - diversity_bonus
    if best is None or score < best[0]:
        best = (score, total, chosen)

if best is None:
    chosen = list(range(len(docs)))
    best = (abs(sum(item['char_count'] for item in docs) - TARGET), sum(item['char_count'] for item in docs), chosen)

_, selected_total, selected_indices = best
selected = [docs[i] for i in sorted(set(selected_indices))]
source_order = {'善用佳软': 0, '月光博客': 1, '小众软件': 2, 'MindHacks': 3}
selected.sort(key=lambda item: (source_order.get(item['source'], 9), item['title']))

manifest = []
for number, item in enumerate(selected, 1):
    slug = re.sub(r'[^a-z0-9]+', '_', item['url'].lower().split('/')[-1].split('.')[0]).strip('_') or f'text{number:03d}'
    filename = f'2008_O_{number:03d}_{slug[:45]}_cleaned.txt'
    (TXT / filename).write_text(item['text'] + '\n', encoding='utf-8')
    manifest.append({
        '#': number,
        'text_id': f'2008_O_{number:03d}',
        'bin': '2008_O_bin01',
        'first_publication_year': 2008,
        'title': item['title'],
        'author': item['author'],
        'source_url_or_identifier': item['url'],
        'simplified or traditional Chinese': 'simplified Chinese',
        'char_count': item['char_count'],
        'ocr_quality': 'high (native digital; cleaned)',
        'copyright_status': item['license'],
        'notes': f"{item['topic']}；{item['note']}；不含国家政策类评论。",
        'filename': filename,
        'source_name': item['source'],
    })

combined = '\n\n'.join(item['text'] for item in selected).strip() + '\n'
(OUT / '2008_O_bin01_combined.txt').write_text(combined, encoding='utf-8')
actual = nonspace_count(combined)

payload = {
    'target_characters': TARGET,
    'actual_characters': actual,
    'count_method': 'all non-whitespace Unicode characters in cleaned main text',
    'document_count': len(manifest),
    'sources': sorted({record['source_name'] for record in manifest}),
    'records': manifest,
}
(OUT / 'manifest.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

(OUT / 'SOURCE_LICENSES.txt').write_text(
    '2008_O 来源与许可说明\n\n'
    '1. MindHacks（刘未鹏）：原文明确允许转载，条件为注明作者、出处和原始链接。\n'
    '2. 善用佳软（张玉新/xbeta）：2008年采用 CC BY-NC-SA 2.5；作者后续声明其原创内容进入公共领域。\n'
    '3. 月光博客（William Long）：网站版权页声明采用 CC BY-NC-SA 2.5。\n'
    '4. 小众软件（Appinn）：版权页允许个人非商业转载，遵循署名-非商业用途-保持一致的创作共用协议。\n\n'
    '清洗范围：仅正文；删除标题、作者/日期等页面元数据、摘要/关键词（如有）、图表及图注、参考资料/参考文献、评论区、相关链接、页眉页脚、[1] 等数字引用角标。\n'
    '题材排除：国家政策、政府施政、法规解读、政治制度、选举及其他政策政治类评论。\n',
    encoding='utf-8',
)

zip_path = Path('2008_O_payload.zip')
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in OUT.rglob('*'):
        if path.is_file():
            archive.write(path, path.relative_to(OUT.parent))

print('RESULT_ACTUAL', actual)
print('RESULT_DOCS', len(manifest))
print('RESULT_SOURCES', sorted({record['source_name'] for record in manifest}))
print('RESULT_SELECTED_TOTAL', selected_total)
print('RESULT_ZIP', zip_path.resolve())
