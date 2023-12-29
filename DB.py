import sqlite3

def executarConsultaGeral(banco, sql):
    conn = sqlite3.connect(banco)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(sql)
    return [dict(row) for row in cursor.fetchall()]

def executarConsulta(banco, sql):
    conn = sqlite3.connect(banco)
    cursor = conn.cursor()
    #print(sql)
    cursor.execute(sql)

    return cursor.fetchone()