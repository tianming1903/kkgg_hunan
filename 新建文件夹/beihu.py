'''
此代码爬取湖南的开庭公告，
'''
import ktgg
import re
from lxml import etree

class Ktgg_hunan():
    def __init__(self):
        # 起始url 
        self.url = "http://bhqfy.chinacourt.gov.cn/article/index/id/M0itMDAwMzAwMiACAAA.shtml"

        self.party = [
            '公开(.*?)[诉与](.*)',
            '公开(.*)',
            '(.*?)[诉与](.*)',
            '(.*)'
        ]

    # 获取每个详情页的链接
    def qingqiu(self):
        links_list = []
        i = 1
        x = '//div[@class="paginationControl"]/preceding-sibling::ul//a'
        print('开始请求一级页面.....')
        while True:
            html = ktgg.request(self.url,i)
            # 判断请求是超过了页面总数
            l = re.findall('上一页',html)
            if l == []:
                break
            # xpath匹配出链接和文本
            links = ktgg.parse(html,x)
            links_list.extend(links)
            i += 1     
        print('请求到详情页数量是: ' + str(len(links_list)))
        return links_list

    def parse_html(self,links):
        # 连接数据库
        db,cursor = ktgg.con_mysql()

        for i in links:
            d = {}
            url = 'http://bhqfy.chinacourt.gov.cn' + i
            text,html= ktgg.request_dis(url)
            if text == 0:
                continue
    
            # 提取一些信息
            d['posttime'] = re.findall('发布时间(.*?)<',html)[0].replace('：','').strip()
            d['court'] = '北湖人民法院'
            d['source'] = self.url
            d['url'] = url
            d['title'] = re.findall("'b_title'>(.*?)<",html)[0]
            d['province'] = '湖南省'
            if text == '':
                text = d['title']
            html = etree.HTML(html)
            self.parse_text(text,html,d,db,cursor)

        # 关闭数据库
        ktgg.clo_mysql(db,cursor)

    def parse_text(self,text,html,d,db,cursor):
        if '开庭公告' in d['title']:
            infos = html.xpath('//tbody/tr')[1:]
            for info in infos:
                d_info = d.copy()
                d_info['body'] = info.xpath('string(.)').replace('\r','').replace('\n','')
                if len(info.xpath('./td')) == 4:
                    # 提取时间
                    d_info['sorttime'] = info.xpath('./td[4]')[0].xpath('string(.)').split(' ')[0]
                    # 提取地点
                    d_info['courtNum'] = info.xpath('./td[3]')[0].xpath('string(.)')
                    party = info.xpath('./td[2]')[0].xpath('string(.)')
                else:
                    # 提取时间
                    d_info['sorttime'] = info.xpath('./td[3]')[0].xpath('string(.)').split(' ')[0]
                    # 提取地点
                    d_info['courtNum'] = info.xpath('./td[2]')[0].xpath('string(.)')
                    party = info.xpath('./td[1]')[0].xpath('string(.)')
                # 提取被告和原告和案由
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
                else:
                    return
                d_info['md5'] = ktgg.get_md5(d_info['body'],d_info['url'])
                ktgg.ins_mysql(d_info,'ktgg_kt_wuhan',db,cursor)

        else:
            d['body'] = text
            # 提取日期
            sorttime = re.findall('\d{1,2}月.*?日',d['title'])
            if sorttime:
                d['sorttime'] = d['posttime'].split('-')[0] + '年' + sorttime[0]
            #提取审判庭    
            courtNum = re.findall('在(.{2,5}庭)',d['body'])
            if courtNum:
                d['courtNum'] = courtNum[0]
            for i in self.party:
                try:
                    party = re.findall(i,d['body'])[0]
                except IndexError:
                    continue
                else:
                    anyou = ktgg.set_anyou()
                    if type(party) is str:
                        start,end = ktgg.search_anyou(anyou,party)
                        if start == 0:
                            return
                        d['anyou'] = party[start:end]
                        d['pname'] = re.findall('(.*?)%s' % d['anyou'],party)[0].replace('被告人','').replace('被告','').replace('审','').replace('理','')
                    elif type(party) is tuple:
                        start,end = ktgg.search_anyou(anyou,party[1])
                        if start == 0:
                            return
                        d['anyou'] = party[1][start:end]
                        d['plaintiff'] = party[0].replace('原告人','').replace('原告','').replace('审','').replace('理','')
                        d['pname'] = re.findall('(.*?)%s' % d['anyou'],party[1])[0].replace('被告人','').replace('被告','')
                break
            else:
                return
            d['md5'] = ktgg.get_md5(d['body'],d['url'])
            ktgg.ins_mysql(d,'ktgg_kt_wuhan',db,cursor)
            # 提取案由和原告和被告

    def main(self):
        links = self.qingqiu()
        self.parse_html(links)

if __name__ == "__main__":
    kh = Ktgg_hunan()
    kh.main()

