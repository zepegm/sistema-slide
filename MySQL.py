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
    
    def inserirNovaTurma(self, turma):   
        
        sql = "INSERT INTO turma VALUES(" + str(turma.values()).replace("'", '').replace('"', "'")[13:-2] + ")"

        try:
            database = mysql.connector.connect(host=self.cred['host'], user=self.cred['user'], passwd=self.cred['passwd'], db=self.cred['db'])
        
            cur = database.cursor()
            cur.execute(sql)
            database.commit()

            database.close()
            return True
        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            return False  
        

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

                if item != 'codigo_disciplina':
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