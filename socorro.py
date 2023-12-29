from os import listdir
from os import rename

def listar_arquivos(caminho=None):
    lista_arqs = [arq for arq in listdir(caminho)]
    return lista_arqs

lista = listar_arquivos(r'C:\Users\Giuseppe\Desktop\Projetos Python\sistema_slide\slides\Oficina')

key = 112

for item in lista:
    rename(r'C:\Users\Giuseppe\Desktop\Projetos Python\sistema_slide\slides\Oficina' + '\\' + item, r'C:\Users\Giuseppe\Desktop\Projetos Python\sistema_slide\slides\Oficina' + '\\' + str(key) + '.png')
    key += 1