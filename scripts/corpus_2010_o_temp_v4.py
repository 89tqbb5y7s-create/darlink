#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from corpus_2010_o_temp import SOURCE_REPO, TARGET, LOWER, UPPER, topic_of, safe_slug

OUT = Path('out')
TXT_DIR = OUT / 'texts'


def count_chars(text: str) -> int:
    return len(re.sub(r'\s+', '', text))


def normalize(text: str) -> str:
    text = unicodedata.normalize('NFKC', text).replace('\r\n','\n').replace('\r','\n')
    text = text.replace('\u3000',' ').replace('\xa0',' ')
    text = re.sub(r'[ \t]+',' ',text)
    text = re.sub(r' *\n *','\n',text)
    text = re.sub(r'\n{3,}','\n\n',text)
    text = re.sub(r'(?<!\w)\[(?:\d{1,3})(?:\s*[-–,，]\s*\d{1,3})*\](?!\w)','',text)
    text = re.sub(r'\[STRIKEOUT:[^\]]+\]','',text)
    text = re.sub(r'[①②③④⑤⑥⑦⑧⑨⑩]','',text)
    return text.strip()


def clean_rst_strict(raw: str):
    raw = raw.replace('\r\n','\n')
    # Resolve RST hyperlinks, including labels that wrap across lines.
    raw = re.sub(r'`([^`<>]+?)\s*<https?://[^>]+>`__', lambda m: re.sub(r'\s+',' ',m.group(1)).strip(), raw, flags=re.S)
    raw = re.sub(r'`([^`]+?)`__', r'\1', raw, flags=re.S)
    raw = re.sub(r'\|image\d+\|','',raw,flags=re.I)
    raw = re.sub(r'\[STRIKEOUT:([^\]]+)\]','',raw)
    lines = raw.splitlines()
    title=''; author=''; official=''; title_i=None
    for i,line in enumerate(lines):
        s=line.strip()
        if not s or s.startswith('.. _'): continue
        if i+1 < len(lines) and re.fullmatch(r'[=\-~^`:#*+]{3,}',lines[i+1].strip()):
            title=s; title_i=i; break
    for line in lines:
        m=re.search(r'原文地址:\s*(https?://\S+)',line)
        if m: official=m.group(1).rstrip('`_ '); break
    for line in lines[:40]:
        m=re.search(r'20\d{2}年\d{1,2}月\d{1,2}日.*?`?([^<`]+?)\s*<',line)
        if m: author=m.group(1).strip(); break
    if not author:
        for line in lines[-25:]:
            m=re.search(r'作者:\s*([^\n]+)',line)
            if m: author=m.group(1).strip(); break
    if title_i is None: return '', '', '', ''
    body_lines=[]; i=title_i+2; in_code=False; code_indent=0
    while i < len(lines):
        line=lines[i]; s=line.strip()
        if s.startswith('.. note::'): break
        if s.startswith('.. |') or s.startswith('.. image::') or s.startswith(':target:') or s.startswith(':width:') or s.startswith(':alt:'):
            i+=1; continue
        if re.match(r'^20\d{2}年\d{1,2}月\d{1,2}日',s): i+=1; continue
        if re.fullmatch(r'(?:mindhacks\.cn|ruanyifeng\.com)',s,flags=re.I): i+=1; continue
        if re.fullmatch(r'`?(?:mindhacks\.cn|ruanyifeng\.com)\s*<[^>]+>`?__',s,flags=re.I): i+=1; continue
        if s == '::':
            in_code=True; code_indent=0; i+=1; continue
        if in_code:
            if not s: i+=1; continue
            indent=len(line)-len(line.lstrip())
            if code_indent==0 and indent>=3: code_indent=indent
            if code_indent and indent>=code_indent: i+=1; continue
            in_code=False
        if re.match(r'^(?:源文|文章来源|原文地址|作者|译者|编辑|版权|标签|参考资料|参考文献)[:：]',s,re.I):
            i+=1; continue
        if re.match(r'^\|?\s*(?:文章)?\s*[:：]?\s*来源\s*\|?$',s): i+=1; continue
        if re.fullmatch(r'(?:图|图片|截图|Figure)\s*\d*[:：]?',s,re.I): i+=1; continue
        line=re.sub(r'https?://\S+','',line)
        line=line.replace('\\ ',' ').replace('\\','')
        line=re.sub(r'^\s*#\.\s*','',line)
        line=re.sub(r'^\s*[-*+]\s+','',line)
        line=line.replace('**','').replace('``','').replace('`','')
        body_lines.append(line.rstrip())
        i+=1
    body=normalize('\n'.join(body_lines))
    body=re.sub(r'^\s*(?:mindhacks\.cn|ruanyifeng\.com)\s*\n+','',body,flags=re.I)
    body=re.sub(r'\n\s*\|?\s*(?:文章)?\s*[:：]?\s*来源\s*\|?\s*(?:\(全文完\)|（全文完）)?\s*$','',body,flags=re.I)
    body=re.sub(r'\s*(?:\(全文完\)|（全文完）|\(完\)|（完）)\s*$','',body)
    # Appendices are not the author's main article and are excluded.
    body=re.split(r'\n\s*(?:附录|Appendix)\s*\n',body,maxsplit=1,flags=re.I)[0]
    body=normalize(body)
    return title.strip(), author.strip(), official.strip(), body


