#!/usr/bin/env python3
# vim: set fileencoding=utf-8 :

import json
import sys

import argparse


parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('notas', metavar='NOTAS', type=str, help='Notas. Ex: 1.5,2.0,1.5,0.5,1.0')
parser.add_argument('url', metavar='URL', type=str, help='URL da redação a ser substituída.')
parser.add_argument('--titulo', help='Título da redação. Se não especificado, o primeiro parágrafo será utilizado como título.')
parser.add_argument('redacao', metavar='texto.txt', type=str, help='Arquivo com texto da redação')
parser.add_argument('arquivo', metavar='arquivo.json', type=str, help='Arquivo onde a entrada será adicionada')

args = parser.parse_args()

try:
	notas = [float(nota) for nota in args.notas.split(',')]
except ValueError:
	print("Erro: Notas inválidas. Exemplo correto: 1.5,2.0,1.5,0.5,1.0")
	sys.exit(1)
	
if len(notas) != 5:
	print("Erro: %d nota(s) informada(s). Exemplo correto: 1.5,2.0,1.5,0.5,1.0" % (len(notas)))
	sys.exit(1)



with open(args.redacao, 'r') as f:
	texto = f.read()
	if "\r\n" in texto:
		paragrafos = texto.split("\r\n\r\n")
	else:
		paragrafos = texto.split("\n\n")

url = args.url.lower()

if args.titulo is None:
	titulo = paragrafos[0]
	paragrafos = paragrafos[1:]
else:
	titulo = args.titulo

print("Notas: ", notas)
print("URL: %s" % (url))
print("Título: %s" % (titulo))
print("# Parágrafos: %d" % (len(paragrafos)))
    
try:
	with open(args.arquivo, 'r') as f:
		custom = json.load(f)
		print("Entradas pré-existentes: %d" % (len(custom)))
except FileNotFoundError:
	custom = {}
	

redacao = {}
redacao['titulo'] = titulo
redacao['paragrafos'] = paragrafos
redacao['notas'] = notas
redacao['nota_total'] = sum(notas)

custom[url] = redacao

with open(args.arquivo, 'w') as f:
	json.dump(custom, f, sort_keys=True, indent=4)
