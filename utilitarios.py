import numpy as np
import datetime

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

    if mes > 0 and mes < 4:
        return '1º Trimestre'
    elif mes > 3 and mes < 7:
        return '2º Trimestre'
    elif mes > 6 and mes < 10:
        return '3º Timestre'
    else:
        return '4º Timestre'
    
def pegarLicoes(data):
    mes = data.month

    if mes > 0 and mes < 4:
        pass