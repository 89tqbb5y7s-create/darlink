#!/usr/bin/env python3
# Temporary isolated 2013 corpus builder. Do not merge into the main application.
# Reopened-event trigger revision.
import csv, hashlib, html, json, re, shutil, subprocess, time
from pathlib import Path
from urllib.parse import quote, urljoin
import requests, markdown
from bs4 import BeautifulSoup
from opencc import OpenCC

Y=2013; TARGET=110000; LO=108500; HI=111500; OUT=Path('build/2013_O')
S=requests.Session(); S.headers['User-Agent']='Mozilla/5.0 academic corpus collection'; CC=OpenCC('t2s')
BAD=('sciscanpub.com','sciscan.org','hanspub.org')
STOP=re.compile(r'^(参考文献|参考资料|注释|脚注|外部链接|参见|版本信息|文档信息|相关文章|留言|评论区|责任编辑)$')
META=re.compile(r'^(作者[:：]|日期[:：]|发表日期[:：]|版权声明[:：]|分类[:：]|标签[:：]|来源[:：]|责任编辑[:：]|上一篇[:：]|下一篇[:：]|本作品收录于|发布机关[:：]|目录$|全文完|（完）$)')

def get(u,params=None):
    e=None
    for n in range(3):
        try:
            r=S.get(u,params=params,timeout=45); r.raise_for_status(); return r
        except Exception as x: e=x; time.sleep(n+1)
    raise RuntimeError(f'{u}: {e}')
def nw(s): return len(re.sub(r'\s+','',s))
def cjk(s): return len(re.findall(r'[\u3400-\u4dbf\u4e00-\u9fff]',s))
def clean(lines):
    out=[]; seen=set()
    for x in lines:
        x=CC.convert(html.unescape(x)).replace('\u200b','').replace('\ufeff','').replace('\xa0',' ')
        x=re.sub(r'https?://\S+','',x); x=re.sub(r'\s+',' ',x).strip(); x=re.sub(r'\[编辑\]|\[編輯\]','',x)
        x=re.sub(r'\[(?:\d+|\d+[–—-]\d+)(?:\s*[,，;；]\s*\d+)*\]','',x); x=re.sub(r'[⁰¹²³⁴⁵⁶⁷⁸⁹]+','',x)
        if not x or META.search(x): continue
        if STOP.fullmatch(x): break
        if x in seen and len(x)<80: continue
        seen.add(x); out.append(x)
    while out and len(out[0])<12 and not re.search(r'[。！？；：]',out[0]): out.pop(0)
    return '\n\n'.join(out).strip()
def drop_nodes(c):
    for q in 'script style noscript img svg figure figcaption table sup sub pre code blockquote .mw-editsection .toc .navbox .noprint .printfooter .catlinks .metadata .infobox .ws-noexport .mw-references-wrap #comments .comments .related .post-ratings .footer .sidebar'.split():
        for n in c.select(q): n.decompose()
def slug(t):
    m={'政府工作报告':'gov','最高人民法院':'court','最高人民检察院':'procuratorate','国民经济和社会发展计划':'plan','预算执行情况':'budget','武装力量':'armed_forces','非洲':'africa','人权':'human_rights','西藏':'tibet','比特币':'bitcoin','版权':'copyright','程序员':'programmer','效率':'efficiency'}
    for k,v in m.items():
        if k in t: return v+'_'+hashlib.md5(t.encode()).hexdigest()[:6]
    return 'text_'+hashlib.md5(t.encode()).hexdigest()[:10]
def add(pool,title,author,date,url,official,platform,genre,rights,license_url,text,notes):
    text=text.strip()
    if nw(text)<700 or cjk(text)<500 or any(d in url.lower() for d in BAD): return
    tid=slug(title); base=tid; z=2
    used={x['text_id'] for x in pool}
    while tid in used: tid=f'{base}_{z}'; z+=1
    pool.append(dict(text_id=tid,title=CC.convert(title),author=author,source_date=date,source_url=url,official_url=official,
        source_platform=platform,genre=genre,copyright_status=rights,license_url=license_url,text=text,
        file_name=f'2013_O_{tid}_cleaned.txt',char_count=nw(text),cjk_count=cjk(text),paragraphs=len(text.split('\n\n')),
        sha256=hashlib.sha256(re.sub(r'\s+','',text).encode()).hexdigest(),notes=notes))

