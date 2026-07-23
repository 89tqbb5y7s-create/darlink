#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import concurrent.futures
import hashlib
import re
import subprocess
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
import trafilatura

from corpus_2010_o_temp import SOURCE_REPO, topic_of
from corpus_2010_o_temp_v4 import (
    count_chars, normalize, zh_ratio, opinion_score, gather_cool, gather_ruan,
    gather_pongba, dedupe, select, write,
)

SESSION=requests.Session()
SESSION.headers.update({'User-Agent':'Mozilla/5.0 (compatible; noncommercial-academic-corpus/1.0)','Accept-Language':'zh-CN,zh;q=0.9'})

MOON_INDEX='https://www.williamlong.info/archives/2468.html'
MOON_LICENSE='https://www.williamlong.info/archives/480.html'
MOON_EXCLUDE=re.compile(r'年度流量|数据统计|推荐阅读文章|新闻搜索排行榜|大事记|软件下载|下载|安装|配置|教程|通知|投放广告|优惠|活动|获奖名单|正式发布|上线$',re.I)
MOON_POS=re.compile(r'评论|评测|质疑|读后感|思考|观察|分析|盘点|看法|建议|隐私|版权|营销|社会|管理|互联网|软件|搜索|博客|地图|游戏|知识|安全|商业|网站|Google|谷歌|百度|腾讯|360|苹果|微软|微博|用户')
MOON_BODY=re.compile(r'我认为|我觉得|在我看来|我的看法|值得|应该|不应该|问题|原因|建议|可以看出|这说明|遗憾|质疑|评论|分析')


def get(url,tries=3):
    for i in range(tries):
        try:
            r=SESSION.get(url,timeout=35,allow_redirects=True)
            if r.status_code==200 and r.content:
                if not r.encoding or r.encoding.lower()=='iso-8859-1': r.encoding=r.apparent_encoding or 'utf-8'
                return r
            print('HTTP',r.status_code,url,flush=True)
        except Exception as e: print('ERR',type(e).__name__,url,flush=True)
        time.sleep(1+i)
    return None


def clean_trafilatura(html_text,title):
    text=trafilatura.extract(html_text,include_comments=False,include_tables=False,include_images=False,include_links=False,
                             favor_precision=True,output_format='txt',deduplicate=True)
    if not text: return ''
    lines=[]; seen=set()
    for line in text.splitlines():
        s=line.strip()
        if not s: lines.append(''); continue
        if s==title or re.match(r'^2010[-/.年]\d{1,2}',s): continue
        if re.match(r'^(?:作者|分类|标签|评论|浏览|发布时间|日期)[:：]',s): continue
        if re.match(r'^(?:本文链接|原文链接|相关文章|相关阅读|欢迎发表评论|版权声明|转载请注明)[:：]?',s): break
        if re.fullmatch(r'(?:上一篇|下一篇|返回首页|月光博客)',s): continue
        s=re.sub(r'https?://\S+','',s)
        s=re.sub(r'\[(?:\d{1,3})(?:[-–,，]\d{1,3})*\]','',s)
        key=re.sub(r'\s+','',s)
        if key and key in seen: continue
        if key: seen.add(key)
        lines.append(s)
    return normalize('\n'.join(lines))


def parse_page(url):
    r=get(url)
    if not r: return None
    soup=BeautifulSoup(r.text,'lxml')
    h1=soup.find('h1')
    title=h1.get_text(' ',strip=True) if h1 else ''
    if not title and soup.title: title=re.split(r'[-_|—]',soup.title.get_text(' ',strip=True))[0].strip()
    page_text=soup.get_text(' ',strip=True)
    if not re.search(r'2010年\d{1,2}月\d{1,2}日|2010-\d{1,2}-\d{1,2}',page_text): return None
    if not re.search(r'作者\s*[:：]\s*月光',page_text): return None
    if not title or MOON_EXCLUDE.search(title): return None
    body=clean_trafilatura(r.text,title)
    if count_chars(body)<800 or count_chars(body)>12000 or zh_ratio(body)<.65: return None
    score=opinion_score(title,body,url)
    if not MOON_POS.search(title) and len(MOON_BODY.findall(body[:7000]))<3: return None
    if score<1.2: return None
    # Exclude clearly syndicated/guest pieces despite author metadata anomalies.
    if re.search(r'投稿|供稿|作者为|本文作者|转载自|译者',body[:800]): return None
    return {'title':title,'author':'月光','official_url':url,'mirror_source':url,'source_site':'月光博客','body':body,
            'char_count':count_chars(body),'topic':topic_of(title,body),'quality_score':round(score+0.8,2),
            'copyright_status':'CC BY-NC-SA (署名-非商业性使用-相同方式共享)',
            'license_url':MOON_LICENSE,
            'notes':'来自作者本人列出的2010年推荐阅读文章；仅保留评论/评测正文，排除导航、标题、作者日期、图注、评论区和相关推荐。'}


def gather_moon():
    r=get(MOON_INDEX)
    if not r: return []
    soup=BeautifulSoup(r.text,'lxml')
    links=[]
    for a in soup.find_all('a',href=True):
        u=urljoin(MOON_INDEX,a['href'])
        if re.match(r'https?://(?:www\.)?williamlong\.info/archives/\d+\.html$',u) and u!=MOON_INDEX:
            links.append(u.replace('http://','https://'))
    links=list(dict.fromkeys(links))
    print('MOON_LINKS',len(links),flush=True)
    out=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futs={ex.submit(parse_page,u):u for u in links}
        for fut in concurrent.futures.as_completed(futs):
            try:
                x=fut.result()
                if x: out.append(x)
            except Exception as e: print('PARSE',futs[fut],repr(e),flush=True)
    # exact dedupe
    uniq={}
    for x in out: uniq[hashlib.sha256(re.sub(r'\s+','',x['body']).encode()).hexdigest()]=x
    out=list(uniq.values())
    print('MOON',len(out),sum(x['char_count'] for x in out),flush=True)
    for x in sorted(out,key=lambda z:z['title']): print('M',x['char_count'],x['title'],flush=True)
    return out


def main():
    if not SOURCE_REPO.exists(): subprocess.run(['git','clone','--depth','1','https://github.com/me115/read.git',str(SOURCE_REPO)],check=True)
    candidates=dedupe(gather_cool()+gather_ruan()+gather_pongba()+gather_moon())
    print('CANDIDATES_V5',len(candidates),sum(x['char_count'] for x in candidates),flush=True)
    chosen=select(candidates)
    write(chosen,candidates)

if __name__=='__main__': main()
