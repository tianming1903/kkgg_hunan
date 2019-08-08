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
        self.url = "http://zxsfy.chinacourt.gov.cn/"

        # 定义请求头
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Host": "zxsfy.chinacourt.gov.cn",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36",
        }
    
        # 定义party
        self.party = [
            '(.*?)[诉与](.*)',
            '(.*)'
        ]
    # 获取每个详情页的链接
    def qingqiu(self):
        print('获取详情页链接.....')
        try:
            r = requests.get(self.url,headers=self.headers,timeout=3.05)
        except (Timeout,ConnectionError):
            sys.exit('请求主页面出错')
        r.encoding = 'gb18030'
        html = r.text
        # xpath匹配出链接
        text = etree.HTML(html)
        links = text.xpath('//td[@class="margin_2"]/table[3]//td[@class="td_line"]/a/@href')
        print('请求到详情页数量是: ' + str(len(links)))
        return links

    def parse_html(self,links):
        # 连接数据库
        db,cursor = ktgg.con_mysql()
        for i in links:
            d = {}
            url = self.url + i
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
            d['court'] = '资兴区人名法院'
            d['source'] = self.url
            d['url'] = url
            d['title'] = text.xpath('//font/b/text()')[0]
            d['posttime'] = text.xpath('//p[@align="center"][3]/text()')[0].split('：')[-1]
            d['province'] = '湖南省'
            self.parse_text(text,d,db,cursor)
            time.sleep(1)

        # 关闭数据库
        ktgg.clo_mysql(db,cursor)

    def parse_text(self,text,d,db,cursor):
            infos = text.xpath('//span[@class="detail_content"]//tr')[1:]
            for info in infos:
                d_info = d.copy()
                # 提取body
                d_info['body'] = info.xpath('string(.)').replace('\r','').replace('\n','')
                # 提取案号
                d_info['caseNo'] = info.xpath('./td[2]/span/text()')[0]
                # 提取审判员
                d_info['judge'] = info.xpath('./td[5]/span/text()')[0]
                # 提取开庭地点
                d_info['courtNum'] = info.xpath('./td[6]/span/text()')[0]
                # 提取时间
                d_info['sorttime'] = info.xpath('./td[7]/span/text()')[0].split(' ')[0]
                # 提取原告和被告和案由
                party = info.xpath('./td[3]/span/text()')[0]
                for i in self.party:
                    try:
                        party = re.findall(i,party)[0]
                    except IndexError:
                        continue
                    else:
                        anyou = ktgg.set_anyou()
                        if type(party) is str:
                            start,end = ktgg.search_anyou(anyou,party)
                            if start == 0:
                                return
                            d_info['anyou'] = party[start:end]
                            d_info['pname'] = re.findall('(.*?)%s' % d_info['anyou'],party)[0].replace('被告人','').replace('被告','')
                        elif type(party) is tuple:
                            start,end = ktgg.search_anyou(anyou,party[1])
                            if start == 0:
                                return
                            d_info['anyou'] = party[1][start:end]
                            d_info['plaintiff'] = party[0].replace('原告人','').replace('原告','')
                            d_info['pname'] = re.findall('(.*?)%s' % d_info['anyou'],party[1])[0].replace('被告人','').replace('被告','')
                    break
                d_info['md5'] = ktgg.get_md5(d_info['body'],d_info['url'])
                ktgg.ins_mysql(d_info,'ktgg_kt_wuhan',db,cursor)

    def main(self):
        links = self.qingqiu()
        self.parse_html(links)

if __name__ == "__main__":
    kh = Ktgg_hunan()
    kh.main()