def zh_ratio(t):
    c=re.sub(r'\s+','',t)
    return len(re.findall(r'[\u3400-\u9fff]',c))/max(len(c),1)


def opinion_score(title,body,path):
    pos=re.compile(r'评论|评测|书评|影评|观察|思考|看法|观点|分析|反思|争论|误区|真相|未来|文化|为什么|为何|应该|不应该|不要|如何|值得|建议|经验|教训|失败|成功|选择|原则|团队|职场|公司|创业|管理|产品|用户|互联网|开源|版权|出版|教育|社会|人生')
    neg=re.compile(r'教程|入门|语法|函数|源码|代码示例|安装|下载|配置指南|发布|更新日志|招聘|通知|汇总|资源列表|书目')
    markers=re.compile(r'我认为|我觉得|在我看来|我的看法|值得注意|可以看出|这说明|建议|应该|不应该|遗憾|可惜|问题在于|关键在于')
    s=(4 if pos.search(title) else 0)-(7 if neg.search(title) else 0)
    s+=min(len(markers.findall(body[:7000])),8)*0.7
    if re.search(r'opinions|essays|startup|literature',path): s+=2.2
    if 900<=count_chars(body)<=10000: s+=1
    if zh_ratio(body)<.62: s-=5
    return s


def make(path,source,author,copyright_status,license_url,notes,minscore=1.5):
    raw=path.read_text(encoding='utf-8',errors='ignore')
    title,a,official,body=clean_rst_strict(raw)
    if not title or not official or count_chars(body)<650: return None
    score=opinion_score(title,body,str(path))
    if score<minscore: return None
    return {'title':title,'author':author or a or '未标明','official_url':official.replace('http://','https://'),
            'mirror_source':f'https://github.com/me115/read/blob/master/{path.relative_to(SOURCE_REPO).as_posix()}',
            'source_site':source,'body':body,'char_count':count_chars(body),'topic':topic_of(title,body),
            'quality_score':round(score,2),'copyright_status':copyright_status,'license_url':license_url,'notes':notes}


# Only clearly authorial CoolShell pieces; obvious translations/third-party reproductions are excluded.
COOL_TITLES={'史上最糟糕的网站','给老婆普及计算机知识','五种应该避免的代码注释','面向对象是个骗局？！'}

def gather_cool():
    out=[]; seen=set()
    for p in (SOURCE_REPO/'coolshell').rglob('*.rst'):
        raw=p.read_text(encoding='utf-8',errors='ignore')
        if '2010年' not in raw[:1800]: continue
        title,_,_,_=clean_rst_strict(raw)
        if title not in COOL_TITLES: continue
        aid=re.search(r'articles(\d+)',p.name); k=aid.group(1) if aid else str(p)
        if k in seen: continue
        x=make(p,'CoolShell','陈皓','Official repost permission with attribution and original source','https://coolshell.cn/about',
               '仅选取作者评论性正文；排除明显外文翻译、转载原文和纯教程。',minscore=-2)
        if x: seen.add(k); out.append(x)
    print('COOL_STRICT',len(out),sum(x['char_count'] for x in out),flush=True)
    return out


RUAN_DIRS={'opinions','essays','startup','sci-tech','literature','misc','notes'}
RUAN_TITLE_EXCLUDE=re.compile(r'译文|翻译|书摘|摘录|演讲全文|判决书|遗书|捐款|救救|探望白血病|征集|广告|教程|算法|语法|函数|源码|安装|下载|资源汇总|书目|歌词|一首歌',re.I)
RUAN_RAW_EXCLUDE=re.compile(r'文章来源\s*[:：]|本文译自|译者\s*[:：]|翻译自|转载自|转自\s+https?://',re.I)

