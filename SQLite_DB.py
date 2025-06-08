import os
import io
import sqlite3
import base64
import shutil
from utilitarios import verificar_arquivo_existe
from HTML_U import converHTML_to_PlainText

caminho = os.path.expanduser('~') + '\\' + 'OneDrive - Secretaria da Educação do Estado de São Paulo\\IGREJA\\sistema-slide_db\\Sistema-slide.db'
caminho_hook = os.path.expanduser('~') + '\\' + 'OneDrive - Secretaria da Educação do Estado de São Paulo\\log\\hook.db'
caminho_calendario = os.path.expanduser('~') + '\\' + 'OneDrive - Secretaria da Educação do Estado de São Paulo\\IGREJA\\sistema-slide_db\\Calendario.db'
caminho_old_musicas = os.path.expanduser('~') + '\\' + 'OneDrive - Secretaria da Educação do Estado de São Paulo\\IGREJA\\Músicas\\NewMusicas.db'

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

    def inserirNovoHinoVersionado(self, info):
        try:
            con = sqlite3.connect(caminho)
            cur = con.cursor()   

            sql = "INSERT INTO harpa_versionada(id_harpa, titulo_versao, desc_versao) VALUES(%s, '%s', '%s')" % (info['numero'], info['titulo_versao'], info['desc_versao'])
            cur.execute(sql)

            id = cur.lastrowid

            for sld in info['slides']:
                sql = "INSERT INTO slides_harpa_versionada VALUES(%s, %s, '%s', '%s', %s, '%s')" % (id, sld['pos'], sld['text-slide'], sld['subtitle'], sld['cat'], sld['anotacao'])
                cur.execute(sql)

            for paragrafo in info['letra']:
                sql = "INSERT INTO letras_harpa_versionada VALUES(%s, %s, '%s', %s)" % (id, paragrafo['paragrafo'], paragrafo['texto'], paragrafo['pagina'])
                cur.execute(sql)

            con.commit()
            con.close()
            return True

        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            return False
        
    def editarNovoHinoVersionado(self, id, info):
        try:
            con = sqlite3.connect(caminho)
            cur = con.cursor()   

            sql = "UPDATE harpa_versionada SET titulo_versao = '%s', desc_versao = '%s' WHERE id = %s" % (info['titulo_versao'], info['desc_versao'], id)
            cur.execute(sql)

            cur.execute('DELETE FROM slides_harpa_versionada WHERE id_harpa_versionada = %s' % id)
            for sld in info['slides']:
                sql = "INSERT INTO slides_harpa_versionada VALUES(%s, %s, '%s', '%s', %s, '%s')" % (id, sld['pos'], sld['text-slide'], sld['subtitle'], sld['cat'], sld['anotacao'])
                cur.execute(sql)

            cur.execute('DELETE FROM letras_harpa_versionada WHERE id_harpa_versionada = %s' % id)
            for paragrafo in info['letra']:
                sql = "INSERT INTO letras_harpa_versionada VALUES(%s, %s, '%s', %s)" % (id, paragrafo['paragrafo'], paragrafo['texto'], paragrafo['pagina'])
                cur.execute(sql)

            con.commit()
            con.close()
            return True

        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            return False        
    
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

    def inserirNovaPoesia(self, poesia):   

        try:
            con = sqlite3.connect(caminho)
            cur = con.cursor()
            
            # primeira etapa é inserir a música
            sql = "INSERT INTO poesia(titulo) VALUES('%s')" % poesia['titulo']
            cur.execute(sql)

            id = cur.lastrowid

            print(id)

            # agora preciso inserir os slides
            for sld in poesia['slides']:
                anotacao = 'null'

                if 'anotacao' in sld.keys():
                    if sld['anotacao'] != '':
                        anotacao = "'%s'" % sld['anotacao']

                sql = "INSERT INTO slide_poesia VALUES(%s, %s, '%s', '%s', %s)" % (id, sld['pos'], sld['text-slide'], sld['subtitle'], anotacao)
                cur.execute(sql)

            # por último inserir as letras para visualização
            for letra in poesia['letra']:
                sql = "INSERT INTO letras_poesia VALUES(%s, %s, '%s', %s)" % (id, letra['paragrafo'], letra['texto'], letra['pagina'])
                cur.execute(sql)

            con.commit()
            con.close()

            # inserir no log
            insert_log(10, 4, id, 0)

            return True
        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            return False


    def inserirNovaMusica(self, musica):   

        capa = 'images/upload_image.jpg'

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

            # inserir capa, pois se trata de uma música nova
            origem = 'static/images/SlidesPPTX/temp_capa.jpg'
            destino = 'static/images/capas/%s.jpg' % id

            if verificar_arquivo_existe(origem):
                shutil.move(origem, destino)
                sql = "INSERT INTO capas VALUES(%s, '%s.jpg')" % (id, id)
                cur.execute(sql)

                capa = 'images/capas/%s.jpg' % id

            con.commit()
            con.close()

            # inserir no log
            insert_log(1, 2, id, 0)

            return {'id':id, 'log':'Operação realizada com sucesso!', 'capa':capa}
        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            return {'id':0, 'log':'Erro ao tentar acessar banco de dados.<br><span class="fw-bold">Descrição: </span>' + str(error), 'capa':capa}

    def alterarPoesia(self, poesia):
        try:
            con = sqlite3.connect(caminho)
            cur = con.cursor()
            
            # primeira preciso alterar a música
            sql = "UPDATE poesia set titulo = '%s' WHERE id = %s" % (poesia['titulo'], poesia['destino'])
            cur.execute(sql)

            # agora preciso inserir os slides

            # primeiro vou deletar os antigos
            sql = 'DELETE FROM slide_poesia WHERE id_poesia = %s' % poesia['destino']
            cur.execute(sql)

            for sld in poesia['slides']:
                anotacao = 'null'

                if 'anotacao' in sld.keys():
                    if sld['anotacao'] != '':
                        anotacao = "'%s'" % sld['anotacao']

                sql = "INSERT INTO slide_poesia VALUES(%s, %s, '%s', '%s', %s)" % (poesia['destino'], sld['pos'], sld['text-slide'], sld['subtitle'], anotacao)
                cur.execute(sql)

            # por último inserir as letras para visualização

            # primeiro preciso remover a letra antiga
            sql = 'DELETE FROM letras_poesia WHERE id_poesia = %s' % poesia['destino']
            cur.execute(sql)

            for letra in poesia['letra']:
                sql = "INSERT INTO letras_poesia VALUES(%s, %s, '%s', %s)" % (poesia['destino'], letra['paragrafo'], letra['texto'], letra['pagina'])
                cur.execute(sql)

            con.commit()
            con.close()

            insert_log(11, 4, poesia['destino'], 0)

            return True
        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            return False


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

    def change_config(self, lista):
        try:
            con = sqlite3.connect(caminho)
            cur = con.cursor()

            for item in lista:
                sql = "UPDATE config SET valor = %s WHERE id = %s" % (item['valor'], item['id'])
                cur.execute(sql)

            con.commit()
            con.close() 
            return True 
        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            return False

    def insertOrUpdate(self, dados, id_name, tabela):
            
        try:
            con = sqlite3.connect(caminho)
            cur = con.cursor()

            keys = ""
            data = ""
            update = ""

            for item in dados:
                keys += item + ", "
                data += dados[item] + ", "

                if item != 'id_musica' and item != 'id_harpa' and item != 'id':
                    update += item + "=" + dados[item] + ", "

            sql = "INSERT INTO " + tabela + " (" + keys[:-2] + ") VALUES(" + data[:-2] + ") ON CONFLICT(" + id_name + ") DO UPDATE SET " + update[:-2]

            cur.execute(sql)

            #sql = 'UPDATE %s SET %s WHERE ' % (tabela, update[:-2])
            
            con.commit()
            con.close()

            return True

        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            #print(sql)
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
        
    def insertListBiblia(self, lista, tabela):
        try:
            con = sqlite3.connect(caminho)
            cur = con.cursor()

            for versiculo in lista:
                sql = "INSERT INTO %s VALUES(%s, %s, %s, '%s')" % (tabela, versiculo['livro'], versiculo['cap'], versiculo['ver'], versiculo['texto'])
                cur.execute(sql)
            
            con.commit()
            con.close()

            return True

        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            print(sql)
            return False
        
    def inserirRoteiroMusical(self, lista):
        try:
            con = sqlite3.connect(caminho)
            cur = con.cursor()

            cur.execute('DELETE FROM roteiro_musical')

            for item in lista:
                cur.execute("INSERT INTO roteiro_musical(id_origem, `tabela-origem`) VALUES(%s, '%s')" % (item['id'], item['origem']))
            
            con.commit()
            con.close()

            return True

        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            return False
        
    def executeCustomQuery(self, sql):
        try:
            con = sqlite3.connect(caminho)
            cur = con.cursor()

            cur.execute(sql)
            
            con.commit()
            con.close()

            return True

        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            return False
        
    def inserirHistorico(self, dia, tema, obs, url, lista):
        try:
            con = sqlite3.connect(caminho)
            cur = con.cursor()

            sql = f"INSERT INTO Historico_Roteiro(Dia, Tema, OBS, URL) VALUES ({dia}, {tema}, {obs}, {url})"
            cur.execute(sql)

            id = cur.lastrowid

            for item in lista:
                sql = f"INSERT INTO Historico_Registro_Eventos VALUES ({id}, {item['id_tipo_evento']}, {item['id_departamento']}, {item['id_cat_biblia']}, {item['id_cat_musica']}, {item['id_musica']}, {item['id_harpa']}, {item['id_livro_biblia']}, {item['cap_biblia']})"
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
    elif tipo == 4:
        sql += "id_poesia) VALUES (datetime('now','localtime'), %s, %s, %s)" % (atividade, tipo, id)

    try:
        con = sqlite3.connect(caminho)
        cur = con.cursor()

        # antes de inserir, limpar dados antigos do log
        cur.execute("DELETE FROM log WHERE date(data_hora) < date('now', '-6 month')")

        cur.execute(sql)
        con.commit()
        con.close()
        return True
    except:
        return False
    

