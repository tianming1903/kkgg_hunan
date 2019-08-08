'''
此代码爬取湖南的开庭公告，
'''
import ktgg
import re

class Ktgg_hunan():
    def __init__(self):
        # 定义审判员的别名
        self.judge = [
            '主审法官','审判员','承办人','审判长'
        ]
        # 定义原告的别名
        self.plaintiff = [
            '原告人','原告','公诉机关'
        ]
        # 定义清理符号
        self.tihuan = ['；','：','人']

        # 起始url 
        self.url = "http://zzxfy.chinacourt.gov.cn/article/index/id/M0gxNjCwMCAOAAA.shtml"

          
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
            url = 'http://zzxfy.chinacourt.gov.cn' + i
            text,html= ktgg.request_dis(url)
            if text == 0:
                continue

            # 提取一些信息
            d['posttime'] = re.findall('发布时间(.*?)<',html)[0].replace('：','').strip()
            d['court'] = '湖南省渌口区人民法院'
            d['source'] = self.url
            d['url'] = url
            d['title'] = re.findall("'b_title'>(.*?)<",html)[0]
            d['province'] = '湖南省'
            # 文本不存在就用标题替代文本
            if text == '':
                text = d['title']
            # 做一个特殊的处理，删除这两条信息(一个非开庭公告，一个内容为表格形式)
            if '保护当事人的诉讼权利' in d['title']:
                continue
            if '2012年8月1日至8月31日' in d['title']:
                continue
            self.parse_text(text,d,db,cursor)

        # 关闭数据库
        ktgg.clo_mysql(db,cursor)

    def parse_text(self,text,d,db,cursor):
        # 有二种格式，要分为二种情况讨论
        if re.findall('\d{2,4}',d['title']):
            infos = re.split('\d{1,2}[、.]',text)
        else:
            infos = [text]
        # 遍历每条开庭信息
        for info in infos:
            d_info = d.copy()
            i = re.split('\s',info)
            info = list(filter(None,i))
            if len(info) == 1:
                continue
            d_info['body'] = ''.join(info).replace('\xa0','').replace('\u3000','').replace('\n','').replace('\r','')
            for i in info:
                if '案由' in i:
                    d_info['anyou'] = i.split('案由')[1].replace('：','')
                if '时间' in i:
                    sorttime = re.findall('\d{4}年.*?日',i)
                    if sorttime:
                        d_info['sorttime'] = sorttime[0]
                if '案号' in i:
                    d_info['caseNo'] = i.split('案号')[1]
                if '地点' in i:
                    d_info['courtNum'] = i.split('地点')[1]
                if '被告' in i:
                    d_info['pname'] = i.split('被告')[1]
                for judge in self.judge:
                    if judge in i:
                        d_info['judge'] = i.split(judge)[1]
                        break
                for plaintiff in self.plaintiff:
                    if plaintiff in i:
                        d_info['plaintiff'] = i.split(plaintiff)[1]
                        break

            if '诉' in d_info['title']:
                l = re.findall('(.*?)诉(.*)',d_info['title'])[0]
                d_info['plaintiff'] = l[0]
                pname = re.findall('(.*?)%s' % d_info['anyou'],l[1])
                if pname:
                    d_info['pname'] = pname[0] 

            # 字符清洗
            for key,value in d_info.items():
                for x in self.tihuan:
                    value = value.replace(x,'')
                d_info[key] = value
            d_info['md5'] = ktgg.get_md5(d_info['body'],d['url'])
            
            ktgg.ins_mysql(d_info,'ktgg_kt_wuhan',db,cursor)

    def main(self):
        links = self.qingqiu()
        self.parse_html(links)

if __name__ == "__main__":
    kh = Ktgg_hunan()
    kh.main()