def gather_ruan():
    out=[]; seen=set()
    root=SOURCE_REPO/'ruanyifeng'
    for p in root.rglob('*.rst'):
        rel=p.relative_to(root)
        if not rel.parts or rel.parts[0] not in RUAN_DIRS: continue
        raw=p.read_text(encoding='utf-8',errors='ignore')
        if not (p.name.startswith('2010') or re.search(r'2010年\d{1,2}月\d{1,2}日',raw[:1800])): continue
        title,_,official,body=clean_rst_strict(raw)
        if not title or not official or RUAN_TITLE_EXCLUDE.search(title) or RUAN_RAW_EXCLUDE.search(raw[:2500]): continue
        if count_chars(body)<650 or zh_ratio(body)<.62: continue
        # Exclude posts dominated by quoted English or externally authored appendices.
        eng=len(re.findall(r'[A-Za-z]',body)); compact=max(count_chars(body),1)
        if eng/compact>.18: continue
        if rel.parts[0] in {'sci-tech','notes','misc'} and opinion_score(title,body,str(p))<2.0: continue
        k=official.replace('http://','https://')
        if k in seen: continue
        x=make(p,'阮一峰的网络日志','阮一峰',
               'CC BY-NC-ND 3.0: verbatim main-body reproduction in a noncommercial collection; no textual rewriting',
               'https://www.ruanyifeng.com/blog/2008/04/creative_commons_licenses.html',
               '正文句子未改写；仅分离网页/RST 元数据与正文。按非商业、署名、禁止演绎条件使用。',minscore=-1.5)
        if x: seen.add(k); out.append(x)
    print('RUAN_STRICT',len(out),sum(x['char_count'] for x in out),flush=True)
    for x in sorted(out,key=lambda z:z['title']): print('R',x['char_count'],x['title'],flush=True)
    return out


def gather_pongba():
    out=[]
    root=SOURCE_REPO/'pongba'/'allpapers'
    for p in sorted(root.glob('2010*.rst')):
        raw=p.read_text(encoding='utf-8',errors='ignore')
        if RUAN_RAW_EXCLUDE.search(raw[:2000]) or re.search(r'译文|翻译|转载',raw[:1000]): continue
        x=make(p,'刘未鹏 | Mind Hacks','刘未鹏','Article-level repost permission: retain author, source and original hyperlink',
               'https://mindhacks.cn/','原文页要求转载注明作者、出处及原始超链接；上述信息保留在 Excel 与 manifest。',minscore=-4)
        if x: out.append(x)
    print('PONGBA',len(out),sum(x['char_count'] for x in out),flush=True)
    return out


def dedupe(items):
    out=[]; urls=set(); hs=set()
    for x in items:
        h=hashlib.sha256(re.sub(r'\s+','',x['body']).encode()).hexdigest()
        if x['official_url'] in urls or h in hs or x['char_count']>18000: continue
        urls.add(x['official_url']); hs.add(h); out.append(x)
    return out


def select(items):
    # Dynamic programming subset sum in 10-character buckets, with source/topic quality bonuses.
    # First seed at least one document per available source, then optimize closeness to target.
    items=sorted(items,key=lambda x:(-x['quality_score'],-x['char_count']))
    # DP: bucket -> tuple(score, indices). Limit states near useful range.
    states={0:(0.0,())}
    for idx,x in enumerate(items):
        w=max(1,round(x['char_count']/10))
        bonus=x['quality_score']+1.2
        updates={}
        for total,(score,inds) in list(states.items()):
            nt=total+w
            if nt>round((UPPER+1500)/10): continue
            ns=score+bonus
            if nt not in states or ns>states[nt][0]: updates[nt]=(ns,inds+(idx,))
        for k,v in updates.items():
            if k not in states or v[0]>states[k][0]: states[k]=v
    viable=[(abs(k*10-TARGET),-v[0],k,v) for k,v in states.items() if LOWER<=k*10<=UPPER]
    if not viable:
        viable=[(abs(k*10-TARGET),-v[0],k,v) for k,v in states.items()]
    _,_,k,best=min(viable)
    chosen=[items[i] for i in best[1]]
    # Source diversity: if a source is absent, attempt a low-impact swap.
    available=set(x['source_site'] for x in items); present=set(x['source_site'] for x in chosen)
    for src in available-present:
        cand=max((x for x in items if x['source_site']==src),key=lambda x:x['quality_score'],default=None)
        if not cand: continue
        cur=sum(x['char_count'] for x in chosen)
        swaps=sorted(chosen,key=lambda old:abs((cur-old['char_count']+cand['char_count'])-TARGET))
        for old in swaps:
            nt=cur-old['char_count']+cand['char_count']
            if LOWER<=nt<=UPPER:
                chosen.remove(old); chosen.append(cand); break
    chosen=sorted(chosen,key=lambda x:(x['source_site'],x['topic'],x['title']))
    print('SELECTED',len(chosen),sum(x['char_count'] for x in chosen),Counter(x['source_site'] for x in chosen),flush=True)
    return chosen