W='https://zh.wikisource.org/w/api.php'
DOCS=[
('2013年中华人民共和国国务院政府工作报告','中华人民共和国国务院','政府工作回顾 / 政策评论','https://www.gov.cn/2013lh/content_2356362.htm'),
('2013年中华人民共和国最高人民法院工作报告','中华人民共和国最高人民法院','司法工作回顾 / 制度评论','https://www.court.gov.cn/'),
('2013年中华人民共和国最高人民检察院工作报告','中华人民共和国最高人民检察院','检察工作回顾 / 制度评论','https://www.spp.gov.cn/'),
('关于2012年国民经济和社会发展计划执行情况与2013年国民经济和社会发展计划草案的报告','国家发展和改革委员会','经济发展评估 / 政策展望','https://www.ndrc.gov.cn/'),
('关于2012年中央和地方预算执行情况与2013年中央和地方预算草案的报告','中华人民共和国财政部','财政执行评估 / 政策展望','https://www.mof.gov.cn/'),
('中国武装力量的多样化运用','国务院新闻办公室','国防政策评论 / 白皮书','https://www.gov.cn/zhengce/2013-04/16/content_2618505.htm'),
('中国与非洲的经贸合作（2013）','国务院新闻办公室','国际经贸回顾 / 白皮书','https://www.gov.cn/zhengce/2013-08/29/content_2615771.htm'),
('2012年中国人权事业的进展','国务院新闻办公室','社会发展回顾 / 白皮书','https://www.gov.cn/zhengce/2013-05/14/content_2615793.htm'),
('西藏的发展与进步','国务院新闻办公室','区域发展回顾 / 白皮书','https://www.gov.cn/zhengce/2013-10/22/content_2615752.htm')]
def wiki_title(q):
    j=get(W,{'action':'query','format':'json','formatversion':2,'titles':q,'redirects':1}).json(); p=j.get('query',{}).get('pages',[])
    if p and not p[0].get('missing'): return p[0]['title']
    j=get(W,{'action':'query','list':'search','srsearch':q,'srlimit':10,'format':'json','formatversion':2,'variant':'zh-hans'}).json()
    r=j.get('query',{}).get('search',[]); return r[0]['title'] if r else None
def official(pool):
    for q,a,g,o in DOCS:
        try:
            t=wiki_title(q)
            if not t: continue
            j=get(W,{'action':'parse','page':t,'prop':'text','format':'json','formatversion':2,'disabletoc':1,'disableeditsection':1,'variant':'zh-hans'}).json()
            so=BeautifulSoup(j['parse']['text'],'lxml'); c=so.select_one('.mw-parser-output') or so; drop_nodes(c)
            lines=[]; start=False
            for e in c.find_all(['h2','h3','h4','p','li']):
                x=CC.convert(e.get_text(' ',strip=True)); x=re.sub(r'\[编辑\]|\[編輯\]','',x).strip()
                if STOP.fullmatch(x): break
                if not start:
                    start=bool(re.search(r'各位代表|前\s*言|过去五年|工作回顾|当前|进入二十一世纪|一、|第一',x) or len(x)>90)
                    if not start: continue
                lines.append(x)
            u='https://zh.wikisource.org/zh-hans/'+quote(t.replace(' ','_'),safe='/:()（）')
            add(pool,q,a,'2013',u,o,'Wikisource / 国家机关公开文件','state official document / '+g,
                'Public domain: PRC Copyright Law Article 5 official document','https://www.ncac.gov.cn/xxfb/flfg/flfg_532/202103/t20210309_50530.html',clean(lines),
                f'official_url={o}; Wikisource page={t}; main body only; Simplified Chinese conversion.')
            print('OFFICIAL',q,pool[-1]['char_count'] if pool and pool[-1]['title']==q else 'skip')
        except Exception as e: print('OFFICIAL_FAIL',q,e)

