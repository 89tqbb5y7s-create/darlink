from __future__ import annotations
import csv, hashlib, html, io, json, re, sys, unicodedata, zipfile
from pathlib import Path
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup

YEAR=2011
TARGET=110000
MINC=104500
MAXC=115500
OUT=Path('corpus_out'); OUT.mkdir(exist_ok=True)
UA={'User-Agent':'Mozilla/5.0 corpus-research/1.0'}

COMMENT=('评论','观点','观察','看法','思考','反思','批评','启示','体验','为什么','争论','论战','谈谈','再谈','文化','管理','职业','故事','现象','趋势','竞争','产品','创业','社会','政策','发展','建议','模式','价值','选择','教育','生活','行业','评','不同','问题','影响','之路','谎谬','品质','申诉','悲催','招聘','程序员','开源','软件公司','微博','配置','用户')
EXCLUDE=('教程','速查卡','代码示例','安装','下载','入门','图解','算法代码','使用说明','函数实现','Cheat Sheet','课程','资源和趣闻','文章和各种资源','文章资源','贴子和工具','免费课程','开发工具和资源')
BACK=('参考文献','参考资料','引用资料','注释','脚注','延伸阅读','相关链接','外部链接','版权声明','作者简介','致谢','鸣谢','利益冲突','基金项目','评论','留言')

def nows(t): return len(re.sub(r'\s+','',t))
def zh(t): return len(re.findall(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]',t))
def norm(t):
    t=t.replace('\r\n','\n').replace('\r','\n')
    t=re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹⁰\u2070-\u209f]+','',t)
    return unicodedata.normalize('NFKC',t).replace('\u00a0',' ').replace('\u200b','')
def inline(t):
    t=re.sub(r'!\[[^\]]*\]\([^)]+\)','',t)
    t=re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',t)
    t=re.sub(r'<https?://[^>]+>|https?://\S+|\bwww\.[^\s，。；：！？）】]+','',t)
    t=re.sub(r'`{1,3}([^`]+)`{1,3}',r'\1',t)
    t=t.replace('**','').replace('__','').replace('~~','')
    t=re.sub(r'\[\s*\d+(?:\s*[-–,，]\s*\d+)*\s*\]','',t)
    return re.sub(r'\s+',' ',t).strip()
def clean_lines(lines,title=''):
    out=[]; started=False; tn=re.sub(r'\s+','',title)
    for raw in lines:
        line=raw.strip()
        if not line: out.append(''); continue
        meta=re.sub(r'^[#>*+\-\s]+','',line).strip()
        mc=re.sub(r'\s+','',meta)
        if not started and (mc==tn or re.match(r'^(title|date|modified|category|tags|slug|authors?|source)\s*:',meta,re.I) or re.match(r'^(作者|日期|时间|来源|编辑|责任编辑|发布单位|发布机构)[:：]',meta) or meta in {'目录','目 录','CONTENTS'}): continue
        hp=re.sub(r'^[#>*\-\s\d.、（）()]+','',line).strip('：:')
        if hp in BACK: break
        if re.search(r'(打印本页|关闭窗口|上一篇|下一篇|返回顶部|分享到|责任编辑|网站地图|版权所有|ICP备|阅读次数|浏览次数|本文链接|评论已关闭)',line): continue
        if re.match(r'^[-_=*]{3,}$',line): continue
        if zh(line)>=2 or re.search(r'[A-Za-z0-9]',line): started=True
        out.append(line)
    paras=[]; buf=[]
    for line in out:
        if not line:
            if buf:
                p=inline(' '.join(buf)); buf=[]
                if nows(p)>=20: paras.append(p)
        else:
            line=re.sub(r'^\s*#+\s*','',line)
            line=re.sub(r'^\s*>\s*','',line)
            if line.startswith(('* ','- ','+ ')): line='• '+line[2:].strip()
            buf.append(line)
    if buf:
        p=inline(' '.join(buf))
        if nows(p)>=20: paras.append(p)
    seen=set(); fin=[]
    for p in paras:
        k=re.sub(r'\s+','',p)
        if k and k not in seen: seen.add(k); fin.append(p)
    return '\n\n'.join(fin).strip()+'\n' if fin else ''
def clean_md(md,title):
    t=norm(md)
    t=re.sub(r'\A---\s*\n.*?\n---\s*\n','',t,flags=re.S)
    t=re.sub(r'```.*?```|~~~.*?~~~','',t,flags=re.S)
    t=re.sub(r'<!--.*?-->','',t,flags=re.S)
    t=html.unescape(re.sub(r'<[^>]+>','',t))
    return clean_lines(t.splitlines(),title)