def get_all_hook():
    con = sqlite3.connect(caminho_hook)
    con.row_factory = sqlite3.Row        
    cur = con.cursor()

    cur.execute(r"""select id,
    strftime('%d/%m/%Y', data) as dia,
    strftime('%Hh%M', data) as hora,
    CASE strftime('%w', data)
        WHEN '0' THEN 'Domingo'
        WHEN '1' THEN 'Segunda'
        WHEN '2' THEN 'Terça'
        WHEN '3' THEN 'Quarta'
        WHEN '4' THEN 'Quinta'
        WHEN '5' THEN 'Sexta'
        WHEN '6' THEN 'Sábado'
    END semana
    from registro_evento order by data desc""")

    result = [dict(row) for row in cur.fetchall()]
        
        #for row in cur.fetchall():
            #print(row)

    con.close()

    return result

def get_photos(id):
    con = sqlite3.connect(caminho_hook)
    con.row_factory = sqlite3.Row        
    cur = con.cursor()

    cur.execute('select foto from fotos where id_registro = %s' % id)

    fotos = []
        
    for row in cur.fetchall():
        image = base64.b64encode(io.BytesIO(row[0]).getvalue())
        fotos.append(image.decode())

    con.close()

    return fotos

def inserir_calendario_semanal(lista): 
    con = sqlite3.connect(caminho_calendario)
    cur = con.cursor()
    cur.execute("DELETE FROM calendario_semanal") # limpar tabela

    try:
        cont = 1
        for item in lista:
            cur.execute("INSERT INTO calendario_semanal VALUES(%s, %s, %s, '%s', '%s', 1)" % (cont, item['semana'], item['mensal'], item['text'].replace('&nbsp;', ' '), converHTML_to_PlainText(item['text'])))
            cont += 1

        con.commit()
        con.close()
        return True
    
    except Exception as error:
        print("An exception occurred:", error) # An exception occurred: division by zero
        return False
    
