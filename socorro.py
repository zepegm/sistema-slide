import os
import sqlite3
from MySQL import db

banco = db({'host':"localhost",    # your host, usually localhost
            'user':"root",         # your username
            'passwd':"Yasmin",  # your password
            'db':"sistema-slide"})

# pegar os dados da tabela alvo
order_by = 'livro, cap, ver'
campos = 'livro, cap, ver, texto'
tabela = 'biblia_nvt'

dados = banco.executarConsulta('select %s from %s order by %s' % (campos, tabela, order_by))

#print(dados)

caminho = os.path.expanduser('~') + '\\' + 'OneDrive - Secretaria da Educação do Estado de São Paulo\\IGREJA\\sistema-slide_db\\Sistema-slide.db'

con = sqlite3.connect(caminho)
cur = con.cursor()

for item in dados:
    data = ''
    for o in item:
        if item[o] == 'None':
            print('yes')
            data += 'null, '
        else:
            data += "'%s', " % item[o]

    sql = 'INSERT INTO %s(%s) VALUES(%s)' % (tabela, campos, data[:-2])
    cur.execute(sql)

con.commit()
con.close()