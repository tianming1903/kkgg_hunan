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
        # 起始url 
        self.url = "http://czyxfy.chinacourt.gov.cn/public/more.php?p=0&LocationID=0301000000&sub="

        # 定义请求头
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Host": "czyxfy.chinacourt.gov.cn",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36",
        }

        # 定义过滤非开庭公告的信息
        self.filter = ['诉','审理']
        
        # 定义获取party的re表达式
        self.party = [
            '审理(.*?)诉(.*)',
            '审理(.*?)与(.*)',
            '审理(.*)',
            '(.*?)诉(.*?)一案',
            '(.*?)一案'
        ]

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
            time.sleep(0.5)
        print('请求到详情页数量是: ' + str(len(links_list)))
        return links_list

    def parse_html(self,links):
        # 连接数据库
        db,cursor = ktgg.con_mysql()
        for i in links:
            d = {}
            url = 'http://czyxfy.chinacourt.gov.cn' + i
            print(url)
            while True:
                try:
                    res = requests.get(url,headers=self.headers,timeout=3.05)
                    res.encoding = 'gb18030'
                    html = res.text
                except (Timeout,ConnectionError):
                    continue
                break
            # 提取一些公共信息
            text = etree.HTML(html)
            try:
                d['court'] = '永兴人名法院'
                d['source'] = self.url
                d['url'] = url
                d['title'] = text.xpath('//p[@align="center"]//b/text()')[0]
                d['posttime'] = text.xpath('//p[@align="center"]/text()')[0].split('：')[1]
                d['province'] = '湖南省'
            except IndexError:
                continue
            self.parse_text(d,db,cursor)

        # 关闭数据库
        ktgg.clo_mysql(db,cursor)

    def parse_text(self,d,db,cursor):
            # 提取详细信息
            d['body'] = d['title']
            # 提取开庭地点
            sorttime = re.findall('\d{1,4}[年月].*?[日号]',d['title'])
            if sorttime:
                d['sorttime'] = sorttime[0]
            # 提取开庭时间
            courtNum = re.findall('第.{1,4}庭',d['title'])
            if courtNum:
                d['courtNum'] = courtNum[0]
            # 提取案由和被告以及原告
            for i in self.party:
                try:
                    party = re.findall(i,d['title'])[0]
                except IndexError:
                    continue
                else:
                    anyou = ktgg.set_anyou()
                    if type(party) is str:
                        start,end = ktgg.search_anyou(anyou,party)
                        if start == 0:
                            return
                        d['anyou'] = party[start:end]
                        d['pname'] = re.findall('(.*?)%s' % d['anyou'],party)[0].replace('被告人','').replace('被告','')
                    elif type(party) is tuple:
                        start,end = ktgg.search_anyou(anyou,party[1])
                        if start == 0:
                            return
                        d['anyou'] = party[1][start:end]
                        d['plaintiff'] = party[0].replace('原告人','').replace('原告','')
                        d['pname'] = re.findall('(.*?)%s' % d['anyou'],party[1])[0].replace('被告人','').replace('被告','')
                break
            d['md5'] = ktgg.get_md5(d['body'],d['url'])
            ktgg.ins_mysql(d,'ktgg_kt_wuhan',db,cursor)
            time.sleep(0.5)

    def main(self):
        links = self.qingqiu()
        self.parse_html(links)

if __name__ == "__main__":
    kh = Ktgg_hunan()
    kh.main()

