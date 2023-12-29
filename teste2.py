import os

dir = os.getcwd() + r'\static\videos'

lista_videos = [arq for arq in os.listdir(dir)]

ls_final_videos = []
cont = 1
for item in lista_videos:
    ls_final_videos.append({'file':item, 'nome':'Fundo ' + str(cont)})
    cont += 1

print(ls_final_videos)