from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, Response
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from threading import Lock
from waitress import serve
from PowerPoint import getListText
from MySQL import db
from HTML_U import converHTML_to_List
import json
import os
import DB
import os.path

app=Flask(__name__)
app.secret_key = "abc123"
app.config['SECRET_KEY'] = 'justasecretkeythatishouldputhere'
#socketio = SocketIO(app, async_mode='threading')
socketio = SocketIO(app)
CORS(app)
thread = None
thread_lock = Lock()

estado = 0
current_presentation = {'id':0, 'tipo':''}
index = 0

musicas_dir = r'C:\Users' + '\\' + os.getenv("USERNAME") + r'\OneDrive - Secretaria da Educação do Estado de São Paulo\IGREJA\Músicas\Escuro' + '\\'

banco = db({'host':"localhost",    # your host, usually localhost
            'user':"root",         # your username
            'passwd':"Yasmin",  # your password
            'db':"sistema-slide"})

@app.route('/', methods=['GET', 'POST'])
def home():
    return 'Hello World!'

@app.route('/controlador', methods=['GET', 'POST'])
def controlador():

    global estado
    global current_presentation
    global index

    if estado == 0:
        return redirect('/')
    else:

        if (current_presentation['tipo'] == 'musica'):
            fundo = banco.executarConsulta('select filename from capas where id_musica = %s' % current_presentation['id'])

            if len(fundo) < 1:
                fundo = 'images/' + banco.executarConsulta("select valor from config where id = 'background'")[0]['valor']
            else:
                fundo = 'images/capas/' + fundo[0]['filename']

            lista_slides = banco.executarConsulta('select `text-slide`, categoria, anotacao from slides where id_musica = %s order by pos' % current_presentation['id'])

            return render_template('controlador.jinja', lista_slides=lista_slides, index=index, fundo=fundo)

@app.route('/abrir_musica', methods=['GET', 'POST'])
def abrir_musica():

    musicas = banco.executarConsulta('select id, titulo, (select group_concat(id_vinculo) from vinculos_x_musicas where id_musica = id) as vinc from musicas order by titulo')
    categoria = banco.executarConsulta('select * from categoria_departamentos')
    for item in categoria:
        item['subcategoria'] = banco.executarConsulta('select id, descricao from subcategoria_departamentos where supercategoria = %s' % item['id'])

    return render_template('musicas.jinja', musicas=musicas, status='', categoria=categoria)

@app.route('/slide', methods=['GET', 'POST'])
def slide():

    global estado
    global current_presentation

    if estado == 0:
        fundo = 'images/' + banco.executarConsulta("select valor from config where id = 'background'")[0]['valor']
        return render_template('PowerPoint.jinja', fundo=fundo, lista_slides=[])
    elif estado == 1: # se iniciou uma apresentação
        if (current_presentation['tipo'] == 'musica'):
            fundo = banco.executarConsulta('select filename from capas where id_musica = %s' % current_presentation['id'])

            if len(fundo) < 1:
                fundo = 'images/' + banco.executarConsulta("select valor from config where id = 'background'")[0]['valor']
            else:
                fundo = 'images/capas/' + fundo[0]['filename']

            lista_slides = banco.executarConsulta('select `text-slide`, categoria from slides where id_musica = %s order by pos' % current_presentation['id'])

            return render_template('PowerPoint.jinja', fundo=fundo, lista_slides=lista_slides)


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
        
@app.route('/addMusica', methods=['GET', 'POST'])
def addMusica():
    if request.method == 'POST':    
        info = json.loads(request.form.getlist('json_send')[0])
        result = banco.inserirNovaMusica(info)

        if result['id'] > 0:       
            titulo = banco.executarConsulta('select titulo from musicas where id = %s' % result['id'])[0]['titulo']
            letras = banco.executarConsulta('select texto from letras where id_musica = %s order by paragrafo' % result['id'])
            
            return render_template('result_musica.jinja', titulo=titulo, letras=letras, id=result['id'])
        else :
            return render_template('erro.jinja', log=result['log'])
    else:
        return redirect("/", code=302)



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

        if 'json_back' in request.form:
            info = json.loads(request.form.getlist('json_back')[0])
            titulo = info['titulo']
            lista_texto = info['slides']
        else:
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
        categoria = banco.executarConsulta('select * from subcategoria_departamentos')
        status = banco.executarConsulta('select * from status_vinculo')

        blocks = []
        for item in info['slides']:
            blocks.append({'type':'paragraph', 'data':{'text':item['text-slide']}})

        return render_template('save_musica.jinja', info=info, cat_slides=cat_slides, blocks=blocks, categoria=categoria, status=status)

