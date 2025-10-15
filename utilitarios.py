import numpy as np
import datetime
import os
from pathlib import Path

def pegarListaSemanas(ano, mes):
    # Defina o ano e o mês desejados (por exemplo, maio de 2022)
    year_month = '%s-%s' % (ano, mes)

    # Calcula a primeira segunda-feira do mês, pega a semana anterior e busca a primeira semana do mês que vem
    cont = 0

    lista = []
    aux = mes

    segunda = np.busday_offset(year_month, -1, roll='forward', weekmask='Mon')
    domingo = segunda.item() + datetime.timedelta(days=6)

    lista.append({'data':segunda.item().strftime('%Y-%m-%d'), 'inicio':segunda.item().strftime('%d/%m'), 'fim':domingo.strftime('%d/%m/%Y')})


    while (aux == mes):
        segunda = np.busday_offset(year_month, cont, roll='forward', weekmask='Mon')
        domingo = segunda.item() + datetime.timedelta(days=6)
        
        lista.append({'data':segunda.item().strftime('%Y-%m-%d'), 'inicio':segunda.item().strftime('%d/%m'), 'fim':domingo.strftime('%d/%m/%Y')})
        aux = segunda.item().strftime('%m')
        cont += 1

    return lista


def pegarTrimestre(data):
    mes = data.month

    trimestre = (mes - 1) // 3 + 1

    return f"{trimestre}º Timestre"
    
def pegarLicoes(data):
    mes = data.month
    ano = data.year

    licoes = []

    trimestre = (mes - 1) // 3 + 1
    inicio = (trimestre - 1) * 3 + 1
    fim = inicio + 2

    cont_licao = 1
    licao_selecionada = 0

    # Encontrar o primeiro dia do mês
    primeiro_dia = datetime.datetime(data.year, inicio, 1)
    
    # Calcular quantos dias precisamos adicionar para chegar ao primeiro domingo
    dias_a_adicionar = (6 - primeiro_dia.weekday()) % 7
    
    # Obter o primeiro domingo
    primeiro_domingo = primeiro_dia + datetime.timedelta(days=dias_a_adicionar)

    if primeiro_dia <= data:
        licao_selecionada = cont_licao - 1

    licoes.append({'licao':cont_licao, 'dia':primeiro_domingo, 'selected':''})

    cont_licao += 1
    proximo_domingo = primeiro_domingo + datetime.timedelta(days=7)
    

    while (proximo_domingo.month <= fim and proximo_domingo.year <= ano):
        licoes.append({'licao':cont_licao, 'dia':proximo_domingo, 'selected':''})
        
        if proximo_domingo <= data:
            licao_selecionada = cont_licao - 1        
        
        cont_licao += 1
        proximo_domingo = proximo_domingo + datetime.timedelta(days=7)

    licoes[licao_selecionada]['selected'] = 'selected'

    return licoes

# Função para verificar se um arquivo existe
def verificar_arquivo_existe(caminho_arquivo):
    return os.path.isfile(caminho_arquivo)


def listar_diretorios(caminho, prefixo=""):
    with open("estrutura.txt", "w", encoding="utf-8") as f:
        def listar(caminho, prefixo=""):
            for item in caminho.iterdir():
                f.write(prefixo + "|-- " + item.name + "\n")
                if item.is_dir():
                    listar(item, prefixo + "    ")
        listar(Path("."))