INC=re.compile(r'读后感|感想|用途|版权|垄断|分工|熵|心理|未来|当代中国|纪录片|创业|社会|制度|苹果公司|美国枪击|开放|自由|互联网|技术|人生|生活|民主|教育|经济|博客|比特币|Secure Boot|货币|公司|产品|职业')
EXC=re.compile(r'详解|算法|JavaScript|Javascript|jQuery|Boyer|KMP|Event Loop|寄存器|Source Map|严格模式|相似图片|TF-IDF|朴素贝叶斯|字符串匹配|代码|编程|CORS|RSA|CSS|HTTP|API|教程|安装|启动')
def after_h1(so):
    h=so.find('h1'); lines=[]
    if not h:return '', ''
    for e in h.find_all_next(['h2','h3','h4','p','li']):
        if e.find_parent(['blockquote','pre','code','table','figure']): continue
        x=CC.convert(e.get_text(' ',strip=True))
        if STOP.fullmatch(x) or re.match(r'^留言（?\d*',x) or re.search(r'文档信息|版权声明|相关文章',x): break
        if e.find_parent(id=re.compile(r'comment|sidebar|footer|related',re.I)): continue
        lines.append(x)
    return h.get_text(' ',strip=True),clean(lines)
def ruanyf(pool):
    links=set()
    for m in range(1,13):
        try: so=BeautifulSoup(get(f'https://www.ruanyifeng.com/blog/2013/{m:02d}/').text,'lxml')
        except: continue
        for a in so.find_all('a',href=True):
            u=urljoin('https://www.ruanyifeng.com',a['href'])
            if re.search(r'/blog/2013/\d{2}/[^/?#]+\.html$',u): links.add(u)
    for u in sorted(links):
        try: so=BeautifulSoup(get(u).text,'lxml'); title,text=after_h1(so); alltxt=so.get_text(' ',strip=True)
        except Exception as e: print('RUANYF_FAIL',u,e); continue
        if not title or not INC.search(title) or EXC.search(title): continue
        if '自由转载-非商用-非衍生-保持署名' not in alltxt and '创意共享3.0许可证' not in alltxt: continue
        mm=re.search(r'/blog/2013/(\d{2})/',u); date='2013-'+mm.group(1) if mm else '2013'
        genre='书评 / 影评 / 文化评论' if re.search(r'读后感|纪录片|电影|书',title) else '观点 / 科技与社会评论'
        add(pool,title,'阮一峰',date,u,u,'阮一峰的网络日志',genre,'CC BY-NC-ND 3.0','https://creativecommons.org/licenses/by-nc-nd/3.0/',text,
            'Page explicitly states 自由转载-非商用-非衍生-保持署名; code, blockquotes, images, comments and back matter removed; wording preserved.')
    print('RUANYF',len([x for x in pool if x['source_platform']=='阮一峰的网络日志']))

CINC=re.compile(r'加班与效率|编程能力与编程年龄|面向对象的设计模式|环保.*百度|谎谬|至理名言|管理|职业|团队|开源|文化|思考|观点|设计')
CEXC=re.compile(r'译文|翻译|摘录|教程|算法|技巧|二维码|Linux|Java|C语言|Lua|Shell|详解|原理')
def coolshell(pool):
    r=Path('/tmp/haoel'); shutil.rmtree(r,ignore_errors=True); subprocess.run(['git','clone','--depth','1','https://github.com/ghostincoolshell/haoel-articles.git',str(r)],check=True)
    for p in sorted((r/'blogs/rss2html2markdown').glob('2013-*.md')):
        title=re.sub(r'^2013-\d{1,2}-\d{1,2}\s+','',p.stem)
        if not CINC.search(title) or CEXC.search(title): continue
        raw=p.read_text('utf-8',errors='ignore'); raw=re.split(r'转载本站文章请注明作者和出处|请勿用于任何商业用途|相关文章',raw)[0]; raw=re.sub(r'```.*?```','',raw,flags=re.S)
        so=BeautifulSoup(markdown.markdown(raw,extensions=['extra']),'lxml'); c=so.body or so; drop_nodes(c)
        text=clean([e.get_text(' ',strip=True) for e in c.find_all(['h2','h3','h4','p','li'])])
        dm=re.match(r'(2013-\d{1,2}-\d{1,2})',p.stem); date=dm.group(1) if dm else '2013'; om=re.search(r'https://coolshell\.cn/articles/\d+\.html',raw); off=om.group(0) if om else 'https://coolshell.cn/'
        u='https://github.com/ghostincoolshell/haoel-articles/blob/ba4cb2e19730d13ab92a1a0ced8c0798c6f32982/'+quote(str(p.relative_to(r)),safe='/')
        add(pool,title,'陈皓 / CoolShell',date,u,off,'酷壳 CoolShell','科技评论 / 职场评论','Author-permitted attribution; noncommercial only','https://coolshell.cn/',text,
            f'Article footer permits redistribution with attribution and prohibits commercial use; official_url={off}; main prose only.')
    print('COOLSHELL',len([x for x in pool if x['source_platform']=='酷壳 CoolShell']))

