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
        # 定义案由
        self.anyou = ''
        # 定义标识词
        self.biaoshi = ['纠纷','争议','诉']
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
            link_list.extend(urls) 
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
            text = etree.HTML(html)
            content = text.xpath('//div[@class="text"]')
            if content == []:
                continue
            info = content[0].xpath('string(.)')

            # 先获取一些字段
            d['source'] = self.url
            d['url'] = url
            d['title'] = text.xpath('//div[@class="b_title"]/text()')[0]
            court =  text.xpath('//div[@class="from"]/text()')
            # 没有则默认法院
            if court == []:
                d['court'] = '湖南省长沙市开福区人民法院'
            else:
                d['court'] = court[0].split('：')[1]
            d['posttime'] = text.xpath('//div[@class="sth_a"]/span[1]/text()')[0].strip().split('：')[-1]
            d['province'] = '湖南省'
            self.parse(info,d)

    # 解析文本提取字段
    def parse(self,info,d):
        if '开庭公告' in d['title']:
            info_list = re.findall('(.*?)案。',info)
            for x in info_list:
                md5 = hashlib.md5()
                l = []
                t = x.strip('一').strip()
                d['body'] = t
                for anyou in self.anyou:
                    if anyou.decode('utf-8') in t:
                        l.append(anyou.decode('utf-8'))
                l.sort(reverse=True,key=len)
                try:
                    d['anyou'] = l[0]
                except IndexError:
                    with open('shibai.txt','a',encoding='utf-8') as f:
                        f.write(t)
                        f.write('\n')
                    continue
                try:
                    if '诉' in t:
                        text = re.findall('于(.*?)在(.*?)开庭审理(.*?)诉(.*?)%s' % d['anyou'] ,t)[0]
                        d['plaintiff'] = text[2]
                        d['pname'] = text[3]
                    else:
                        text = re.findall('于(.*?)在(.*?)开庭审理(.*?)%s'% d['anyou'] ,t)[0]
                        d['plaintiff'] = ''
                        d['pname'] = text[2]
                    d['sorttime'] = text[0]
                    d['courtNum'] = text[1]
                except IndexError:
                    with open('shibai.txt','a',encoding='utf-8') as f:
                        f.write(t)
                        f.write('\n')
                    continue
                md5.update((t + d['url']).encode())
                d['md5'] = md5.hexdigest()
                print(d)
                self.insert_mysql(d)

        else:
            for y in self.biaoshi:
                if y in d['title']:
                    break

    def insert_mysql(self,d):

        # 删除没有值的字段
        l = []
        for i in d.keys():
            if d[i] == '':
                l.append(i)
        for i in l:
            del d[i]

        # 准备入库
        db = pymysql.connect(host="localhost",user="root",password="123456",db='litianming')
        cursor = db.cursor()
        table = 'ktgg_hunan1'
        keys = ','.join(d.keys())
        values = ','.join(['%s'] * len(d))
        sql = "INSERT INTO {table}({keys}) VALUES({values})".format(table = table,keys = keys,values = values)
        try:
            cursor.execute(sql,tuple(d.values()))
            db.commit()
        except:
            db.rollback()
        cursor.close()
        db.close()

    def main(self):
        self.set_anyou()
        links = self.set_request()
        self.request_info(links)

# if __name__ == "__main__":
#     kh = Ktgg_hunan()
#     kh.main()

body = '开福区人民法院将于2018年10月30日14:00在B216民事审判庭开庭审理湖南爱屋装饰有限责任公司诉曹宇夫装饰装修合同纠纷'
url = 'http://kfqfy.chinacourt.gov.cn/article/detail/2018/10/id/3543002.shtml'
md5 = hashlib.md5()
md5.update((body+url).encode())
print(md5.hexdigest())