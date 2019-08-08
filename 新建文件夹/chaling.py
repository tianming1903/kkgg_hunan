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
            '.','/','年','月','日'
        ]
        # 时间切割
        self.re = [
            '\d{4}年.*?日',
            '\d{1,2}月.*?日',
            '\d{4}\.\d{1,2}\.\d{1,2}',
            '\d{1,2}\.\d{1,2}',
            '\d{4}/\d{1,2}/\d{1,2}'
        ]

        # 定义过滤字符
        self.tihuan = ['\xa0','\r\n','\n',' ','\u3000','\t']

        # 起始url 
        self.url = "http://clxfy.chinacourt.gov.cn/article/index/id/M0gxNTAwMTAwMiACAAA.shtml"
 
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
            d['court'] = '茶陵县人民法院'
            d['source'] = self.url
            d['url'] = url
            d['title'] = re.findall("'b_title'>(.*?)<",html)[0]
            d['province'] = '湖南省'
            self.parse_text(text,d,db,cursor)

        # 关闭数据库
        ktgg.clo_mysql(db,cursor)

    def parse_text(self,text,d,db,cursor):
        # 对文本切片获取每个案列
        infos = re.split('\n',text)

        for info in infos:
            if '案由' in info or not info:
                continue

            # 获取案例的列表
            l = re.split('\s',info)

            # 获取body
            for i in self.tihuan:
                info = info.replace(i,'')
            d['body'] = info

            # 案号
            caseNo = re.findall('[民（].*?号',info)
            d['caseNo'] = ''
            if caseNo:
                d['caseNo'] = caseNo[0]

            # 案由
            b = 0
            anyou = ktgg.set_anyou()
            for i in l:
                for a in anyou:
                    if a in i:
                        d['anyou'] = i
                        b = 1
                        break
                if b == 1:
                    break
            else:
                continue

            # 开庭地点
            for i in l:
                courtNum = re.findall('第.*?庭',i)
                d['courtNum'] = ''
                if courtNum:
                    d['courtNum'] = courtNum[0] 
                    break

            # 开庭时间
            sorttime = ''
            for i in l[-1::-1]:
                for x in self.t:
                    if x in i:
                        sorttime = i
                        break
                if sorttime:
                    break
            # 格式化时间
            for i in self.re:
                s = re.findall(i,sorttime)
                if s:
                    d['sorttime'] = s[0]
                    break
            else:
                d['sorttime'] = ''

            if '.' in d['sorttime']:
                times = d['sorttime'].split('.')
                if len(times) == 2:
                    d['sorttime'] = times[0] + '月' + times[1] + '日'
                else:
                    d['sorttime'] = times[0] + '年' + times[1] + '月' + times[2] + '日'
            elif '/' in d['sorttime']:
                times = sorttime.split('/')
                d['sorttime'] = times[0] + '年' + times[1] + '月' + times[2] + '日'

            # 原告和被告
            for i in l:
                if i == d['anyou']:
                    s = l.index(i) + 1
                    while True:
                        if l[s] == '':
                            s += 1
                            continue
                        yuan_bei = l[s]
                        break
                    break

            # 获取原告
            d['party'] = ''
            d['plaintiff'] = ''
            d['pname'] = ''
            if ';' in yuan_bei:
                d['plaintiff'] = yuan_bei.split(';')[0].replace('原告','').replace(' ','').replace(':','')
                d['pname'] = yuan_bei.split(';')[1].replace('被告','').replace(' ','').replace(':','')
            elif '；' in yuan_bei:
                d['plaintiff'] = yuan_bei.split('；')[0].replace('原告','').replace(' ','').replace(':','')
                d['pname'] = yuan_bei.split('；')[1].replace('被告','').replace(' ','').replace(':','')
            elif '诉' in yuan_bei:
                d['plaintiff'] = yuan_bei.split('诉')[0].replace('原告','').replace(' ','').replace(':','')
                d['pname'] = yuan_bei.split('诉')[1].replace('被告','').replace(' ','').replace(':','')
            else:
                d['party'] = yuan_bei
            d['md5'] = ktgg.get_md5(info,d['url'])
            ktgg.ins_mysql(d,'ktgg_kt_wuhan',db,cursor)

    def main(self):
        links = self.qingqiu()
        self.parse_html(links)

if __name__ == "__main__":
    kh = Ktgg_hunan()
    kh.main()