def excerpt(x,need):
    ps=[]; n=0
    for p in x['text'].split('\n\n'):
        z=nw(p)
        if ps and n+z>need+450: break
        ps.append(p); n+=z
        if n>=need-300: break
    if n<700:return None
    y=x.copy(); y['text']='\n\n'.join(ps); y['text_id']=x['text_id']+'_excerpt'; y['title']=x['title']+'（正文节选）'; y['file_name']=f"2013_O_{y['text_id']}_cleaned.txt"; y['char_count']=nw(y['text']); y['cjk_count']=cjk(y['text']); y['paragraphs']=len(ps); y['sha256']=hashlib.sha256(re.sub(r'\s+','',y['text']).encode()).hexdigest(); y['notes']+=' Paragraph-boundary excerpt used for bin balancing; no rewriting or padding.'; return y
def bins(pool):
    seen=set(); pool=[x for x in pool if not (x['sha256'] in seen or seen.add(x['sha256']))]
    groups={k:[x for x in pool if x['source_platform']==k] for k in sorted({x['source_platform'] for x in pool})}
    used=set(); bs=[]
    for b in range(2):
        sel=[]; total=0
        for g,v in groups.items():
            cand=[x for x in v if id(x) not in used]
            if cand:
                x=sorted(cand,key=lambda z:z['char_count'],reverse=True)[min(b,len(cand)-1)]; sel.append(x); used.add(id(x)); total+=x['char_count']
        rest=sorted([x for x in pool if id(x) not in used],key=lambda x:(x['source_platform'],x['char_count']))
        for x in rest:
            if total>=TARGET-700: break
            if total+x['char_count']<=TARGET+350: sel.append(x); used.add(id(x)); total+=x['char_count']
        if total<LO:
            need=TARGET-total
            cand=sorted([x for x in pool if id(x) not in used and x['char_count']>=need-600],key=lambda x:abs(x['char_count']-need))
            if cand:
                y=excerpt(cand[0],need)
                if y: sel.append(y); used.add(id(cand[0])); total+=y['char_count']
        bs.append(sel)
    return bs,[x for x in pool if id(x) not in used]
