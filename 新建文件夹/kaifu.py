w'''
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
        self.re = {
            1: '原告(.*?)被告(.*?)案由(.*?)审判员(.*?)代理.*?开庭时间(.*?)开庭地点(.*)',
            2: '原告(.*?)被告(.*?)案由(.*?)审判员(.*?)书记.*?开庭时间(.*?)开庭地点(.*)',
            3: '原告(.*?)被告(.*?)案由(.*?)审判员(.*?)开庭时间(.*?)开庭地点(.*)',
            4: '原告(.*?)被告(.*?)案由(.*?)开庭时间(.*?)开庭地点(.*?)审判员(.*)',
            5: '原告(.*?)被告(.*?)开庭时间(.*?)开庭地点(.*?)审判员(.*)',
        }

        self.re1 = [
            '于(.*?)\\d{1,2}:\\d{1,2}在(.*?)开庭审理(.*?)诉(.*?)%s',
            '院(.*?)\\d{1,2}:\\d{1,2}在(.*?)开庭审理(.*?)诉(.*?)%s',
            '于(.*?)\\d{1,2}:\\d{1,2}(.*?)开庭审理(.*?)诉(.*?)%s',
            '院(.*?)\\d{1,2}:\\d{1,2}(.*?)开庭审理(.*?)诉(.*?)%s',
            '院(.*?):\\d{1,2}(.*?)开庭审理(.*?)诉(.*?)%s',
            ]
        
        self.re2 = [
            '于(.*?)\\d{1,2}:\\d{1,2}在(.*?)开庭审理(.*?)%s',
            '院(.*?)\\d{1,2}:\\d{1,2}在(.*?)开庭审理(.*?)%s',
        ]
        
        # 定义案由
        self.anyou = ''

        # 定义去除详情页非数据标识
        self.biaoshi = ['纠纷','争议','诉','开民','开庭公告']

        # 定义请求头headers
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            "Accept-Encoding": "gzip, deflate",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Host": "kfqfy.chinacourt.gov.cn",
            "Upgrade-Insecure-Requests": "1",
            }

        # 起始url 
        self.url = "http://kfqfy.chinacourt.gov.cn/article/index/id/M0guMjCwMDAwNCACAAA/page/1.shtml"

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
            urls = text.xpath('//div[@class="font14 dian_a"]//li//a/@href')
            names = text.xpath('//div[@class="font14 dian_a"]//li//a/text()')
            for x,y in zip(names,urls):
                for s in self.biaoshi:
                    if s in x:
                        link_list.append(y)
                        break
            if urls == []:
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
            d['court'] = '湖南省长沙市开福区人民法院'
            d['posttime'] = text.xpath('//div[@class="sth_a"]/span[1]/text()')[0].strip().split('：')[-1]
            d['province'] = '湖南省'
            self.parse(info,d)

    # 解析文本提取字段
    def parse(self,info,d):
        # 由于详情页的不同分为两种情况处理
        if '开庭公告' in d['title']:
            info_list = re.findall('(.*?)案。',info)
            for x in info_list:
                t = x.strip('一').strip()
                d['body'] = t

                # 获取案由
                l = []
                for anyou in self.anyou:
                    if anyou.decode('utf-8') in t:
                        l.append(anyou.decode('utf-8'))
                l.sort(reverse=True,key=len)
                try:
                    d['anyou'] = l[0]
                except IndexError:
                    continue

                # 提取原告，被告，法庭，开庭时间(分为有误原告)
                for i in self.re1:
                    try:
                        text = re.findall(i % d['anyou'] ,t)[0]
                        d['plaintiff'] = text[2]
                        d['pname'] = text[3]
                        break
                    except IndexError:
                        continue
                else:
                    for i in self.re2:
                        try:
                            text = re.findall(i % d['anyou'] ,t)[0]
                            d['plaintiff'] = ''
                            d['pname'] = text[2]
                            break
                        except IndexError:
                            continue
                    else:
                        with open('shibai.txt','a',encoding='utf-8') as f:
                            f.write('----------' + t)
                            f.write('\n')
                        continue
                d['sorttime'] = text[0].strip()
                d['courtNum'] = text[1].strip()

                # 对被告和原告的后面多余字进行丢弃
                d['pname'] = d['pname'].replace('在','')
                d['plaintiff'] = d['plaintiff'].replace('在','')

                md5 = hashlib.md5()
                md5.update((d['body'] + d['url']).encode())
                d['md5'] = md5.hexdigest()
                self.insert_mysql(d)
        else:
            if '第三人' in info:
                return
            d['body'] = info.strip()
            for x,y in self.re.items():
                try:
                    l = re.findall(y,info,re.S)[0]
                except IndexError:
                    continue
                if '被告' in l[1]:
                    return
                if x == 4:
                    d['anyou'] = l[2].replace(';',' ').replace(':',' ').replace('：',' ').strip()
                    d['sorttime'] = l[3].replace(';',' ').replace(':',' ').replace('：',' ').strip()
                    d['courtNum'] = l[4].replace(';',' ').replace(':',' ').replace('：',' ').strip()
                    d['judge'] = l[5].replace(';',' ').replace(':',' ').replace('：',' ').strip()
                elif x == 5:
                    d['anyou'] = ''
                    d['sorttime'] = l[2].replace(';',' ').replace(':',' ').replace('：',' ').strip()
                    d['courtNum'] = l[3].replace(';',' ').replace(':',' ').replace('：',' ').strip()
                    d['judge'] = l[4].replace(';',' ').replace(':',' ').replace('：',' ').strip()
                else:
                    d['anyou'] = l[2].replace(';',' ').replace(':',' ').replace('：',' ').strip()
                    d['judge'] = l[3].replace(';',' ').replace(':',' ').replace('：',' ').strip()
                    d['sorttime'] = l[4].replace(';',' ').replace(':',' ').replace('：',' ').strip()
                    d['courtNum'] = l[5].replace(';',' ').replace(':',' ').replace('：',' ').strip()
                d['plaintiff'] = l[0].replace(';',' ').replace(':',' ').replace('：',' ').strip()
                d['pname'] = l[1].replace(';',' ').replace(':',' ').replace('：',' ').strip()
                break
            else:
                with open('shibai.txt','a',encoding='utf-8') as f:
                    f.write('----------' + d['body'])
                    f.write('\n')
                return
            md5 = hashlib.md5()
            md5.update((d['body'] + d['url']).encode())
            d['md5'] = md5.hexdigest()
            self.insert_mysql(d)
            
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