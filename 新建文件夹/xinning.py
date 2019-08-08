
'''
此代码爬取湖南的开庭公告，
'''
import ktgg
import re
import time


class Ktgg_hunan():
    def __init__(self):
        # 起始url 
        self.url = "http://xnxfy.chinacourt.gov.cn/article/index/id/M0g1NDCwMDAAkoQBAA.shtml"

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
            url = 'http://xnxfy.chinacourt.gov.cn' + i
            text,html= ktgg.request_dis(url)
            if text == 0:
                continue
            # 提取一些信息
            d['posttime'] = re.findall('发布时间(.*?)<',html)[0].replace('：','').strip()
            d['court'] = '新宁县人民法院'
            d['source'] = self.url
            d['url'] = url
            d['title'] = re.findall("'b_title'>(.*?)<",html)[0]
            d['province'] = '湖南省'
            self.parse_text(text,d,db,cursor)

        # 关闭数据库
        ktgg.clo_mysql(db,cursor)

    def parse_text(self,text,d,db,cursor):
        # 切割文本
        infos = re.split('\n',text)
        f = []
        for info in infos:
            d_info = d.copy()
            info = re.split('\s',info)
            info = list(filter(None,info))
            # 第一种情况
            start = 0
            if len(info) >= 6:
                d_info['sorttime'] = ''
                d_info['caseNo'] = ''
                d_info['body'] = ''.join(info)
                for i in info:
                    # 提取案号,案由，被告和原告
                    if ('号' in i) and  (d_info['caseNo'] == ''):
                        d_info['caseNo'] = i
                        # 获取party
                        index = info.index(i)
                        party = info[index + 1]
                        # 获取案由
                        anyou = ktgg.set_anyou()
                        start,end = ktgg.search_anyou(anyou,party)
                        if start == 0:
                            break
                        d_info['anyou'] = party[start:end]
                        # 获取原告和被告
                        if '诉' in party:
                            p = re.split('诉',party)
                            d_info['plaintiff'] = p[0]
                            d_info['pname'] = re.findall('(.*?)%s' % d_info['anyou'],p[1])
                        else:
                            d_info['pname'] = re.findall('(.*?)%s' % d_info['anyou'],party)[0]
                    # 提取开庭时间和开庭地点
                    if d_info['sorttime'] == '':
                        sorttime = re.findall('\d{4}-\d{2}-\d{2}',i)
                        if sorttime:
                            d_info['sorttime'] = sorttime[0]
                            index = info.index(i)
                            d_info['courtNum'] = info[index - 1]
                if start == 0:
                    continue
                d_info['md5'] = ktgg.get_md5(d_info['body'],d_info['url'])
                ktgg.ins_mysql(d_info,'ktgg_kt_wuhan',db,cursor)

            # 第二种情况
            elif 0 < len(info):
                f.append(info)
                if len(f) == 2:
                    info = f[0] + f[1]
                    d_info['body'] = ''.join(info)
                    # 提取时间
                    sorttime = re.findall('\d{4}年.*?日',d_info['body'])
                    if sorttime:
                        d_info['sorttime'] = sorttime[0]
                    # 提取法庭
                    courtNum = re.findall('第.{2,6}庭|回龙法庭',d_info['body'])
                    if courtNum:
                        d_info['courtNum'] = courtNum[0]
                    # 获取案号
                    caseNo = re.findall('[(（民].*?号',d_info['body'])
                    if caseNo:
                        d_info['caseNo'] = caseNo[0]

                    for i in info:
                        if '诉' in i:
                            # 获取案由
                            anyou = ktgg.set_anyou()
                            start,end = ktgg.search_anyou(anyou,i)
                            if start == 0:
                                break
                            d_info['anyou'] = i[start:end]
                            # 获取原告和被告
                            if '诉' in i:
                                p = re.split('诉',i)
                                if '号' in p[0]:
                                    d_info['plaintiff'] = p[0].split('号')
                                else:
                                    d_info['plaintiff'] = p[0]
                                d_info['pname'] = re.findall('(.*?)%s' % d_info['anyou'],p[1])
                            else:
                                d_info['pname'] = re.findall('(.*?)%s' % d_info['anyou'],party)[0]
                        
                    f = []
                if start == 0:
                    continue
                d_info['md5'] = ktgg.get_md5(d_info['body'],d_info['url'])
                ktgg.ins_mysql(d_info,'ktgg_kt_wuhan',db,cursor)

    def main(self):
        links = self.qingqiu()
        self.parse_html(links)

if __name__ == "__main__":
    kh = Ktgg_hunan()
    kh.main()
