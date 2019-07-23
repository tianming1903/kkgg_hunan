# -*- coding: utf-8 -*-
import scrapy


class Hunan1Spider(scrapy.Spider):
    name = 'hunan1'
    allowed_domains = ['kfqfy.chinacourt.gov.cn']
    start_urls = ['http://kfqfy.chinacourt.gov.cn/']
    
    def parse(self, response):
        pass
