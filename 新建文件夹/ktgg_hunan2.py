'''
此代码爬取湖南的开庭公告，
'''

import requests
import time
from requests.exceptions import Timeout,ConnectionError
from lxml import etree
import pymysql
import re
import redis
import hashlib

class Ktgg_hunan(object):
    def __init__(self):
        # 链接mysql数据库
        self.db = pymysql.connect(host="localhost",user="root",password="123456",db='litianming')
        self.cursor = self.db.cursor()

        # 定义正则表达式
        self.re = [
            ]

        self.re1 = [
            
            ]
        
        self.re2 = [
           
        ]
        
        # 定义案由
        self.anyou = ''

        # 定义去除详情页非数据标识
        self.biaoshi = ['纠纷','争议','诉','排期开庭']

        # 定义请求头headers
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Host": "wcxfy.chinacourt.gov.cn",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36",
            }

        # 起始url 
        self.url = "http://wcxfy.chinacourt.gov.cn/article/index/id/M0guNTBINTAwNCACAAA/page/1.shtml"

    # 获取所有的案由
    def set_anyou(self):
        r = redis.Redis(host='127.0.0.1',port=6379,db=0)
        self.anyou = r.lrange('anyou', 0, -1)

    # 构建一级链接请求并且请求获得响应
    def set_request(self):
        print('正在获取详情页链接....')
        # 更改起始页
        i = 1
        link_list = []
        while True:
            new = str(i) + '.shtml'
            old = self.url.split('/')[-1]
            url = self.url.replace(old,new)
            try:
                re = requests.get(url,headers=self.headers,timeout=3.05)
                re.encoding = 'utf8'
                html = re.text
            except (Timeout,ConnectionError):
                continue
            text = etree.HTML(html)
            urls = text.xpath('//div[@class="list_br"]//li//a/@href')
            names = text.xpath('//div[@class="list_br"]//li//a/text()')
            for x,y in zip(names,urls):
                for s in self.biaoshi:
                    if s in x:
                        link_list.append(y)
                        break
            if not text.xpath('//div[@class="paginationControl"]'):
                break
            i += 1
        print('详情链接请求到的个数有: ' + str(len(link_list)))
        return link_list

    # 进行详情页的请求并且解析
    def request_info(self,links):
        for i in links:
            d = {}
            url = 'http://kfqfy.chinacourt.gov.cn' + i
            while True:
                try:
                    re = requests.get(url,headers=self.headers,timeout=3.05)
                    re.encoding = 'utf8'
                    html = re.text
                except (Timeout,ConnectionError):
                    continue
                break

            # 获取所有的文本内容
            text = etree.HTML(html)
            content = text.xpath('//div[@class="text"]')
            if content == []:
                continue
            info = content[0].xpath('string(.)')

            # 先获取一些字段
            d['source'] = self.url
            d['url'] = url
            d['title'] = text.xpath('//div[@class="b_title"]/text()')[0]
            d['court'] = '湖南省长沙市望城区人民法院'
            d['posttime'] = text.xpath('//div[@class="sth_a"]/span[1]/text()')[0].strip().split('：')[-1]
            d['province'] = '湖南省'
            self.parse(info,d)

    # 解析文本提取字段
    def parse(self,info,d):
            if 
            # self.insert_mysql(d)
            
    # 对数据的入库和清洗
    def insert_mysql(self,d):
        # 删除没有值的字段
        l = []
        for i in d.keys():
            if d[i] == '':
                l.append(i)
        for i in l:
            del d[i]

        # 准备入库
        table = 'ktgg_hunan1'
        keys = ','.join(d.keys())
        values = ','.join(['%s'] * len(d))
        sql = "INSERT INTO {table}({keys}) VALUES({values})".format(table = table,keys = keys,values = values)
        try:
            self.cursor.execute(sql,tuple(d.values()))
            self.db.commit()
        except:
            self.db.rollback()
    
    def close_mysql(self):
        self.cursor.close()
        self.db.close()

    # 函数的控制
    def main(self):
        self.set_anyou()
        links = self.set_request()
        self.request_info(links)
        self.close_mysql()

if __name__ == "__main__":
    kh = Ktgg_hunan()
    kh.main()
