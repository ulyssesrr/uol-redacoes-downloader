#!/usr/bin/env python3
# vim: set fileencoding=utf-8 :

import csv
import os
import re

from bs4 import BeautifulSoup

def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    import unicodedata
    import re
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub('[^\w\s-]', '', str(value)).strip().lower()
    return re.sub('[-\s]+', '-', value)

import scrapy
from scrapy.settings import Settings
class BlogSpider(scrapy.Spider):
	name = 'uol-redacoes-downloader'
	start_urls = ['http://educacao.uol.com.br/bancoderedacoes/propostas/carta-convite-discutir-discriminacao-na-escola.htm']
	custom_settings = {'USER_AGENT':'Mozilla/5.0 (Windows; U; Windows NT 5.1; pt-BR; rv:1.9) Gecko/20080705 Firefox/3.0 Kapiko/3.0', 
					'LOG_LEVEL': 'INFO'}
		
	def parse(self, response):
		tema = response.css('h1.pg-color10::text').extract()[0].strip()
		print('TEMA', tema)
		basePath = slugify(tema)
		os.makedirs(basePath, exist_ok=True)
		url_redacoes = response.css('table.lista-corrigidas a::attr("href")')
		print("Buscando %d redações..." % (len(url_redacoes)))
		for i, url in enumerate(url_redacoes):
			print("URL", url.extract())
			yield scrapy.Request(url.extract(), meta={'basePath': basePath, 'idx': i}, callback=self.parse_redacao)
	
	def parse_redacao(self, response):
		redacao = {}
		redacao['titulo'] = response.css('header.redacao h1::text').extract()[0].strip()
		redacao['idx'] = response.meta['idx']
		redacao['paragrafos'] = response.xpath('//div[@id="texto"]/p').extract()
		
		print("TITULO", len(response.css('header.redacao h1').extract()), redacao['titulo'])
		
		tableNotas = response.css('table.table-redacoes')[0]
		notas = [float(nota.replace(',', '.')) for nota in tableNotas.css("td::text").extract()[1::2]]
		notaTotal = float(tableNotas.css("th::text").extract()[3].replace(',', '.'))
		assert sum(notas) == notaTotal
		print(notas, notaTotal)
		
		#print("PARA", len(redacao['paragrafos']), redacao['paragrafos'])
		
		fileName = "%s-%d.txt" % (slugify(redacao['titulo']), redacao['idx'])
		essayFile = os.path.join(response.meta['basePath'], fileName)
		print(essayFile)
		rmCerto = re.compile(r'<span class=\"certo\">.*?</span>')
		with open(essayFile, 'w') as f:
			redacao['paragrafos'] = [rmCerto.sub('', para) for para in redacao['paragrafos']]
			redacao['paragrafos'] = [para.replace('  ', ' ') for para in redacao['paragrafos']]
			redacao['paragrafos'] = [BeautifulSoup(para).text for para in redacao['paragrafos']]
			texto = "\r\n\r\n".join(redacao['paragrafos'])
			f.write(texto)
		
		with open(os.path.join(response.meta['basePath'], 'notas.csv'), 'a') as f:
			writer = csv.writer(f)
			writer.writerow([fileName, notaTotal] + notas)
			
		#for post_title in response.css('div.entries > ul > li a::text').extract():
		#	print('title', post_title)
		#	yield {'title': post_title}
