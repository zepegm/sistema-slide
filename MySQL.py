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
                sql = "INSERT INTO letras VALUES(%s, %s, '%s')" % (id, letra['paragrafo'], letra['texto'])
                cur.execute(sql)

            database.commit()
            database.close()
            return {'id':id, 'log':'Operação realizada com sucesso!'}
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

            print(sql)

            cur.execute(sql)
            database.commit()
            database.close()

            return True

        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            return False                    