'''
此代码爬取湖南的开庭公告，
'''
import ktgg
import re
import time


class Ktgg_hunan():
    def __init__(self):
        # 时间标识
        self.t = [
        ]
        # 时间切割
        self.re = [
        ]

        # 定义过滤字符
        self.tihuan = ['\xa0',' ','\u3000']

        # 起始url 
        self.url = "http://sfqfy.chinacourt.gov.cn/article/index/id/M0iuMjAwNTAwNCACAAA.shtml"
 
    # 获取每个详情页的链接
    def qingqiu(self):
        links_list = []
        i = 1
        x = '//div[@id="list"]//li/span/a'
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
            url = 'http://sfqfy.chinacourt.gov.cn' + i
            text,html= ktgg.request_dis(url)
            if text == '':
                continue
            # 提取一些信息
            d['posttime'] = re.findall('发布时间：(.*?)<',html)[0].strip()
            d['court'] = '石峰区人民法院'
            d['source'] = self.url
            d['url'] = url
            d['title'] = re.findall("'b_title'>(.*?)<",html)[0]
            d['province'] = '湖南省'
            self.parse_text(text,d,db,cursor)

        # 关闭数据库
        ktgg.clo_mysql(db,cursor)

    def parse_text(self,text,d,db,cursor):
            # 删除不必要的字符和格式化数据
            for i in self.tihuan:
                text = text.replace(i,'')
            info = re.split('\s',text)
            
            # 提取信息
            if len(info) >= 3 and '--' not in d['title']:
                d['body'] = text.replace('\n','')
                d['md5'] = ktgg.get_md5(d['body'],d['url'])
                d['sorttime'] = re.findall('\d{1,4}[年月].*?[日号]',d['title'])[0]
                for i in info:
                    if '原告' in i:
                        d['plaintiff'] = re.findall('原告(.*)',i)[0].replace('人','').replace(':','').replace('：','')
                    elif '被告' in i:
                        d['pname'] = re.findall('被告(.*)',i)[0].replace('人','').replace(':','').replace('：','')
                    elif '案由' in i:
                        d['anyou'] = re.findall('案由(.*)',i)[0].replace(':','').replace('：','')
                    elif '主审法官' in i:
                        d['judge'] = re.findall('主审法官(.*)',i)[0].replace(':','').replace('：','')
                    elif '审判员' in i:
                        d['judge'] = re.findall('审判员(.*)',i)[0].replace(':','').replace('：','')
                    elif '主审人' in i:
                        d['judge'] = re.findall('主审人(.*)',i)[0].replace(':','').replace('：','')
                    elif '案号' in i:
                        d['caseNo'] = re.findall('案号(.*)',i)[0].replace(':','').replace('：','')
                ktgg.ins_mysql(d,'ktgg_kt_wuhan',db,cursor)

    def main(self):
        links = self.qingqiu()
        self.parse_html(links)

if __name__ == "__main__":
    kh = Ktgg_hunan()
    kh.main()

