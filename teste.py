from MySQL import db


banco = db({'host':"localhost",    # your host, usually localhost
            'user':"root",         # your username
            'passwd':"Yasmin",  # your password
            'db':"sistema-slide"})



lista = '1,2,3,4,5,6,7,14,15,'[:-1].split(',')
lista_categoria = []

supercategoria = 0
aux = []


for item in lista:
    cat = banco.executarConsulta('select * from subcategoria_departamentos where id = %s' % item)[0]

    if cat['supercategoria'] != supercategoria:
        
        if len(aux) > 0:
            descricao = banco.executarConsulta('select descricao from categoria_departamentos where id = %s' % supercategoria)[0]['descricao']
            lista_categoria.append({'descricao':descricao, 'cats':aux})
            aux = []

        supercategoria = cat['supercategoria']

    aux.append(cat['descricao'])

descricao = banco.executarConsulta('select descricao from categoria_departamentos where id = %s' % supercategoria)[0]['descricao']
lista_categoria.append({'descricao':descricao, 'cats':aux})

print(lista_categoria)
        
