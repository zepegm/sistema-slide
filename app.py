from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, Response
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from threading import Lock
from waitress import serve
from PowerPoint import getListText
from MySQL import db
import json
import os
import DB

app=Flask(__name__)
app.secret_key = "abc123"
app.config['SECRET_KEY'] = 'justasecretkeythatishouldputhere'
#socketio = SocketIO(app, async_mode='threading')
socketio = SocketIO(app)
CORS(app)
thread = None
thread_lock = Lock()

index = 1
total_slides = DB.executarConsulta('Musicas.db', 'select max(slide) from lista')[0]
musicas_dir = r'C:\Users' + '\\' + os.getenv("USERNAME") + r'\OneDrive - Secretaria da Educação do Estado de São Paulo\IGREJA\Músicas\Escuro' + '\\'

banco = db({'host':"localhost",    # your host, usually localhost
            'user':"root",         # your username
            'passwd':"Yasmin",  # your password
            'db':"sistema-slide"})

@app.route('/', methods=['GET', 'POST'])
def home():
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

    lista_final.append({'musica':temp[0]['title'], 'slides':temp})

    dir = os.getcwd() + r'\static\videos'

    lista_videos = [arq for arq in os.listdir(dir)]

    ls_final_videos = []
    cont = 1
    for item in lista_videos:
        ls_final_videos.append({'file':item, 'nome':'Fundo ' + str(cont)})
        cont += 1    

    return render_template('index.jinja', total_slides=total_slides, index=index, listaSlideShow=lista_final, videos=ls_final_videos)

@app.route('/slide', methods=['GET', 'POST'])
def slide():

    global index
    return render_template('PowerPoint.jinja', index=index)


@app.route('/proximoSlide', methods=['GET', 'POST'])
def proximoSlide():
    if request.method == 'POST':
        #print('got a post request!')

        if request.is_json: # application/json
            # handle your ajax request here!

    
            global index
            global total_slides

            if index < total_slides:
                index += 1

            socketio.emit('update', index)
            legenda = DB.executarConsulta('Musicas.db', 'SELECT sub_linha_1 || CASE WHEN sub_linha_2 != "" THEN "<br>" ELSE "" END || sub_linha_2 as legenda from lista WHERE slide = %s' % index)[0]
            socketio.emit('legenda', legenda)            
            return jsonify(index)


@app.route('/anteriorSlide', methods=['GET', 'POST'])
def anteriorSlide():
    if request.method == 'POST':
        #print('got a post request!')

        if request.is_json: # application/json
            # handle your ajax request here!

    
            global index
            global total_slides

            if index > 1:
                index -= 1

            socketio.emit('update', index)
            legenda = DB.executarConsulta('Musicas.db', 'SELECT sub_linha_1 || CASE WHEN sub_linha_2 != "" THEN "<br>" ELSE "" END || sub_linha_2 as legenda from lista WHERE slide = %s' % index)[0]
            socketio.emit('legenda', legenda)            
            return jsonify(index)

@app.route('/goto', methods=['GET', 'POST'])
def goto():
    if request.method == 'POST':
        #print('got a post request!')

        if request.is_json: # application/json
            # handle your ajax request here!
            new_index = request.json
            global index
            index = new_index  

            socketio.emit('update', index)
            legenda = DB.executarConsulta('Musicas.db', 'SELECT sub_linha_1 || CASE WHEN sub_linha_2 != "" THEN "<br>" ELSE "" END || sub_linha_2 as legenda from lista WHERE slide = %s' % index)[0]
            socketio.emit('legenda', legenda)
            return jsonify(index)              


@app.route('/changeBackground', methods=['GET', 'POST'])
def changeBackground():
    if request.method == 'POST':
        #print('got a post request!')

        if request.is_json: # application/json
            # handle your ajax request here!
            file = request.json
            completo = '/static/videos/' + file

            socketio.emit('change', completo)
            return jsonify(True)



@app.route('/subtitle')
def exibirLegenda():
    legenda = DB.executarConsulta('Musicas.db', 'SELECT sub_linha_1 || CASE WHEN sub_linha_2 != "" THEN "<br>" ELSE "" END || sub_linha_2 as legenda from lista WHERE slide = %s' % index)[0]

    if legenda != '':
    
        if len(legenda) > 199:
            tamanho = 30
        else:
            tamanho = 20
    else:
        tamanho = 0

    return render_template('subtitle.jinja', legenda=legenda, tamanho=tamanho)

@app.route('/edit_musica', methods=['GET', 'POST'])
def edit_musica():

    lista_texto = []
    blocks = []
    blocks_s = []
    titulo = ''

    if request.method == "POST":
        nome = request.form.getlist('file')[0]
        lista_texto = getListText(musicas_dir + nome)
        titulo = nome.replace('.pptx', '')

        # recriar lista pro editor
        for item in lista_texto:
            blocks.append({'type':'paragraph', 'data':{'text':item['text-slide']}})
            blocks_s.append({'type':'paragraph', 'data':{'text':item['subtitle']}})

    return render_template('editor_musica.jinja', lista_texto=lista_texto, blocks=blocks, blocks_s=blocks_s, titulo=titulo)


@app.route('/enviarDadosNovaMusica', methods=['GET', 'POST'])
def enviarDadosNovaMusica():
    if request.method == "POST":
        info = json.loads(request.form.getlist('json_data_send')[0])
        cat_slides = banco.executarConsulta('select * from categoria_slide')

        blocks = []
        for item in info['slides']:
            blocks.append({'type':'paragraph', 'data':{'text':item['text-slide']}})

        return render_template('save_musica.jinja', info=info, cat_slides=cat_slides, blocks=blocks)


@app.route('/teste_2')
def teste_2():
    return render_template('teste.html')



if __name__ == '__main__':
    app.run('0.0.0.0',port=80)
    #serve(app, host='0.0.0.0', port=80, threads=8)
    #eventlet.wsgi.server(eventlet.listen(('', 80)), app)
    #socketio.run(app, port=80,host='0.0.0.0', debug=True) 
    #monkey.patch_all()
    #http_server = WSGIServer(('0.0.0.0', 80), app)
    #http_server.serve_forever()