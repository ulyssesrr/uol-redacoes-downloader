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
class UOLSpider(scrapy.Spider):
	name = 'uol-redacoes-downloader'
	custom_settings = {'USER_AGENT':'Mozilla/5.0 (Windows; U; Windows NT 5.1; pt-BR; rv:1.9) Gecko/20080705 Firefox/3.0 Kapiko/3.0', 
					'LOG_LEVEL': 'INFO'}
		
	def __init__(self):
		with open('urls.txt', 'r') as f:
			self.start_urls = [url.strip() for url in f.readlines()]
	
	def parse(self, response):
		legacy_layout = response.url.lower().endswith('jhtm')
		if legacy_layout:
			url_redacoes = response.css('div#corrigidas a::attr("href")')
			tema = response.css('div#conteudo h1::text').extract()[0].strip()
		else:
			url_redacoes = response.css('table.lista-corrigidas a::attr("href")')
			tema = response.css('h1.pg-color10::text').extract()[0].strip()
			
		print('TEMA', tema)
		basePath = slugify(tema)
		os.makedirs(basePath, exist_ok=True)
		
		print("Buscando %d redações..." % (len(url_redacoes)))
		for i, url in enumerate(url_redacoes):
			print("URL", url.extract())
			#if "xemplos" in url.extract():
			yield scrapy.Request(url.extract(), meta={'basePath': basePath, 'idx': i, 'legacy_layout': legacy_layout}, callback=self.parse_redacao)
			
	def parse_redacao(self, response):
		if response.meta['legacy_layout']:
			redacao = self.parse_redacao_old_layout(response)
			rmCerto = re.compile(r'<span class=\"texto-corrigido\">.*?</span>')
		else:
			redacao = self.parse_redacao_new_layout(response)
			rmCerto = re.compile(r'<span class=\"certo\">.*?</span>')
			
		rmMultiSpace = re.compile(r'\s+')
	
		fileName = "%s-%d.txt" % (slugify(redacao['titulo']), redacao['idx'])
		essayFile = os.path.join(response.meta['basePath'], fileName)
		print(essayFile)
		
		with open(essayFile, 'w') as f:
			#print("1",redacao['paragrafos'])
			redacao['paragrafos'] = [rmCerto.sub('', para) for para in redacao['paragrafos']]
			#print("2",redacao['paragrafos'])
			redacao['paragrafos'] = [''.join(BeautifulSoup(para, "lxml").findAll(text=True)).strip() for para in redacao['paragrafos']]
			#print("4",redacao['paragrafos'])
			redacao['paragrafos'] = list(filter(lambda para : len(para) > 0, redacao['paragrafos']))
			#print("5",redacao['paragrafos'])
			redacao['paragrafos'] = [rmMultiSpace.sub(' ', para) for para in redacao['paragrafos']]
			#print("3",redacao['paragrafos'])
			texto = "\r\n\r\n".join(redacao['paragrafos'])
			f.write(texto)
		
		with open(os.path.join(response.meta['basePath'], 'notas.csv'), 'a') as f:
			writer = csv.writer(f)
			writer.writerow([fileName, redacao['notaTotal']] + redacao['notas'])
	
	def parse_redacao_new_layout(self, response):
		redacao = {}
		redacao['titulo'] = response.css('header.redacao h1::text').extract()[0].strip()
		redacao['idx'] = response.meta['idx']
		redacao['paragrafos'] = response.xpath('//div[@id="texto"]/p').extract()
		
		print("TITULO", redacao['titulo'])
		
		tableNotas = response.css('table.table-redacoes')[0]
		redacao['notas'] = [float(nota.replace(',', '.')) for nota in tableNotas.css("td::text").extract()[1::2]]
		redacao['notaTotal'] = float(tableNotas.css("th::text").extract()[3].replace(',', '.'))
		#print(redacao['notas'], redacao['notaTotal'])
		assert sum(redacao['notas']) == redacao['notaTotal']
		return redacao

	def parse_redacao_old_layout(self, response):
		redacao = {}
		redacao['titulo'] = response.css('div#texto h1::text').extract()[0].strip()
		redacao['idx'] = response.meta['idx']
		redacao['paragrafos'] = response.css('div#texto').extract()[0]
		start_idx = redacao['paragrafos'].index('</h1>') + len('</h1>')
		end_idx = redacao['paragrafos'].index('<h3')
		redacao['paragrafos'] = redacao['paragrafos'][start_idx:end_idx]
		redacao['paragrafos'] = redacao['paragrafos'].split('<br><br>')
		
		
		print("TITULO", redacao['titulo'])
		
		tableNotas = response.css('table#comp')[0]
		redacao['notas'] = [float(nota.replace(',', '.')) for nota in tableNotas.css("td::text").extract()[2::3]]
		redacao['notaTotal'] = float(response.css("table.total td.destaque::text").extract()[0].replace(',', '.'))
		print(redacao['notas'], redacao['notaTotal'])
		assert sum(redacao['notas']) == redacao['notaTotal']
		return redacao
