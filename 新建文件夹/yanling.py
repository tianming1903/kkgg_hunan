
'''
此代码爬取湖南的开庭公告，
'''
import ktgg
import re
import time


class Ktgg_hunan():
    def __init__(self):
        # 起始url 
        self.url = "http://ylxfy.chinacourt.gov.cn/article/index/id/M0gxMzAwNTAwMiACAAA.shtml"
        # 定义party
        self.party = [
            '审理(.*?)诉(.*)',
            '审理(.*?)与(.*)',
            '庭(.*?)诉(.*)',
            '庭(.*?)、(.*)'
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
            url = 'http://ylxfy.chinacourt.gov.cn' + i
            text,html= ktgg.request_dis(url)
            if text == 0:
                continue
            # 提取一些信息
            d['posttime'] = re.findall('发布时间(.*?)<',html)[0].replace('：','').strip()
            d['court'] = '炎陵县人民法院'
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
        for info in infos:
            if info:
                d_info = d.copy()
                # 提取时间
                d_info['body'] = info.replace('\xa0','').replace('\r','')
                sorttime = re.findall('\d{1,4}[年月].*?[日号]',info)
                if sorttime:
                    d_info['sorttime'] = sorttime[0]
                # 提取开庭地点
                courtNum = re.findall('在(.*?庭)',info)
                if courtNum:
                    d_info['courtNum'] = courtNum[0]
                d_info['md5'] = ktgg.get_md5(d_info['body'],d_info['url'])
                # 提取案由，原告，被告
                for party in self.party:
                    party = re.findall(party,info)
                    if party:
                        party = party[0]
                        d_info['plaintiff'] = party[0].replace('原告','').replace('人','')
                        anyou = ktgg.set_anyou()
                        start,end = ktgg.search_anyou(anyou,party[1])
                        d_info['anyou'] = party[1][start:end]
                        pname = re.findall('(.*?)%s' % d_info['anyou'],party[1])
                        if pname:
                            d_info['pname'] = pname[0].replace('被告','').replace('人','')
                            break
                    else:
                        continue
                d_info['md5'] = ktgg.get_md5(d_info['body'],d_info['url'])
                ktgg.ins_mysql(d_info,'ktgg_kt_wuhan',db,cursor)

    def main(self):
        links = self.qingqiu()
        self.parse_html(links)

if __name__ == "__main__":
    kh = Ktgg_hunan()
    kh.main()
