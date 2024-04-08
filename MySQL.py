import mysql.connector

class db:
    def __init__(self, credenciais):
        self.cred = credenciais

    def executarConsultaVetor(self, sql):
        database = mysql.connector.connect(host=self.cred['host'],
                                   user=self.cred['user'],
                                   passwd=self.cred['passwd'],
                                   db=self.cred['db'])
        
        cur = database.cursor()

        cur.execute(sql)

        result = [item[0] for item in cur.fetchall()]

        database.close()

        return result        

    def executarConsulta(self, sql):
        database = mysql.connector.connect(host=self.cred['host'],
                                   user=self.cred['user'],
                                   passwd=self.cred['passwd'],
                                   db=self.cred['db'])
        
        cur = database.cursor(dictionary=True)

        cur.execute(sql)

        result = [dict(row) for row in cur.fetchall()]
        
        #for row in cur.fetchall():
            #print(row)

        database.close()

        return result
    
    def inserirNovoHino(self, harpa):
        try:
            database = mysql.connector.connect(host=self.cred['host'], user=self.cred['user'], passwd=self.cred['passwd'], db=self.cred['db'])
            cur = database.cursor()      

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

            database.commit()
            database.close()
            return True                

        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            return False


    def inserirNovaMusica(self, musica):   

        try:
            database = mysql.connector.connect(host=self.cred['host'], user=self.cred['user'], passwd=self.cred['passwd'], db=self.cred['db'])
            cur = database.cursor()
            
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

            database.commit()
            database.close()
            return {'id':id, 'log':'Operação realizada com sucesso!'}
        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            return {'id':0, 'log':'Erro ao tentar acessar banco de dados.<br><span class="fw-bold">Descrição: </span>' + str(error)}
        

    def alterarMusica(self, musica):
        try:
            database = mysql.connector.connect(host=self.cred['host'], user=self.cred['user'], passwd=self.cred['passwd'], db=self.cred['db'])
            cur = database.cursor()
            
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

            database.commit()
            database.close()
            return {'id':int(musica['destino']), 'log':'Alteração realizada com sucesso!'}
        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            return {'id':0, 'log':'Erro ao tentar acessar banco de dados.<br><span class="fw-bold">Descrição: </span>' + str(error)}        

    def insertOrUpdate(self, dados, tabela):
            
        try:
            database = mysql.connector.connect(host=self.cred['host'], user=self.cred['user'], passwd=self.cred['passwd'], db=self.cred['db'])
            cur = database.cursor()

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
            database.commit()
            database.close()

            return True

        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            return False          


    def insertOrUpdateList(self, lista, tabela):
            
        try:
            database = mysql.connector.connect(host=self.cred['host'], user=self.cred['user'], passwd=self.cred['passwd'], db=self.cred['db'])
            cur = database.cursor()

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
            
            database.commit()
            database.close()

            return True

        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            return False                   