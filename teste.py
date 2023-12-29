import DB

listaSlideShow = DB.executarConsultaGeral('Musicas.db', 'select slide as `index`, id_musica, sub_linha_1 from lista')

lista_final = []
temp = []

id_musica = listaSlideShow[0]['id_musica']

for item in listaSlideShow:
    if id_musica != item['id_musica'] and len(temp) > 0:
        lista_final.append({'musica':temp[0]['title'], 'slides':temp})
        temp = []
        id_musica = item['id_musica']
        
    temp.append({'index':item['index'], 'title':item['sub_linha_1']})
    

for item in lista_final:
    print(item)