def clean_html(frag,title):
    s=BeautifulSoup(frag,'lxml')
    for tag in s.find_all(['script','style','noscript','figure','figcaption','table','svg','form','nav','footer','aside','iframe','audio','video','pre','code','sup']): tag.decompose()
    for a in s.find_all('a'): a.replace_with(a.get_text(' ',strip=True))
    lines=[]
    for node in s.find_all(['p','li','h2','h3','h4','blockquote']):
        x=node.get_text(' ',strip=True)
        if x: lines.extend([x,''])
    return clean_lines(lines or s.get_text('\n').splitlines(),title)
def get(url,**kw):
    r=requests.get(url,headers=UA,timeout=60,**kw); r.raise_for_status(); return r

def collect_gv():
    docs=[]; page=1
    while True:
        params={'after':'2011-01-01T00:00:00','before':'2012-01-01T00:00:00','per_page':100,'page':page,'_fields':'date,link,title,content'}
        r=requests.get('https://zhs.globalvoices.org/wp-json/wp/v2/posts',params=params,headers=UA,timeout=60)
        if r.status_code==400: break
        r.raise_for_status(); posts=r.json()
        if not posts: break
        for p in posts:
            title=BeautifulSoup(p['title']['rendered'],'html.parser').get_text(' ',strip=True)
            text=clean_html(p['content']['rendered'],title)
            if 500<=nows(text)<=30000 and zh(text)/max(nows(text),1)>.45:
                docs.append(dict(source='Global Voices 简体中文',title=title,author='Global Voices contributors',date=p['date'][:10],text=text,source_url=p['link'],official_url=p['link'],license='CC BY 3.0',copyright_status='public/open-license',notes='CC BY 3.0；正文HTML清洗；需署名。'))
        if page>=int(r.headers.get('X-WP-TotalPages',page)): break
        page+=1
    return docs

def unzip_repo(url):
    r=get(url); z=zipfile.ZipFile(io.BytesIO(r.content)); root=Path('/tmp')/('repo_'+hashlib.md5(url.encode()).hexdigest());
    if root.exists(): import shutil; shutil.rmtree(root)
    z.extractall(root); return next(root.iterdir())

def collect_coolshell():
    root=unzip_repo('https://github.com/slan-ning/coolshell-markdown/archive/refs/heads/main.zip')
    docs=[]
    for p in sorted((root/'2011').glob('*.md')):
        title=p.stem
        if title.startswith('[转]') or any(x in title for x in EXCLUDE) or not any(x in title for x in COMMENT): continue
        md=p.read_text(encoding='utf-8',errors='ignore'); text=clean_md(md,title)
        if 700<=nows(text)<=35000 and zh(text)/max(nows(text),1)>.35:
            m=re.search(r'^>?\s*date\s*:\s*(2011-\d\d-\d\d)',md,re.I|re.M)
            gh='https://github.com/slan-ning/coolshell-markdown/blob/main/2011/'+quote(p.name)
            docs.append(dict(source='酷壳 CoolShell',title=title,author='陈皓/酷壳作者',date=m.group(1) if m else '2011',text=text,source_url=gh,official_url='https://coolshell.cn/',license='署名＋非商业转载政策',copyright_status='permission-limited/noncommercial',notes='需注明作者和出处，不得商业使用；仅正文清洗。'))
    return docs

def collect_linuxtoy():
    root=unzip_repo('https://github.com/LinuxTOY/linuxtoy.org/archive/refs/heads/master.zip')
    docs=[]
    for p in sorted((root/'content').rglob('*.md')):
        md=p.read_text(encoding='utf-8',errors='ignore')
        meta={}
        for line in md.splitlines()[:25]:
            m=re.match(r'^(Title|Date|Authors?)\s*:\s*(.*)$',line,re.I)
            if m: meta[m.group(1).lower()]=m.group(2).strip()
        if not meta.get('date','').startswith('2011-'): continue
        title=meta.get('title',p.stem)
        if any(x in title for x in EXCLUDE): continue
        text=clean_md(md,title)
        if 600<=nows(text)<=25000 and zh(text)/max(nows(text),1)>.35:
            gh='https://github.com/LinuxTOY/linuxtoy.org/blob/master/'+quote(str(p.relative_to(root)).replace('\\','/'),safe='/')
            docs.append(dict(source='LinuxTOY',title=title,author=meta.get('authors','LinuxTOY contributors'),date=meta['date'][:10],text=text,source_url=gh,official_url='https://linuxtoy.org/',license='CC BY-NC-SA 2.5 中国大陆',copyright_status='public/open-license-noncommercial',notes='署名、非商业、相同方式共享；仅正文清洗。'))
    return docs

