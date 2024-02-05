from MySQL import db
import random

banco = db({'host':"localhost",    # your host, usually localhost
            'user':"root",         # your username
            'passwd':"",  # your password
            'db':"sistema-slide"})


texto = banco.executarConsulta("select * from slides where `text-slide` like '" + '%<mark class="cdx-marker">%' + "' and categoria = 1")

result = texto[random.randint(0, len(texto))]

print(result['text-slide'])