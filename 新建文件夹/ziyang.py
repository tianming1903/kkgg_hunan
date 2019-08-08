'''
此代码爬取湖南的开庭公告，
'''
import requests
import time
from requests.exceptions import Timeout,ConnectionError
from lxml import etree
import pymysql
import redis
import hashlib
import re
import ktgg
import sys


class Ktgg_hunan():
    def __init__(self):
        # 定义被告人替换字符
        self.p = [
            '（市看）','（在押）','（女看）','人','被告','单位','(市看）','（二看）','（取保）','（女）'
        ]
        # 起始url 
        self.url = "http://zyqfy.chinacourt.gov.cn/swgk/more.php?p=0&LocationID=0301000000&sub="

        # 定义请求头
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Host": "zyqfy.chinacourt.gov.cn",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36",
        }

        # 定义过滤非开庭公告的信息
        self.filter = ['开庭','审理']

    # 获取每个详情页的链接
    def qingqiu(self):
        links_list = []
        i = 1
        print('开始请求一级页面.....')
        while True:
            url = self.url.replace('p=0','p=' + str(i))
            try:
                r = requests.get(url,headers=self.headers,timeout=3.05)
                r.encoding = 'gb18030'
                html = r.text
                if len(html) <= 200:
                    sys.exit('程序终止')
            except (Timeout,ConnectionError):
                continue

            # xpath匹配出链接和文本
            text = etree.HTML(html)
            links = text.xpath('//tr[contains(@class,"tr_")]/td[@class="td_line"]/a/@href')
            names = text.xpath('//tr[contains(@class,"tr_")]/td[@class="td_line"]/a/text()')
            for x,y in zip(links,names):
                for f in self.filter:
                    if f in y:
                        links_list.append(x)
                        break
            # 获取页数作为停止请求的条件
            num = text.xpath('//td[@class="td_pagebar"]/font/text()')[1]
            if i == int(num):
                break
            i += 1
            time.sleep(1)    
        print('请求到详情页数量是: ' + str(len(links_list)))
        return links_list

    def parse_html(self,links):
        # 连接数据库
        db,cursor = ktgg.con_mysql()
        for i in links:
            d = {}
            url = 'http://zyqfy.chinacourt.gov.cn' + i
            while True:
                try:
                    res = requests.get(url,headers=self.headers,timeout=3.05)
                    res.encoding = 'gb18030'
                    html = res.text
                except (Timeout,ConnectionError):
                    continue
                break

            # 获取所有的文本内容
            text = etree.HTML(html)
            content = text.xpath('//span[@class="detail_content"]')
            if content == []:
                continue

            # 提取一些公共信息
            d['court'] = '资阳区人名法院'
            d['source'] = self.url
            d['url'] = url
            d['title'] = text.xpath('//p[@align="center"]//b/text()')[0]
            d['posttime'] = text.xpath('//p[@align="center"]/text()')[0].split('：')[1]
            d['province'] = '湖南省'
            
            # 格式化文本
            info = []
            t = content[0].xpath('./text()')
            if t:
                info.append(t[0].replace('\xa0',''))
            for i in content[0].xpath('./p/text()'):
                info.append(i.replace('\xa0',''))
            for i in content[0].xpath('./font/text()'):
                info.append(i.replace('\xa0',''))
            if info == []:
                info = [d['title']]
            self.parse_text(info,d,db,cursor)
            time.sleep(1)

        # 关闭数据库
        ktgg.clo_mysql(db,cursor)

    def parse_text(self,text,d,db,cursor):
        if text[0][-2:] == '审理':
            text = [text[0] + text[1]]
        for info in text:
            if len(info) <= 30:
                continue
            d['body'] = info
            d['sorttime'] = ''
            d['courtNum'] = ''
            d['anyou'] = ''
            d['pname'] = ''
            d['plaintiff'] = ''
            
            # 获取开庭时间
            sorttime = re.findall('\d{2,4}[年月].*?[日号]',info)
            if sorttime:
                d['sorttime'] = sorttime[0]
            
            # 获取开庭地点
            courtNum = re.findall('第.*?庭',info)
            if courtNum:
                d['courtNum'] = ','.join(courtNum)
            
            # 获取被告和案由的文本
            p = re.findall('被告.*?[罪案，。]',info)
            if not p:
                continue

            # 获取案由
            anyou = ktgg.set_anyou()
            L = []
            for x in p:
                l = []
                for ay in anyou:
                    if ay in x:
                        l.append(ay)
                if l == []:
                    L.append('')
                    continue
                l.sort(reverse=True,key=len)
                L.append(l[0])
            d['anyou'] = ','.join(L)

            # 获取被告
            pnames = []
            for x,y in zip(p,L):
                if y == '':
                    continue
                pname = re.findall('被告(.*?)%s' % y,x)[0]
                for i in self.p:
                    pname = pname.replace(i,'')
                pnames.append(pname)
            d['pname'] = ','.join(pnames)
            print(d['pname'])

            # 获取原告
            plaintiff = re.findall('原告(.*?)[诉与]',info)
            if plaintiff:
                d['plaintiff'] = plaintiff[0]

            d['md5'] = ktgg.get_md5(info,d['url'])
            ktgg.ins_mysql(d,'ktgg_kt_wuhan',db,cursor)

    def main(self):
        links = self.qingqiu()
        self.parse_html(links)

if __name__ == "__main__":
    kh = Ktgg_hunan()
    kh.main()