@app.route('/upload_capa',  methods=['GET', 'POST'])
def upload_capa():
    isthisFile = request.files.get('file')
    id = request.form.getlist('id')[0]
    filename = str(id) + os.path.splitext(isthisFile.filename)[1]

    isthisFile.save('./static/images/capas/' + filename)

    banco.insertOrUpdate({'id_musica':id, 'filename':"'" + filename + "'"}, 'capas')

    return jsonify('./static/images/capas/' + filename)

@app.route('/converto_to_pdf_list', methods=['GET', 'POST'])
def converto_to_pdf_list():
    texto = request.json
    print(texto)
    lista = []
    
    texto_formatado = []

    for txt in texto['texto_bruto']:
        texto_formatado.append(converHTML_to_List(txt['texto']))

    lista.append({'titulo':texto['titulo'], 'letras':texto_formatado})

    return jsonify(lista)

@app.route('/get_info_musica', methods=['GET', 'POST'])
def get_info_musica():

    if request.method == "POST":
        if request.is_json:

            id = request.json

            sql = 'select ' + \
                    "concat(categoria_departamentos.descricao, ' - ', subcategoria_departamentos.descricao) as vinculo, " + \
                    "status_vinculo.descricao as desc_status, " + \
                    "vinculos_x_musicas.descricao " + \
                "from vinculos_x_musicas " + \
                "inner join subcategoria_departamentos ON subcategoria_departamentos.id = vinculos_x_musicas.id_vinculo " + \
                "inner join  status_vinculo on status_vinculo.id = vinculos_x_musicas.id_status " + \
                "inner join categoria_departamentos ON categoria_departamentos.id = subcategoria_departamentos.supercategoria " + \
                "where id_musica = %s " % id['id'] + \
                "order by vinculos_x_musicas.id_status "                
            
            vinculos = banco.executarConsulta(sql)
            letras = banco.executarConsulta('select texto from letras where id_musica = %s order by paragrafo' % id['id'])
            capa = '/static/images/capas/' + banco.executarConsulta('select * from capas where id_musica = %s' % id['id'])[0]['filename']

            return jsonify({'vinculos':vinculos, 'letras':letras, 'capa':capa})

@app.route('/verificarSenha', methods=['GET', 'POST'])
def verificarSenha():
    if request.method == "POST":
        senha = request.form.getlist('senha')[0]
        destino = request.form.getlist('destino')[0]
        
        if senha == '120393':
            if destino == '1':
                return render_template('editor_musica.jinja', lista_texto=[], blocks=[], blocks_s=[], titulo='')
            
        else:
            if destino == '1' or destino == '2':
                musicas = banco.executarConsulta('select id, titulo, (select group_concat(id_vinculo) from vinculos_x_musicas where id_musica = id) as vinc from musicas order by titulo')
                status= '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Senha incorreta!</strong> Por favor digite a senha correta para abrir a área de Cadastro e Alteração.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'

                categoria = banco.executarConsulta('select * from categoria_departamentos')
                for item in categoria:
                    item['subcategoria'] = banco.executarConsulta('select id, descricao from subcategoria_departamentos where supercategoria = %s' % item['id'])

                return render_template('musicas.jinja', musicas=musicas, status=status, categoria=categoria)

    return render_template('erro.jinja', log='Erro fatal ao tentar redirecionar para área de Administrador.')


@app.route('/getTexto_PDF', methods=['GET', 'POST'])
def getTexto_PDF():
    lista = []
    musicas = request.json
    
    for musica in musicas:
        letras = banco.executarConsulta('select texto from letras where id_musica = %s order by paragrafo' % musica['id'])
        texto_formatado = []
        for l in letras:
            texto_formatado.append(converHTML_to_List(l['texto']))
        
        lista.append({'titulo':musica['titulo'], 'letras':texto_formatado})

    return jsonify(lista)

@app.route('/iniciar_apresentacao', methods=['GET', 'POST'])
def iniciar_apresentacao():

    global current_presentation
    global estado
    global index

    if request.method == 'POST':
        if request.is_json:
            info = request.json
            current_presentation = {'id':info['id'], 'tipo':info['tipo']}
            estado = 1
            index = 0


    return jsonify(True)



if __name__ == '__main__':
    app.run('0.0.0.0',port=120)
    #serve(app, host='0.0.0.0', port=80, threads=8)
    #eventlet.wsgi.server(eventlet.listen(('', 80)), app)
    #socketio.run(app, port=80,host='0.0.0.0', debug=True) 
    #monkey.patch_all()
    #http_server = WSGIServer(('0.0.0.0', 80), app)
    #http_server.serve_forever()