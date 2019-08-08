'''
此代码爬取湖南的开庭公告，
'''
import ktgg
import re
from lxml import etree

class Ktgg_hunan():
    def __init__(self):
        # 提取被告和原告
        self.party = [
            '原告(.*?)[诉与]被告(.*)',
            '被告(.*)'
        ]

        # body替换无效字符
        self.tihuan = ['\xa0','\r\n','\n',' ','\u3000']

        # 起始url 
        self.url = "http://hnyzfy.chinacourt.gov.cn/article/index/id/M0gzMjCwNCAOAAA.shtml"

          
    # 获取每个详情页的链接
    def qingqiu(self):
        links_list = []
        i = 1
        x = '//div[@class="content"]//ul/li//a'
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
            url = 'http://hnyzfy.chinacourt.gov.cn' + i
            text,html= ktgg.request_dis(url)
            if text == 0:
                continue
    
            # 提取一些信息
            d['posttime'] = re.findall('发布时间(.*?)<',html)[0].replace('：','').strip()
            d['court'] = '宜章人民法院'
            d['source'] = self.url
            d['url'] = url
            d['title'] = re.findall("'b_title'>(.*?)<",html)[0]
            if d['title'] == '':
                t = etree.HTML(html)
                d['title'] = t.xpath('//div[@class="b_title"]/span/text()')[0]
            d['province'] = '湖南省'
            self.parse_text(text,d,db,cursor)

        # 关闭数据库
        ktgg.clo_mysql(db,cursor)

    def parse_text(self,text,d,db,cursor):
        for i in self.tihuan:
            text = text.replace(i,'')
        d['body'] = text

        # 提取开庭时间
        sorttime = re.findall('\d{1,4}[年月].*?[日号]',text)
        if sorttime:
            d['sorttime'] = sorttime[0]
        # 提取开庭地点
        courtNum = re.findall('在(.{2,7}庭)',text)
        if courtNum:
            d['courtNum'] = courtNum[0]
        else:
            courtNum= re.findall('第.{1,4}庭',text)
            if courtNum:
                d['courtNum'] = courtNum[0]

        # 提取原告，被告和案由
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
                        ktgg.write_txt('anyou',text)
                    d['anyou'] = party[start:end]
                    d['pname'] = re.findall('(.*?)%s' % d['anyou'],party)[0].replace('人','')
                elif type(party) is tuple:
                    start,end = ktgg.search_anyou(anyou,party[1])
                    if start == 0:
                        return
                    d['anyou'] = party[1][start:end]
                    d['plaintiff'] = party[0].replace('人','')
                    d['pname'] = re.findall('(.*?)%s' % d['anyou'],party[1])[0].replace('人','')
            break
        d['md5'] = ktgg.get_md5(d['body'],d['url'])
        ktgg.ins_mysql(d,'ktgg_kt_wuhan',db,cursor)

    def main(self):
        links = self.qingqiu()
        self.parse_html(links)

if __name__ == "__main__":
    kh = Ktgg_hunan()
    kh.main()

