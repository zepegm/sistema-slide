from MySQL import db
import random
import sqlite3


def executarConsultaLista(banco, tabela):
    conn = sqlite3.connect(banco)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    codigoSQL = "SELECT * FROM %s" % tabela
    cursor.execute(codigoSQL)
    return [dict(row) for row in cursor.fetchall()]


banco = db({'host':"localhost",    # your host, usually localhost
            'user':"root",         # your username
            'passwd':"Yasmin",  # your password
            'db':"sistema-slide"})

lista_livros = banco.executarConsulta('select * from livro_biblia')

for livro in lista_livros:
    tabela = "`" + livro['descricao'].replace('1', 'I').replace('2', 'II').replace('3', 'III') + "`"
    banco_original = executarConsultaLista(r'C:\Users\giuseppe.manzella\Documents\GitHub\roteiro-slides\BibliaFormat.db', tabela)
    print('inserindo ' + tabela)
    lista = []
    for item in banco_original:
        try:
            lista.append({'livro':str(livro['id']), 'cap':str(item['Cap']), 'ver':str(item['Ver']), 'texto':"'" + item['NVT'] + "'"})
        except:
            print('erro.............. ')
            print(item)
            print('-------------------')
        
    banco.insertOrUpdateList(lista, 'biblia_nvt')



#for item in banco_original:
    #print(item)