def write(selected,candidates):
    if OUT.exists(): shutil.rmtree(OUT)
    TXT_DIR.mkdir(parents=True)
    rows=[]; merged=[]; total=0
    for i,x in enumerate(selected,1):
        tid=f'2010_O_{i:03d}'; fn=f"{tid}_{safe_slug(x['title'])}_cleaned.txt"; body=normalize(x['body']); cc=count_chars(body)
        (TXT_DIR/fn).write_text(body+'\n',encoding='utf-8'); merged.append(body); total+=cc
        r={k:v for k,v in x.items() if k!='body'}; r.update({'id':i,'text_id':tid,'bin':'bin01','first_publication_year':2010,'language':'simplified','char_count':cc,'ocr_quality':'copiable','filename':fn}); rows.append(r)
    (OUT/'2010_O_all_cleaned.txt').write_text('\n\n'.join(merged)+'\n',encoding='utf-8')
    payload={'year':2010,'target_chars':TARGET,'actual_chars':total,'count_method':'Unicode characters excluding whitespace','article_count':len(rows),'sources':dict(Counter(x['source_site'] for x in selected)),'source_chars':{s:sum(x['char_count'] for x in selected if x['source_site']==s) for s in sorted(set(x['source_site'] for x in selected))},'topics':dict(Counter(x['topic'] for x in selected)),'rows':rows}
    (OUT/'manifest.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'candidate_audit.json').write_text(json.dumps([{k:v for k,v in x.items() if k!='body'} for x in candidates],ensure_ascii=False,indent=2),encoding='utf-8')
    ad=OUT/'candidate_texts'; ad.mkdir()
    for j,x in enumerate(sorted(candidates,key=lambda z:(z['source_site'],z['title'])),1): (ad/f"{j:03d}_{safe_slug(x['source_site'])}_{safe_slug(x['title'])}.txt").write_text(x['body']+'\n',encoding='utf-8')
    lic=f'''2010_O 版权与清洗说明\n\n用途：非商业学术语料研究。\n实际正文字符数：{total:,}（排除空格、制表符与换行）。\n文章数量：{len(rows)}。\n\n来源及授权：\n1. CoolShell：官方说明允许转载，须保留作者和原始出处。https://coolshell.cn/about\n2. 阮一峰的网络日志：自由转载—非商用—非衍生—保持署名。正文原句未改写，仅分离网页/RST 元数据。https://www.ruanyifeng.com/blog/2008/04/creative_commons_licenses.html\n3. 刘未鹏 | Mind Hacks：原文页要求转载时注明作者、出处和原始超链接；相关信息保留于 Excel 与 manifest。\n\n筛选：排除明显外文翻译、第三方全文转载、纯教程、新闻摘编和版权边界不清的文章。\n清洗：排除标题、作者/日期行、导航、标签、广告、图表/图片说明、代码块、评论区、相关推荐、参考资料/参考文献和编辑说明；删除数字型引用标记与网页链接语法。正文句子、段落顺序和标点尽量保持原样。\n\n本包不得商用。任何再分发必须保留作者、官方链接和版权状态；阮一峰文本不得改写或演绎。\n'''
    (OUT/'LICENSE_AND_CLEANING.txt').write_text(lic,encoding='utf-8')
    summary={'actual_chars':total,'article_count':len(rows),'within_target_band':LOWER<=total<=UPPER,'sources':payload['sources'],'source_chars':payload['source_chars'],'topics':payload['topics']}
    (OUT/'build_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print('FINAL',json.dumps(summary,ensure_ascii=False),flush=True)
    if not LOWER<=total<=UPPER: raise SystemExit(f'target failed {total}')


def main():
    if not SOURCE_REPO.exists(): subprocess.run(['git','clone','--depth','1','https://github.com/me115/read.git',str(SOURCE_REPO)],check=True)
    candidates=dedupe(gather_cool()+gather_ruan()+gather_pongba())
    print('CANDIDATES',len(candidates),sum(x['char_count'] for x in candidates),flush=True)
    write(select(candidates),candidates)

if __name__=='__main__': main()
