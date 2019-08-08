'''
此脚本中有的函数仅仅适用于.shtml后缀网站链接
'''

import requests
import time
from requests.exceptions import Timeout,ConnectionError
from lxml import etree
import pymysql
import redis
import hashlib
import re

'''
适用于.shtml后缀网站链接
'''

# 定义请求头
headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
    "Accept-Encoding": "gzip, deflate",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Host": "",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36"
    }

# 连接数据库
def con_mysql():
    # db = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', db='litianming', charset='utf8')
    db = pymysql.connect(host='117.50.3.204', port=3306, user='wh_court', password='Liruijing!123', db='adjudicative', charset='utf8')
    cursor = db.cursor()
    return db,cursor

# 关闭数据库
def clo_mysql(db,cursor):
    cursor.close()
    db.close()

# 数据的插入,d为一条记录，字典形式，table为表名
def ins_mysql(d,table,db,cursor):
    # 删除没有值的字段
    l = []
    for i in d.keys():
        if d[i] == '':
            l.append(i)
    for i in l:
        del d[i]

    # 准备入库
    keys = ','.join(d.keys())
    values = ','.join(['%s'] * len(d))
    sql = "INSERT INTO {table}({keys}) VALUES({values})".format(table = table,keys = keys,values = values)
    try:
        cursor.execute(sql,tuple(d.values()))
        db.commit()
    except:
        db.rollback()

# 一级页面的请求，url为起始链接,i为页数
def request(url,i):
    # 提取域名，构建请求头
    host = re.findall('//(.*?)/',url)[0]
    headers['Host'] = host

    # 构建请求链接
    if i == 1:
        r_url = url
    else:
        r_url = url.replace('.shtml','/page/') + str(i) + '.shtml'
    # 进行请求，做一个异常处理
    while True:
        try:
            r = requests.get(r_url,headers=headers,timeout=3.05)
            r.encoding = 'utf8'
            html = r.text
        except (Timeout,ConnectionError):
            continue
        break
    return html

# 解析响应文本匹配出每一条信息的详细页面,html为解析文本，xp为链接提取器
def parse(html,xp,biaoshi):
    links = []
    text = etree.HTML(html)
    urls = text.xpath(xp + '/@href')
    names = text.xpath(xp + '/text()')
    for x,y in zip(names,urls):
        for s in biaoshi:
            if s in x:       
                links.append(y)
                break
    return links

# 获取详情页的文本,url为详情页链接，xp为文本提取器
def request_dis(url,xp=None):
    if xp == None:
        xp = '//div[@class="text"]'
    while True:
        try:
            re = requests.get(url,headers=headers,timeout=3.05)
            re.encoding = 'utf8'
            html = re.text
        except (Timeout,ConnectionError):
            continue
        break
    text = etree.HTML(html)
    content = text.xpath(xp)
    try:
        info = content[0].xpath('string(.)')
    except IndexError:
        return (0,0)
    else:
        return (info,html)

# 同步数据库的案由并且返回案由列表
def syn_anyou(): 
    # 从mysql里面取出所有的案由
    conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', db='litianming', charset='utf8')
    cursor = conn.cursor()
    sql = 'select (anyou) from anyou'
    cursor.execute(sql)
    rows = cursor.fetchall()
    anyou = list(a[0] for a in rows)

    # 同步到redis中去
    r = redis.Redis(host='127.0.0.1',port=6379,db=0)
    if 'anyou' in r.keys():
        r.delete('anyou')
    for a in anyou:
        r.lpush('anyou',a)

# 获取案由列表
def set_anyou():
    r = redis.Redis(host='127.0.0.1',port=6379,db=0)
    anyou = r.lrange('anyou',0,-1)
    ay = [i.decode('utf-8') for i in anyou]
    return ay

# 返回案由
def get_anyou(body):
    start = 0
    end = 0
    anyou = set_anyou()
    for ay in anyou:
        if ay in body:
            num = body.find(ay)
            if start == 0 or num <= start:
                start = num
            if num + len(ay) >= end:
                end = num + len(ay)
    anyou = body[start:end]
    return anyou

# 获取原告和被告,res为匹配原告和被告的正则表达式
def get_party(res,body,anyou):
    for i in res:
        party = re.findall(i,body)
        if party:
            party = party[0]
            if type(party) is str:
                plaintiff = ''
                pname = re.findall('(.*?)%s' % anyou,party)[0]
            else:
                plaintiff = party[0]
                pname = re.findall('(.*?)%s' % anyou,party[1])[0]
            break
    else:
        return (None,None)
    return (plaintiff,pname)

# 对原告和被告进行进一步的清洗
def qingxi_party(tihuan,party):
    for i in tihuan:
        party = party.replace(i,'')
    return party

# 获取MD5
def get_md5(body,url):
    md5 = hashlib.md5()
    md5.update((body+url).encode())
    md = md5.hexdigest()
    return md

# 写文本信息
def write_txt(name,text):
    with open(name + '.txt','a',encoding='utf-8') as f:
        f.write(text)
        f.write('\n')
        f.write('---------------------')
        f.write('\n')

# 获取时间
def get_str(res,body):
    if type(res) is str:
        res = [res]
    for i in res:
        sorttime = re.findall(i,body)
        if sorttime:
            t = sorttime[0]
            break
    else:
        return
    return t

# 定义切割时间的字符
split_str = ['年','月','日','号','-','.']

# 定义格式化时间的字符
f_time = ['零','〇','○','一','二','四','五','六','七','八','九','十']

times = '2018.10.8'

# 格式化时间
def format_time(time_str):
    # 构建切割字符串
    string = ''
    for i in split_str:
        if i in time_str:
            string += i
    # 对时间进行切割
    time_list = re.split('['+ string +']',time_str)
    time_list = list(filter(None,time_list))
    for i in time_list:
        