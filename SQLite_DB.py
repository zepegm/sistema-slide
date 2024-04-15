import os
import sqlite3


caminho = os.path.expanduser('~') + '\\' + 'OneDrive - Secretaria da Educação do Estado de São Paulo\\IGREJA\\Historico-New.db'

def insert_log(atividade, tipo, id, cap):
    sql = 'INSERT INTO `log` (data_hora, atividade, tipo, '

    if tipo == 1:
        sql += "livro_biblia, capitulo) VALUES (datetime('now','localtime'), %s, %s, %s, %s)" % (atividade, tipo, id, cap)
    elif tipo == 2:
        sql += "id_musica) VALUES (datetime('now','localtime'), %s, %s, %s)" % (atividade, tipo, id)
    elif tipo == 3:
        sql += "id_harpa) VALUES (datetime('now','localtime'), %s, %s, %s)" % (atividade, tipo, id)

    try:
        con = sqlite3.connect(caminho)
        cur = con.cursor()

        # antes de inserir, limpar dados antigos do log
        cur.execute("DELETE FROM log WHERE atividade > 4 AND date(data_hora) < date('now', '-6 month')")

        cur.execute(sql)
        con.commit()
        con.close()
        return True
    except:
        return False
