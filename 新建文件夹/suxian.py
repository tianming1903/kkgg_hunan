'''
此代码爬取湖南的开庭公告，
'''
import ktgg
import re

class Ktgg_hunan():
    def __init__(self):
        # 定义正则表达式
        # 提取法庭的
        self.courtNum = [
            '在(.*?)[依共]',
            '在(.*?)审理',
            '本院(.*?)依法'
        ]
        # 提取被告和原告
        self.pname_p = [
            '审理(.*?)诉(.*?)%s',
            '审理(.*?)与(.*?)%s',
            '审理(.*?)指控的(.*?)%s',
            '审理(.*?)%s'
        ]

        # body替换无效字符
        self.tihuan = ['\xa0','\r\n','\n',' ','\u3000']

        # 起始url 
        self.url = "http://sxqfy.chinacourt.gov.cn/article/index/id/M0itMjBINCAOAAA.shtml"

          
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
            url = 'http://' + re.findall('//(.*?)/',self.url)[0] + i
            text,html= ktgg.request_dis(url)
            if text == '':
                continue
    
            # 提取一些信息
            d['posttime'] = re.findall('发布时间(.*?)<',html)[0].replace('：','').strip()
            d['court'] = '郴州市苏仙区人民法院'
            d['source'] = self.url
            d['url'] = url
            d['title'] = re.findall("'b_title'>(.*?)<",html)[0]
            d['province'] = '湖南省'
            for i in self.tihuan:
                text = text.replace(i,'')
            d['body'] = text
            if text == '':
                d['body'] = d['title']
            d['md5'] = ktgg.get_md5(d['body'],d['url'])
            self.parse_text(d,db,cursor)

        # 关闭数据库
        ktgg.clo_mysql(db,cursor)

    def parse_text(self,d,db,cursor):
        # 获取案由
        d['anyou'] = ktgg.set_anyou(d['body'])
        # 获取开庭时间
        try:
            d['sorttime'] = re.findall(r'(\d{4}年\d{1,2}月\d{1,2})日',d['body'])[0] + '日'
        except IndexError:
            d['sorttime'] = ''
        # 获取开庭地点
        for i in self.courtNum:
            l = re.findall(i,d['body'])
            if l:
                d['courtNum'] = l[0].split('庭')[0] + '庭'
                break
        # 获取原告和被告
        for i in self.pname_p:
            l = re.findall(i % d['anyou'],d['body'])
            if l:
                if len(l[0]) == 2:
                    d['plaintiff'] = l[0][0].replace('原告人','').replace('原告','').replace(' ','')
                    d['pname'] = l[0][1].replace('被告人','').replace('被告','').replace(' ','')
                else:
                    d['plaintiff'] = ''
                    d['pname'] = l[0].replace('被告人','').replace('被告','').replace(' ','')
                break
        # print(d)
        ktgg.ins_mysql(d,'ktgg_ceshi',db,cursor)

    def main(self):
        links = self.qingqiu()
        self.parse_html(links)

if __name__ == "__main__":
    kh = Ktgg_hunan()
    kh.main()

