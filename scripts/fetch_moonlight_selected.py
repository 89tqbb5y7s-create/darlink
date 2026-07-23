#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, re, unicodedata
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import trafilatura

URLS=[
 'https://www.williamlong.info/archives/2380.html',
 'https://www.williamlong.info/archives/2375.html',
 'https://www.williamlong.info/archives/2336.html',
]
OUT=Path('out_moon')
OUT.mkdir(exist_ok=True)
S=requests.Session(); S.headers.update({'User-Agent':'Mozilla/5.0 academic-corpus/1.0','Accept-Language':'zh-CN,zh;q=0.9'})

def norm(t):
 t=unicodedata.normalize('NFKC',t).replace('\r\n','\n').replace('\r','\n').replace('\xa0',' ')
 t=re.sub(r'https?://\S+','',t)
 t=re.sub(r'\n{3,}','\n\n',t); t=re.sub(r'[ \t]+',' ',t); t=re.sub(r' *\n *','\n',t)
 return t.strip()

def count(t): return len(re.sub(r'\s+','',t))

def extract(url):
 r=S.get(url,timeout=40); print('GET',r.status_code,len(r.content),url,flush=True); r.raise_for_status()
 if not r.encoding or r.encoding.lower()=='iso-8859-1': r.encoding=r.apparent_encoding or 'utf-8'
 soup=BeautifulSoup(r.text,'lxml')
 h1=soup.find('h1'); title=h1.get_text(' ',strip=True) if h1 else soup.title.get_text(' ',strip=True).split('-')[0]
 page=soup.get_text(' ',strip=True)
 date=re.search(r'(2010-\d{1,2}-\d{1,2})',page)
 if not date or not re.search(r'作者\s*[:：]\s*月光',page): raise RuntimeError('year/author check failed')
 text=trafilatura.extract(r.text,include_comments=False,include_tables=False,include_images=False,include_links=False,favor_precision=True,output_format='txt',deduplicate=True)
 if not text: raise RuntimeError('trafilatura empty')
 lines=[]; started=False
 for line in text.splitlines():
  s=line.strip()
  if not s: 
   if started: lines.append('')
   continue
  if s==title: started=True; continue
  if not started:
   # trafilatura sometimes omits title and starts directly with metadata/body
   if re.search(r'2010-\d{1,2}-\d{1,2}',s) or s.startswith('月光博客'): continue
   started=True
  if re.match(r'^2010-\d{1,2}-\d{1,2}',s): continue
  if re.match(r'^(?:作者|分类|评论|浏览)\s*[:：]',s): continue
  if re.search(r'顶一下|踩一下|上一篇|下一篇|相关文章|订阅博客|网站分类|热文排行|控制面板',s): break
  if s.startswith('Image:') or re.search(r'点击图片(?:放大|可放大)?$',s): continue
  if re.match(r'^(?:首发|本文链接|转载请注明)\s*[:：]',s): continue
  s=re.sub(r'\[(?:\d{1,3})(?:[-–,，]\d{1,3})*\]','',s)
  if s: lines.append(s)
 body=norm('\n'.join(lines))
 if body.startswith(title): body=norm(body[len(title):])
 if count(body)<800: raise RuntimeError(f'body too short {count(body)}')
 return {'title':title,'author':'月光','official_url':url,'year':2010,'body':body,'char_count':count(body),'source_site':'月光博客','topic':'互联网与平台','copyright_status':'CC BY-NC-SA','license_url':'https://www.williamlong.info/archives/480.html'}

rows=[]
for u in URLS:
 try:
  x=extract(u); rows.append(x); (OUT/(re.sub(r'[^0-9A-Za-z\u3400-\u9fff]+','_',x['title']).strip('_')+'.txt')).write_text(x['body']+'\n',encoding='utf-8'); print('OK',x['char_count'],x['title'],flush=True)
 except Exception as e: print('FAIL',u,repr(e),flush=True)
(OUT/'moon_manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print('TOTAL',len(rows),sum(x['char_count'] for x in rows),flush=True)
if len(rows)<2: raise SystemExit('not enough pages extracted')
