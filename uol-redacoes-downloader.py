#!/usr/bin/env python3
# vim: set fileencoding=utf-8 :

import csv
import logging
import os
import re

from bs4 import BeautifulSoup


import scrapy
from scrapy.settings import Settings

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

LAYOUT_UOL_0 = 'uol-0'
LAYOUT_UOL_1 = 'uol-1'
LAYOUT_BRASILESCOLA = 'brasilescola'

class UOLSpider(scrapy.Spider):
	name = 'uol-redacoes-downloader'
	custom_settings = {'USER_AGENT':'Mozilla/5.0 (Windows; U; Windows NT 5.1; pt-BR; rv:1.9) Gecko/20080705 Firefox/3.0 Kapiko/3.0', 
					'LOG_LEVEL': logging.INFO}
		
	def __init__(self):
		with open('urls.txt', 'r') as f:
			self.start_urls = [url.strip() for url in f.readlines()]
	
	def parse(self, response):
		lower_url = response.url.lower()
		
		
		if 'vestibular.brasilescola' in lower_url:
			url_redacoes = response.css('table#redacoes_corrigidas a::attr("href")')
			skip_len = len('Tema: ')
			tema = response.css('span.definicao::text').extract()[0].strip()[skip_len:].strip()
			layout_type = LAYOUT_BRASILESCOLA
		else:
			legacy_layout = lower_url.endswith('jhtm')
			if legacy_layout:
				url_redacoes = response.css('div#corrigidas a::attr("href")')
				tema = response.css('div#conteudo h1::text').extract()[0].strip()
				layout_type = LAYOUT_UOL_0
			else:
				url_redacoes = response.css('table.lista-corrigidas a::attr("href")')
				tema = response.css('h1.pg-color10::text').extract()[0].strip()
				layout_type = LAYOUT_UOL_1
			
		basePath = slugify(tema)
		os.makedirs(basePath, exist_ok=True)
		
		self.logger.info("TEMA: %s - Redações: %d - Pasta Destino: %s" % (tema, len(url_redacoes), basePath))
		for i, url in enumerate(url_redacoes):
			self.logger.debug("URL: %s" % (url.extract()))
			#if "xemplos" in url.extract():
			yield scrapy.Request(url.extract(), meta={'basePath': basePath, 'idx': i, 'layout_type': layout_type}, callback=self.parse_redacao)
			
	def get_deep_html_text(self, elem):
		return ''.join(BeautifulSoup(elem, "lxml").findAll(text=True)).strip()
	
	def parse_redacao(self, response):
		layout_type = response.meta['layout_type']
		if layout_type == LAYOUT_UOL_0:
			redacao = self.parse_redacao_old_layout(response)
			rmCerto = re.compile(r'<span class=\"texto-corrigido\">.*?</span>')
		elif layout_type == LAYOUT_UOL_1:
			redacao = self.parse_redacao_new_layout(response)
			rmCerto = re.compile(r'<span class=\"certo\">.*?</span>')
		elif layout_type == LAYOUT_BRASILESCOLA:
			redacao = self.parse_redacao_brasilescola(response)
			rmCerto = None
		else:
			raise Exception("Unknow layout type: %s" % (layout_type))
			
		rmMultiSpace = re.compile(r'\s+')
	
		fileName = "%s-%d.txt" % (slugify(redacao['titulo']), redacao['idx'])
		essayFile = os.path.join(response.meta['basePath'], fileName)
		self.logger.debug(essayFile)
		
		with open(essayFile, 'w') as f:
			#print("1",redacao['paragrafos'])
			if rmCerto is not None:
				redacao['paragrafos'] = [rmCerto.sub('', para) for para in redacao['paragrafos']]
			#print("2",redacao['paragrafos'])
			redacao['paragrafos'] = [self.get_deep_html_text(para) for para in redacao['paragrafos']]
			#print("4",redacao['paragrafos'])
			redacao['paragrafos'] = list(filter(lambda para : len(para) > 0, redacao['paragrafos']))
			#print("5",redacao['paragrafos'])
			redacao['paragrafos'] = [rmMultiSpace.sub(' ', para) for para in redacao['paragrafos']]
			#print("3",redacao['paragrafos'])
			texto = "\r\n\r\n".join(redacao['paragrafos'])
			if not "sem" in redacao['titulo'].lower() or not ("titulo" in redacao['titulo'].lower() or "título" in redacao['titulo'].lower()):
				texto = redacao['titulo'] + "\r\n\r\n" + texto
			f.write(texto)
		
		with open(os.path.join(response.meta['basePath'], 'notas.csv'), 'a') as f:
			writer = csv.writer(f)
			writer.writerow([fileName, redacao['notaTotal']] + redacao['notas'] + [response.url])
			
	def parse_redacao_brasilescola(self, response):
		redacao = {}
		
		skip_len = len('BANCO DE REDAÇÕES ')
		titulo = response.css('h1::text').extract()[0].strip()[skip_len:].strip()
		if titulo.lower().startswith('título: '):
			skip_len = len('título: ')
			titulo = titulo[skip_len:].strip()
		
		redacao['titulo'] = titulo
		redacao['idx'] = response.meta['idx']
		redacao['paragrafos'] = response.css('div.conteudo-materia > p').extract()
		
		self.logger.debug("TITULO: [%s]" % (redacao['titulo']))
		
		tableNotas = response.css('table#redacoes_corrigidas')[0]
		redacao['notas'] = [float(nota)/100 for nota in tableNotas.css("td::text").extract()[4:17:3]]
		#for i, elem in enumerate(tableNotas.css("td").extract()):
		#	print(i, self.get_deep_html_text(elem))
		notaTotalTxt = self.get_deep_html_text(tableNotas.css("td").extract()[18])
		notaTotal = [int(s) for s in notaTotalTxt.split() if s.isdigit()][0]
		redacao['notaTotal'] = float(notaTotal)/100
		#print(redacao['notas'], redacao['notaTotal'])
		assert sum(redacao['notas']) == redacao['notaTotal']
		return redacao
	
	def parse_redacao_new_layout(self, response):
		redacao = {}
		redacao['titulo'] = response.css('header.redacao h1::text').extract()[0].strip()
		redacao['idx'] = response.meta['idx']
		redacao['paragrafos'] = response.xpath('//div[@id="texto"]/p').extract()
		
		self.logger.debug("TITULO: %s" % (redacao['titulo']))
		
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
		redacao['paragrafos'] = re.split("\<br\>[\s]*\<br\>", redacao['paragrafos'])#.split('<br><br>')
		
		self.logger.debug("TITULO: %s" % (redacao['titulo']))
		
		tableComp = response.css('table#comp')
		if len(tableComp) == 1:
			tableNotas = tableComp[0]
			redacao['notas'] = [float(nota.replace(',', '.')) for nota in tableNotas.css("td::text").extract()[2::3]]
			redacao['notaTotal'] = float(response.css("table.total td.destaque::text").extract()[0].replace(',', '.'))
			#print(redacao['notas'], redacao['notaTotal'])
			assert sum(redacao['notas']) == redacao['notaTotal']
			return redacao
		else:
			self.logger.error("Redação sem tabela de notas, ignorando... (%s)" % (response.url))
