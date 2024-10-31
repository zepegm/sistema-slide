import os

# Função para verificar se um arquivo existe
def verificar_arquivo_existe(caminho_arquivo):
    return os.path.isfile(caminho_arquivo)


file = 'static/images/capas/1.jpg'

print(verificar_arquivo_existe(file))