def inserir_calendario_mensal(lista, mes):
    con = sqlite3.connect(caminho_calendario)
    cur = con.cursor()

    try:
        cur.execute(r"DELETE FROM `calendario_mensal` WHERE strftime('%m', inicio) = '" + mes + "'")
        
        for item in lista:
            cur.execute("INSERT INTO calendario_mensal(inicio, fim, texto, plain_text, ativo) VALUES('%s', '%s', '%s', '%s', 1)" % (item['data_inicial'], item['data_final'], item['texto'].replace('&nbsp;', ' '), converHTML_to_PlainText(item['texto'])))

        con.commit()
        con.close()
        return True

    except Exception as error:
        print("An exception occurred:", error) # An exception occurred: division by zero
        return False        


def executarConsultaCalendario(sql):
    con = sqlite3.connect(caminho_calendario)
    con.row_factory = sqlite3.Row        
    cur = con.cursor()

    cur.execute(sql)

    result = [dict(row) for row in cur.fetchall()]
    
    #for row in cur.fetchall():
        #print(row)

    con.close()

    return result


def executarConsultaOldMusic(sql):
    con = sqlite3.connect(caminho_old_musicas)
    con.row_factory = sqlite3.Row        
    cur = con.cursor()

    cur.execute(sql)

    result = [dict(row) for row in cur.fetchall()]
    
    #for row in cur.fetchall():
        #print(row)

    con.close()

    return result


