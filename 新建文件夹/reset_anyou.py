import pymysql
import redis

r = redis.Redis(host='127.0.0.1',port=6379,db=0)
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', db='litianming', charset='utf8')
cursor = conn.cursor()
sql = 'select * from anyou'
cursor.execute(sql)
rows = cursor.fetchall()
for a in rows:
    r.lpush('anyou',a[1])