def write(bs,unused):
    OUT.mkdir(parents=True,exist_ok=True); rows=[]
    for bi,sel in enumerate(bs,1):
        bn=f'2013_O_bin{bi:02d}'
        for x in sel:
            x['bin']=bn; Path(OUT/x['file_name']).write_text(x['text']+'\n',encoding='utf-8'); d={k:v for k,v in x.items() if k!='text'}; d['index']=len(rows)+1; rows.append(d)
        Path(OUT/f'{bn}_cleaned.txt').write_text('\n\n'.join(x['text'] for x in sel)+'\n',encoding='utf-8')
    Path(OUT/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    flds=['index','text_id','bin','source_date','title','author','source_platform','genre','source_url','official_url','copyright_status','license_url','file_name','char_count','cjk_count','paragraphs','sha256','notes']
    with open(OUT/'manifest.csv','w',encoding='utf-8-sig',newline='') as f: w=csv.DictWriter(f,fieldnames=flds); w.writeheader(); w.writerows({k:r.get(k,'') for k in flds} for r in rows)
    with open(OUT/'excluded_candidates.csv','w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f); w.writerow(['title','source_platform','source_url','reason']); [w.writerow([x['title'],x['source_platform'],x['source_url'],'valid licensed/open candidate not selected after bin balancing']) for x in unused]; w.writerow(['SCISCAN / 汉斯出版社','excluded','','explicitly excluded by user']); w.writerow(['知乎 / 豆瓣未授权全文','excluded','','public readability is not redistribution permission'])
    stats=[]; issues=[]
    for bi,sel in enumerate(bs,1):
        t=Path(OUT/f'2013_O_bin{bi:02d}_cleaned.txt').read_text('utf-8'); st={'bin':f'2013_O_bin{bi:02d}','non_whitespace_chars':nw(t),'cjk_chars':cjk(t),'files':len(sel),'platforms':sorted({x['source_platform'] for x in sel})}; stats.append(st)
        if not LO<=st['non_whitespace_chars']<=HI: issues.append(f"{st['bin']} count outside range: {st['non_whitespace_chars']}")
        if len(st['platforms'])<2: issues.append(f"{st['bin']} lacks source diversity")
    for x in rows:
        t=Path(OUT/x['file_name']).read_text('utf-8')
        if re.search(r'\[(?:\d+|\d+[–—-]\d+)\]|[⁰¹²³⁴⁵⁶⁷⁸⁹]|参考文献|责任编辑[:：]|版权声明[:：]|文档信息|相关文章|留言（?\d*条',t): issues.append(x['text_id']+' non-body marker')
        if x['source_date'][:4]!='2013' or any(d in x['source_url'].lower() for d in BAD): issues.append(x['text_id']+' source/year problem')
    qa={'status':'PASS' if not issues else 'FAIL','year':2013,'target_per_bin':TARGET,'accepted_range':[LO,HI],'bins':stats,'selected_documents':len(rows),'source_platforms':sorted({x['source_platform'] for x in rows}),'excluded_publishers':['SCISCAN','Hans Publishers / 汉斯出版社'],'issues':issues}
    Path(OUT/'qa_report.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
    md=['# 2013_O Quality Assurance Report','',f"**Status: {qa['status']}**",'']
    for s in stats: md += [f"## {s['bin']}",f"- Non-whitespace characters: {s['non_whitespace_chars']:,}",f"- CJK characters: {s['cjk_chars']:,}",f"- Individual files: {s['files']}",f"- Platforms: {', '.join(s['platforms'])}",'']
    md += ['## Compliance','- Main body only; title/byline/date, abstracts, figures/tables/captions, references, comments, footers and numeric citation markers removed.','- No fabricated text, duplicated padding or paraphrasing.','- SCISCAN, Hans Publishers and unlicensed Zhihu/Douban full text excluded.','', '## Issues'] + ([f'- {x}' for x in issues] if issues else ['- None detected.'])
    Path(OUT/'QA_REPORT.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    Path(OUT/'README.md').write_text(f"# 2013_O Corpus\n\nTwo Simplified Chinese Opinion/Commentary/Review bins. Bin01: {stats[0]['non_whitespace_chars']:,}; Bin02: {stats[1]['non_whitespace_chars']:,} non-whitespace characters. The final A-type workbook is added after artifact retrieval.\n",encoding='utf-8')
    print(json.dumps(qa,ensure_ascii=False,indent=2))
    if issues: raise SystemExit('QA failed')
def main():
    shutil.rmtree(OUT,ignore_errors=True); pool=[]; official(pool); ruanyf(pool); coolshell(pool); print('POOL',len(pool),sum(x['char_count'] for x in pool))
    if sum(x['char_count'] for x in pool)<225000: raise SystemExit('insufficient pool')
    bs,u=bins(pool); print('BIN_RAW',[sum(x['char_count'] for x in b) for b in bs]); write(bs,u)
if __name__=='__main__': main()