def alterarEventoAtivo(valor, id):
    con = sqlite3.connect(caminho_calendario)
    cur = con.cursor()
    
    try:
        cur.execute('UPDATE calendario_semanal SET ativo = %s WHERE id = %s' % (valor, id))

        con.commit()
        con.close()
        return True
    
    except Exception as error:
        print("An exception occurred:", error) # An exception occurred: division by zero
        return False    

def inserirFestaDepCalendario(lista):
    con = sqlite3.connect(caminho_calendario)
    cur = con.cursor()

    semana_sqlite = [1, 2, 3, 4, 5, 6, 0]

    try:
        # inserir info básica sobre a data da festa na congregação
        sql = "INSERT INTO calendario_festa_dep (id_congregacao, inicio, fim) VALUES(%s, '%s', '%s') ON CONFLICT(id_congregacao) DO UPDATE SET inicio = '%s', fim = '%s'"  % (lista['id_cong'], lista['inicio'], lista['fim'], lista['inicio'], lista['fim'])
        cur.execute(sql)
        
        cur.execute('DELETE FROM eventos_festa_dep WHERE id_congregacao = %s' % lista['id_cong'])

        for evento in lista['lista_final']:
            cur.execute("INSERT INTO eventos_festa_dep VALUES(%s, %s, %s, '%s', %s)" % (lista['id_cong'], evento['dia'], semana_sqlite[int(evento['dia'])], evento['hora'], evento['evento']))

        con.commit()
        con.close()
        return True
    except Exception as error:
        con.close()
        print("An exception occurred:", error) # An exception occurred: division by zero
        return False

def inserirFestaDepSedeCalendario(lista):
    con = sqlite3.connect(caminho_calendario)
    cur = con.cursor()

    try:
        cur.execute('DELETE FROM calendario_festa_dep_sede')

        for evento in lista:
            cur.execute("INSERT INTO calendario_festa_dep_sede VALUES('%s', '%s', '%s', '%s', '%s')" % (evento['de'], evento['ate'], evento['desc_curta'].replace("&nbsp;", " "), evento['desc_longa'].replace("&nbsp;", " "), evento['plain_text']))

        con.commit()
        con.close()
        return True
    except Exception as error:
        con.close()
        print("An exception occurred:", error) # An exception occurred: division by zero
        return False          
