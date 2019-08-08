'''
此代码爬取湖南的开庭公告，
'''
import ktgg
import re
import time


class Ktgg_hunan():
    def __init__(self):
        # 定义正则表达式
        # 提取法庭的
        self.courtNum = [

        ]
        # 提取被告和原告
        self.pname_p = [
            '号(.*?)诉(.*?)%s',
        ]

        # body替换无效字符
        self.tihuan = ['\xa0','\r\n','\n',' ','\u3000']

        # 起始url 
        self.url = "http://wcxfy.chinacourt.gov.cn/article/index/id/M0guNTBINTAwNCACAAA.shtml"


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
            url = 'http://' + re.findall('//(.*?)/',self.url)[0] + i
            text,html= ktgg.request_dis(url)
            if text == '':
                continue
            # 提取一些信息
            d['posttime'] = re.findall('发布时间(.*?)<',html)[0].replace('：','').strip()
            d['court'] = '长沙市望城区人民法院'
            d['source'] = self.url
            d['url'] = url
            d['title'] = re.findall("'b_title'>(.*?)<",html)[0]
            d['province'] = '湖南省'
            # 防止body为空,如果为空则为标题
            for i in self.tihuan:
                text = text.replace(i,'')
            d['body'] = text
            if text == '':
                d['body'] = d['title']
            self.parse_text(d,db,cursor)

        # 关闭数据库
        ktgg.clo_mysql(db,cursor)
    
    def parse_text(self,d,db,cursor):
        # 由于格式原因分为两种情况
        if '排期开庭' in d['title']:
            l = re.findall('(\d{1,4}[年].*?[日上下号])(.*?)\d{1,2}、{1,2}',d['body'])
            for info in l:
                d['body'] = info[0] + info[1]
                d['sorttime'] = info[0]
                d['anyou'] = ktgg.set_anyou(info[1])

                caseNo = re.findall('[\[【（(].*?号',info[1])
                d['caseNo'] = ''
                if caseNo:
                    d['caseNo'] = caseNo[0]

                courtNum = re.findall('我院(.*?)开庭审理',info[1])
                d['courtNum'] = ''
                if courtNum:
                    d['courtNum'] = courtNum[0].replace('公开','')

                for i in self.pname_p:
                    s = re.findall(i % d['anyou'],info[1])
                    if s :
                        d['plaintiff'] = s[0][0].replace('原告人','').replace('原告','').replace('，','').replace(',','')
                        d['pname'] = s[0][1].replace('被告人','').replace('被告','')
                        break
                
                d['md5'] = ktgg.get_md5(d['body'],d['url'])
                ktgg.ins_mysql(d,'ktgg_kt_wuhan',db,cursor)

        else:
            anyou = ktgg.set_anyou()
            d['anyou'] = ktgg.search_anyou(anyou,d['body'])
            d['sorttime'] = re.findall('\d{1,4}[年月].*?[日上下号]',d['body'])[0]
            # 案号
            caseNo = re.findall('[\[【（(].*?号',d['body'])
            d['caseNo'] = ''
            if caseNo:
                d['caseNo'] = caseNo[0]
            # 开庭地点
            courtNum = re.findall('我院(.*?)开庭审理',d['body'])
            d['courtNum'] = ''
            if courtNum:
                d['courtNum'] = courtNum[0].replace('公开','')
            # 获取原告和被告
            for i in self.pname_p:
                l = re.findall(i % d['anyou'],d['body'])
                if l :
                    d['plaintiff'] = l[0][0].replace('原告人','').replace('原告','').replace('，','').replace(',','')
                    d['pname'] = l[0][1].replace('被告人','').replace('被告','')
                    break
            d['md5'] = ktgg.get_md5(d['body'],d['url'])
            ktgg.ins_mysql(d,'ktgg_kt_wuhan',db,cursor)

    def main(self):
        links = self.qingqiu()
        self.parse_html(links)

if __name__ == "__main__":
    kh = Ktgg_hunan()
    kh.main()
