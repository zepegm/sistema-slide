import os
import sqlite3


caminho = os.path.expanduser('~') + '\\' + 'OneDrive - Secretaria da Educação do Estado de São Paulo\\IGREJA\\sistema-slide_db\\Sistema-slide.db'

class db:
    def __init__(self):
        self.caminho = caminho

    def executarConsultaVetor(self, sql):
        con = sqlite3.connect(caminho)
        
        cur = con.cursor()

        cur.execute(sql)

        result = [item[0] for item in cur.fetchall()]

        con.close()

        return result        

    def executarConsulta(self, sql):
        con = sqlite3.connect(caminho)
        con.row_factory = sqlite3.Row        
        cur = con.cursor()

        cur.execute(sql)

        result = [dict(row) for row in cur.fetchall()]
        
        #for row in cur.fetchall():
            #print(row)

        con.close()

        return result
    
    def inserirNovoHino(self, harpa):
        try:
            con = sqlite3.connect(caminho)
            cur = con.cursor()      

            # inserir slides
            sql = 'DELETE FROM slides_harpa WHERE id_harpa = %s' % harpa['numero']
            cur.execute(sql)

            for sld in harpa['slides']:
                anotacao = 'null'

                if 'anotacao' in sld.keys():
                    if sld['anotacao'] != '':
                        anotacao = "'%s'" % sld['anotacao']

                sql = "INSERT INTO slides_harpa VALUES(%s, %s, '%s', '%s', %s, %s)" % (harpa['numero'], sld['pos'], sld['text-slide'], sld['subtitle'], sld['cat'], anotacao)
                cur.execute(sql)  


            # inserir letras

            sql = 'DELETE FROM letras_harpa WHERE id_harpa = %s' % harpa['numero']
            cur.execute(sql)

            for letra in harpa['letra']:
                sql = "INSERT INTO letras_harpa VALUES(%s, %s, '%s', %s)" % (harpa['numero'], letra['paragrafo'], letra['texto'], letra['pagina'])
                cur.execute(sql)

            con.commit()
            con.close()
            return True                

        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            return False


    def inserirNovaMusica(self, musica):   

        try:
            con = sqlite3.connect(caminho)
            cur = con.cursor()
            
            # primeira etapa é inserir a música
            sql = "INSERT INTO musicas(titulo) VALUES('%s')" % musica['titulo']
            cur.execute(sql)

            id = cur.lastrowid

            # agora preciso inserir os slides
            for sld in musica['slides']:
                anotacao = 'null'

                if 'anotacao' in sld.keys():
                    if sld['anotacao'] != '':
                        anotacao = "'%s'" % sld['anotacao']

                sql = "INSERT INTO slides VALUES(%s, %s, '%s', '%s', %s, %s)" % (id, sld['pos'], sld['text-slide'], sld['subtitle'], sld['cat'], anotacao)
                cur.execute(sql)

            # agora irei inserir os vínculos
            for vin in musica['vinculos']:
                sql = "INSERT INTO vinculos_x_musicas VALUES(%s, %s, %s, '%s')" % (id, vin['vinc'], vin['status'], vin['descricao'])
                cur.execute(sql)

            # por último inserir as letras para visualização
            for letra in musica['letra']:
                sql = "INSERT INTO letras VALUES(%s, %s, '%s', %s)" % (id, letra['paragrafo'], letra['texto'], letra['pagina'])
                cur.execute(sql)

            con.commit()
            con.close()

            # inserir no log
            insert_log(1, 2, id, 0)

            return {'id':id, 'log':'Operação realizada com sucesso!'}
        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            return {'id':0, 'log':'Erro ao tentar acessar banco de dados.<br><span class="fw-bold">Descrição: </span>' + str(error)}
        

    def alterarMusica(self, musica):
        try:
            con = sqlite3.connect(caminho)
            cur = con.cursor()
            
            # primeira preciso alterar a música
            sql = "UPDATE musicas set titulo = '%s' WHERE id = %s" % (musica['titulo'], musica['destino'])
            cur.execute(sql)

            # agora preciso inserir os slides

            # primeiro vou deletar os antigos
            sql = 'DELETE FROM slides WHERE id_musica = %s' % musica['destino']
            cur.execute(sql)

            for sld in musica['slides']:
                anotacao = 'null'

                if 'anotacao' in sld.keys():
                    if sld['anotacao'] != '':
                        anotacao = "'%s'" % sld['anotacao']

                sql = "INSERT INTO slides VALUES(%s, %s, '%s', '%s', %s, %s)" % (musica['destino'], sld['pos'], sld['text-slide'], sld['subtitle'], sld['cat'], anotacao)
                cur.execute(sql)

            # agora irei inserir os vínculos

            # primeiro preciso remover os vínculos antigos
            sql = 'DELETE FROM vinculos_x_musicas WHERE id_musica = %s' % musica['destino']
            cur.execute(sql)

            for vin in musica['vinculos']:
                sql = "INSERT INTO vinculos_x_musicas VALUES(%s, %s, %s, '%s')" % (musica['destino'], vin['vinc'], vin['status'], vin['descricao'])
                cur.execute(sql)

            # por último inserir as letras para visualização

            # primeiro preciso remover a letra antiga
            sql = 'DELETE FROM letras WHERE id_musica = %s' % musica['destino']
            cur.execute(sql)

            for letra in musica['letra']:
                sql = "INSERT INTO letras VALUES(%s, %s, '%s', %s)" % (musica['destino'], letra['paragrafo'], letra['texto'], letra['pagina'])
                cur.execute(sql)

            con.commit()
            con.close()

            insert_log(2, 2, musica['destino'], 0)

            return {'id':int(musica['destino']), 'log':'Alteração realizada com sucesso!'}
        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            return {'id':0, 'log':'Erro ao tentar acessar banco de dados.<br><span class="fw-bold">Descrição: </span>' + str(error)}        

    def insertOrUpdate(self, dados, tabela):
            
        try:
            con = sqlite3.connect(caminho)
            cur = con.cursor()

            keys = ""
            data = ""
            update = ""

            for item in dados:
                keys += item + ", "
                data += dados[item] + ", "

                if item != 'id_musica':
                    update += item + "=" + dados[item] + ", "

            sql = "INSERT OR IGNORE INTO " + tabela + " (" + keys[:-2] + ") VALUES(" + data[:-2] + ")"

            print(sql)

            cur.execute(sql)

            sql = 'UPDATE %s SET %s WHERE ' % (tabela, update[:-2])
            print(sql)
            con.commit()
            con.close()

            return True

        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            return False          


    def insertOrUpdateList(self, lista, tabela):
            
        try:
            con = sqlite3.connect(caminho)
            cur = con.cursor()

            for dados in lista:

                keys = ""
                data = ""
                update = ""

                for item in dados:
                    keys += item + ", "
                    data += dados[item] + ", "

                    if item != 'id_musica':
                        update += item + "=" + dados[item] + ", "

                sql = "INSERT INTO " + tabela + " (" + keys[:-2] + ") VALUES(" + data[:-2] + ") ON DUPLICATE KEY UPDATE " + update[:-2]

                #print(sql)

                cur.execute(sql)
            
            con.commit()
            con.close()

            return True

        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            return False                   


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
