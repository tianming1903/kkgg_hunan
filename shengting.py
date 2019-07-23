import requests
from lxml import etree
import json
import pymysql
from queue import Queue
from threading import Thread
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import re
import hashlib
from requests.exceptions import Timeout,ConnectionError


class Tingsheng():
    def __init__(self):
        self.queue = Queue()
        # 设置无头浏览器
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        self.driver = webdriver.Chrome(chrome_options=chrome_options)

        # 详情页链接
        self.url = 'http://tingshen.court.gov.cn/live/'
        # ajax链接
        self.link = 'http://tingshen.court.gov.cn/search/a/revmor/full?'
        # 起始链接
        self.start_url = 'http://tingshen.court.gov.cn/court/review/3050?courtLevel=2'

        self.headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Host": "tingshen.court.gov.cn",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36",
        }

        self.params = {
            "unUnionIds": "",
            "label": "",
            "courtCode": "3050",
            "catalogId": "",
            "pageNumber": "",
            "courtLevel": "2",
            "dataType": "2",
            "pageSize": "6",
            "level": "0",
            "extType": "",
            "isOts": "",
            "keywords": "",
        }

        self.cookies = {}

    # 获取cookies
    def set_cookies(self):
        self.driver.get(self.start_url)
        time.sleep(2)
        self.driver.refresh()
        cookies = self.driver.get_cookies()
        for i in cookies:
            self.cookies[i['name']] = i['value']
        self.driver.quit()

    # 构建一个线程去请求详情页的信息
    def create_thread(self):
        t = Thread(target=self.request_tetails)
        t.start()
        print('正在抓取详情页信息，请稍等...')
        return t

    # 构建请求链接进行ajax异步请求
    def request(self,t):
        i = 1
        while True:
            self.params['pageNumber'] = str(i)
            try:
                re = requests.get(self.link,params=self.params,headers=self.headers,cookies=self.cookies,timeout=3.1)
            except Timeout:
                print('json数据请求超时')
                continue
            try:
                text = re.json()['resultList']
            except json.decoder.JSONDecodeError as e:
                print('错误是：' + str(e))
                return
            if text == []:
                break
            for x in text:
                l = []
                # 获取详情页的链接参数
                l.append(x['caseId'])
                l.append(x['title'])
                l.append(x['courtName'])
                l.append(x['caseNo'])
                l.append(x['caseCause'])
                l.append(x['judge'])
                l.append(x['description'])
                l.append(int(x['beginTime'])/1000)
                self.queue.put(l)
            time.sleep(1)
            i += 1
        print('json数据请求完成')

        # 等待所有的详情页请求完结束代码
        if self.queue.join():
            t.join()
            return

    def request_tetails(self):
        time.sleep(5)
        while True:
            if self.queue.empty():
                return
            info = self.queue.get()
            url = self.url + str(info[0])
            try:
                re = requests.get(url,headers=self.headers,cookies=self.cookies,timeout=3.1)
            except (Timeout,ConnectionError):
                print('....不好意思，一条数据被丢')
                self.queue.task_done()
                continue
            else:
                re.encoding = 'utf8'
                html = re.text
                self.parse(html,info)

    def parse(self,html,info):
        d = {}
        body = {}
        md5 = hashlib.md5()
        et = etree.HTML(html)
        try:
            # 网站来源
            d['source'] = self.start_url
            # 详情链接
            d['url'] = self.url + str(info[0])
            # 标题
            d['title'] = info[1]
            # 法院
            d['court'] = info[2]
            # 发布时间
            d['posttime'] = time.strftime("%Y-%m-%d-%H:%M:%S", time.localtime(info[7]))
            # 开庭时间
            d['sorttime'] = et.xpath('//li[@id="_beginTime"]/text()')[1].strip()
            # 描述
            d['description'] = info[6]
            # 案号
            d['caseNo'] = info[3]
            # 案由
            d['anyou'] = info[4]
            # 法庭
            d['courtNum'] = et.xpath('//i[@id="_locate"]/text()')[0]
            # 省份
            d['province'] = '四川省'
            # 审判员
            d['judge'] = (info[5].split(';')[0]).split(':')[1]
            # 构建正文
            body['基本信息'] = {'案号':info[3],'开庭时间':d['sorttime'],'案由':info[4],'庭审地点':d['courtNum']}
            body['审判组成员'] = et.xpath('//ul[@id="judgeul"]//i/text()')[0]
            body['当事人'] = re.findall('party = "(.*?);"',html)[0]
            d['body'] = json.dumps(body,ensure_ascii=False)
            # body唯一性
            md5.update((d['url'] + d['body']).encode())
            d['md5'] = md5.hexdigest()
        except (IndexError,AttributeError):
            print('....不好意思，一条数据被丢')
            self.queue.task_done()
            return 
    
        # 获取被告和原告
        string = re.findall('party =(.*?)\n',html)[0].split(';')
        if len(string) > 3:
            plaintiff = string[0].split(':')[1]
            pname = string[1].split(':')[1]
        else:
            pname = string[0].split(':')[1]
            plaintiff = ''
        d['pname'] = pname
        d['plaintiff'] = plaintiff
        
        # # 写入到文本中
        # with open('info.text','a',encoding='utf-8') as f:
        #     f.write(str(d))
        #     f.write('\n')
    
        # 存入到数据库
        self.write_mysql(d)
        self.queue.task_done()

    # 插入数据库
    def write_mysql(self,d):
        # 删除空字符串
        l = []
        for i in d.keys():
            if d[i] == '':
                l.append(i)
        for i in l:
            del d[i]

        db = pymysql.connect(host="localhost",user="root",password="123456",db='litianming')
        cursor = db.cursor()
        table = 'ktgg_kt'
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
        self.set_cookies()
        print('成功获取cookies')
        t = self.create_thread()
        print('成功开启线程')
        print('开始请求json数据')
        self.request(t)
        print('数据已经全部插入数据库')

if __name__ == '__main__':
    ts = Tingsheng()
    ts.main()
