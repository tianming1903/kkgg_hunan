
'''
此代码爬取湖南的开庭公告，
'''
import ktgg
import re
import time


class Ktgg_hunan():
    def __init__(self):
        # 起始url 
        self.url = "http://hylyfy.chinacourt.gov.cn/article/index/id/M0jJNjBIMSAOAAA.shtml"

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
            url = 'http://hylyfy.chinacourt.gov.cn' + i
            text,html= ktgg.request_dis(url)
            if text == 0:
                continue
            # 提取一些信息
            d['posttime'] = re.findall('发布时间(.*?)<',html)[0].replace('：','').strip()
            d['court'] = '耒阳市人民法院'
            d['source'] = self.url
            d['url'] = url
            d['title'] = re.findall("'b_title'>(.*?)<",html)[0]
            d['province'] = '湖南省'
            self.parse_text(text,d,db,cursor)

        # 关闭数据库
        ktgg.clo_mysql(db,cursor)

    def parse_text(self,text,d,db,cursor):
        d['body'] = re.sub('\s','',text)
        # 提取开庭地点
        courtNum = re.findall('法院(.*?庭)',d['body'])
        if courtNum:
            d['courtNum'] = courtNum[0]
        # 提取时间
        sorttime = re.findall('\d{1,4}[年月].*?[日号]',d['body'])
        if sorttime:
            d['sorttime'] = sorttime[0]
        # 提取审判员
        judge = re.findall('审判员(.*?)[书代]',d['body'])
        if judge:
            d['judge'] = judge[0].replace('：','')
        
        # 提取被告，案由，原告(从标题上面提取)
        party = re.findall('被告(.*)',d['title'])
        if party:
            party = party[0]
            anyou = ktgg.set_anyou()
            start,end = ktgg.search_anyou(anyou,party)
            if start == 0:
                return
            d['anyou'] = party[start:end]
            d['pname'] = re.findall('(.*?)%s' % d['anyou'],party)[0].replace('人','')
        d['md5'] = ktgg.get_md5(d['body'],d['url'])
        ktgg.ins_mysql(d,'ktgg_kt_wuhan',db,cursor)

    def main(self):
        links = self.qingqiu()
        self.parse_html(links)

if __name__ == "__main__":
    kh = Ktgg_hunan()
    kh.main()

二〇一八年七月二十七