def dedup(ds):
    out=[]; seen=set(); titles=set()
    for d in ds:
        k=hashlib.sha256(re.sub(r'\s+','',d['text']).encode()).hexdigest(); tk=re.sub(r'\W+','',d['title']).lower()
        if k in seen or tk in titles: continue
        seen.add(k); titles.add(tk); d['char_count']=nows(d['text']); out.append(d)
    return out

def subset(docs):
    prev={0:None}
    for i,d in enumerate(docs):
        c=d['char_count']
        for s in sorted(list(prev.keys()),reverse=True):
            ns=s+c
            if ns<=MAXC and ns not in prev: prev[ns]=(s,i)
    candidates=[s for s in prev if MINC<=s<=MAXC]
    if not candidates: return None
    best=min(candidates,key=lambda s:abs(s-TARGET)); idx=[]; cur=best
    while cur:
        old,i=prev[cur]; idx.append(i); cur=old
    return best,sorted(idx)

def choose_bins(docs):
    # Favor diversity by interleaving sources and moderate lengths.
    groups={}
    for d in docs: groups.setdefault(d['source'],[]).append(d)
    for g in groups.values(): g.sort(key=lambda x:(x['date'],x['title']))
    ordered=[]
    while any(groups.values()):
        for src in sorted(groups):
            if groups[src]: ordered.append(groups[src].pop(0))
    a=subset(ordered)
    if not a: raise RuntimeError('Cannot form bin01')
    _,ia=a; b1=[ordered[i] for i in ia]; rem=[d for i,d in enumerate(ordered) if i not in set(ia)]
    b=subset(rem)
    if not b: raise RuntimeError('Cannot form bin02')
    _,ib=b; b2=[rem[i] for i in ib]
    return b1,b2

def safe(title,source,i):
    s=unicodedata.normalize('NFKC',title); s=re.sub(r'[\\/:*?"<>|\r\n\t]+','_',s); s=re.sub(r'\s+','_',s).strip('._ ')
    return f'2011_O_{i:03d}_{source}_{s[:55]}_cleaned.txt'

def main():
    all_docs=[]
    for fn in (collect_gv,collect_linuxtoy,collect_coolshell):
        try:
            x=fn(); print(fn.__name__,len(x)); all_docs+=x
        except Exception as e: print('WARN',fn.__name__,repr(e),file=sys.stderr)
    docs=dedup(all_docs); print('total',len(docs),sum(d['char_count'] for d in docs))
    b1,b2=choose_bins(docs)
    rows=[]; seq=1
    for bi,arr in enumerate((b1,b2),1):
        parts=[]
        for d in arr:
            fn=safe(d['title'],{'Global Voices 简体中文':'gv','LinuxTOY':'linuxtoy','酷壳 CoolShell':'coolshell'}[d['source']],seq)
            (OUT/fn).write_text(d['text'],encoding='utf-8'); parts.append(d['text'].strip())
            rows.append({'#':seq,'text_id':Path(fn).stem.replace('2011_O_','').replace('_cleaned',''),'bin':f'2011_O_bin0{bi}','first_publication_year':2011,'title':d['title'],'author':d['author'],'source_url_or_identifier':d['source_url'],'official_url':d['official_url'],'simplified or traditional Chinese':'simplified','char_count':d['char_count'],'ocr_quality':'copiable/cleaned','copyright_status':d['copyright_status'],'notes':d['notes'],'filename':fn,'source_name':d['source']})
            seq+=1
        (OUT/f'2011_O_bin0{bi}_cleaned.txt').write_text('\n\n'.join(parts)+'\n',encoding='utf-8')
    counts=[sum(x['char_count'] for x in b1),sum(x['char_count'] for x in b2)]
    meta={'year':2011,'target':TARGET,'bin_counts':counts,'documents':len(rows),'sources':sorted(set(r['source_name'] for r in rows)),'complete':all(MINC<=x<=MAXC for x in counts)}
    (OUT/'metadata.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'summary.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    with (OUT/'index.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    (OUT/'README.txt').write_text('2011年简体中文O类语料；两个bin均由完整文章组成。正文已删除标题、作者栏、日期栏、图表、链接、参考文献、评论及数字引文标记。权利状态见索引。\n',encoding='utf-8')
    with zipfile.ZipFile('2011_O_raw_artifact.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in OUT.rglob('*'):
            if p.is_file(): z.write(p,arcname='2011_O/'+p.name)
    print(json.dumps(meta,ensure_ascii=False))
    if not meta['complete']: raise SystemExit(2)
if __name__=='__main__': main()
