from MySQL import db


banco = db({'host':"localhost",    # your host, usually localhost
            'user':"root",         # your username
            'passwd':"Yasmin",  # your password
            'db':"sistema-slide"})



categoria = banco.executarConsulta('select * from categoria_departamentos')

for item in categoria:
    item['subcats'] = banco.executarConsulta('select descricao from subcategoria_departamentos where supercategoria = %s order by descricao' % item['id'])

print(categoria)