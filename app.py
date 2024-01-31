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
import re
import datetime

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
roteiro = []

musicas_dir = r'C:\Users' + '\\' + os.getenv("USERNAME") + r'\OneDrive - Secretaria da Educação do Estado de São Paulo\IGREJA\Músicas\Escuro' + '\\'

banco = db({'host':"localhost",    # your host, usually localhost
            'user':"root",         # your username
            'passwd':"Yasmin",  # your password
            'db':"sistema-slide"})

@app.route('/', methods=['GET', 'POST'])
def home():

    if estado > 0:
        titulo = banco.executarConsulta('select titulo from %s where id = %s' % (current_presentation['tipo'], current_presentation['id']))[0]['titulo']

        if (current_presentation['tipo'] == 'musicas'):
            tipo = 'Música'

        ls_capa = banco.executarConsulta('select filename from capas where id_musica = %s' % current_presentation['id'])
        
        if (len(ls_capa) > 0):
            capa = 'static/images/capas/' + ls_capa[0]['filename']
        else:
            capa = 'static/images/Background.jpeg'    
    else:
        titulo = None
        tipo = None
        capa = 'static/images/Background.jpeg'

    return render_template('home.jinja', roteiro=roteiro, estado=estado, titulo=titulo, tipo=tipo, capa=capa)

@app.route('/render_pdf', methods=['GET', 'POST'])
def render_pdf():
    lista_final = []
    cont = 1
    now = datetime.date.today()

    # convert to string
    hoje = now.strftime("%d/%m/%Y") 

    #ls = request.json
    ls = request.args.get('ls')
    
    if ls == '': # pegar geral
        lista_musicas = banco.executarConsulta('select * from musicas order by titulo')
        lista_categoria = []

        for item in banco.executarConsulta('select * from categoria_departamentos order by id'):
            aux = []
            for cats in banco.executarConsulta('select descricao from subcategoria_departamentos where supercategoria = %s order by id' % item['id']):
                aux.append(cats['descricao'])

            lista_categoria.append({'descricao':item['descricao'], 'cats':aux})
    else: # fazer o processo reverso pra pegar isso daqui
        lista = ls[:-1].split(',')
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

        lista_musicas = banco.executarConsulta('select ' + \
                                               'musicas.id, musicas.titulo ' + \
                                               'from musicas inner join vinculos_x_musicas ' + \
                                               'on vinculos_x_musicas.id_musica = musicas.id ' + \
                                               'where vinculos_x_musicas.id_vinculo IN (%s) ' % ls[:-1] + \
                                               'group by (titulo) order by titulo')
    
    for item in lista_musicas:
        letras = banco.executarConsulta('select replace(replace(replace(texto, "<mark ", "<span "), "</mark>", "</span>"), "cdx-underline", "cdx-underline-view") as texto from letras where id_musica = %s order by paragrafo' % item['id'])
        lista_final.append({'titulo':item['titulo'], 'letras':letras, 'cont':'{:02d}'.format(cont)})
        cont += 1

    #return jsonify({'lista_musicas':lista_final, 'lista_categorias':lista_categoria, 'completo':'true', 'total':len(lista_final)})
    return render_template('render_pdf.jinja', lista=lista_final, completo='true', lista_categoria=lista_categoria, total=len(lista_final), data=hoje)

@app.route('/controlador', methods=['GET', 'POST'])
def controlador():

    global estado
    global current_presentation
    global index

    if estado == 0:
        return redirect('/')
    else:

        if (current_presentation['tipo'] == 'musicas'):
            fundo = banco.executarConsulta('select filename from capas where id_musica = %s' % current_presentation['id'])

            if len(fundo) < 1:
                fundo = 'images/' + banco.executarConsulta("select valor from config where id = 'background'")[0]['valor']
            else:
                fundo = 'images/capas/' + fundo[0]['filename']

            lista_slides = banco.executarConsulta("select `text-slide`, categoria, ifnull(anotacao, '') as anotacao, pos from slides where id_musica = %s order by pos" % current_presentation['id'])

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
    global index

    if estado == 0:
        fundo = 'images/' + banco.executarConsulta("select valor from config where id = 'background'")[0]['valor']
        return render_template('PowerPoint.jinja', fundo=fundo, lista_slides=[], index=0)
    elif estado == 1: # se iniciou uma apresentação
        if (current_presentation['tipo'] == 'musicas'):
            fundo = banco.executarConsulta('select filename from capas where id_musica = %s' % current_presentation['id'])

            if len(fundo) < 1:
                fundo = 'images/' + banco.executarConsulta("select valor from config where id = 'background'")[0]['valor']
            else:
                fundo = 'images/capas/' + fundo[0]['filename']

            lista_slides = banco.executarConsulta('select `text-slide`, categoria from slides where id_musica = %s order by pos' % current_presentation['id'])

            return render_template('PowerPoint.jinja', fundo=fundo, lista_slides=lista_slides, index=index)


@app.route('/updateSlide', methods=['GET', 'POST'])
def updateSlide():
    if request.method == 'POST':
        #print('got a post request!')

        if request.is_json: # application/json
            # handle your ajax request here!

    
            global index

            index = int(request.json)

            socketio.emit('update', index)
            #legenda = DB.executarConsulta('Musicas.db', 'SELECT sub_linha_1 || CASE WHEN sub_linha_2 != "" THEN "<br>" ELSE "" END || sub_linha_2 as legenda from lista WHERE slide = %s' % index)[0]
            #socketio.emit('legenda', legenda)            
            return jsonify(True)

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
        
        capa = 'images/upload_image.jpg'

        if (info['destino'] == '0'):
            result = banco.inserirNovaMusica(info)
        else:
            result = banco.alterarMusica(info)
            ls_capa = banco.executarConsulta('select filename from capas where id_musica = %s' % result['id'])
            print(ls_capa)
            if (len(ls_capa) > 0):
                capa = 'images/capas/' + ls_capa[0]['filename']

        if result['id'] > 0:       
            titulo = banco.executarConsulta('select titulo from musicas where id = %s' % result['id'])[0]['titulo']
            letras = banco.executarConsulta('select texto from letras where id_musica = %s order by paragrafo' % result['id'])
            
            return render_template('result_musica.jinja', titulo=titulo, letras=letras, id=result['id'], log=result['log'], capa=capa)
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
    destino = '0'

    if request.method == "POST":

        destino = '0'

        if 'json_back' in request.form:
            info = json.loads(request.form.getlist('json_back')[0])
            titulo = info['listaGeral']['titulo']
            lista_texto = info['listaGeral']['slides']
            destino = info['destino']
        else:
            nome = request.form.getlist('file')[0]
            lista_texto = getListText(musicas_dir + nome)
            titulo = nome.replace('.pptx', '')

        # recriar lista pro editor
        for item in lista_texto:
            blocks.append({'type':'paragraph', 'data':{'text':item['text-slide']}})
            blocks_s.append({'type':'paragraph', 'data':{'text':item['subtitle']}})

    
    return render_template('editor_musica.jinja', lista_texto=lista_texto, blocks=blocks, blocks_s=blocks_s, titulo=titulo, destino=destino)
    



@app.route('/enviarDadosNovaMusica', methods=['GET', 'POST'])
def enviarDadosNovaMusica():
    if request.method == "POST":
        info = json.loads(request.form.getlist('json_data_send')[0])
        cat_slides = banco.executarConsulta('select * from categoria_slide')
        categoria = banco.executarConsulta('select * from subcategoria_departamentos')
        status = banco.executarConsulta('select * from status_vinculo')
        vinculos = []
        cat_slides_list = []

        blocks = []
        for item in info['slides']:
            blocks.append({'type':'paragraph', 'data':{'text':item['text-slide']}})

        destino = request.form.getlist('destino')[0]
        if destino != '0': # significa que é edição e não acréscimo
            vinculos = banco.executarConsulta('select * from vinculos_x_musicas where id_musica = %s' % destino)
            letras = banco.executarConsulta('select * from letras where id_musica = %s order by paragrafo' % destino)
            blocks = []

            for item in letras:
                blocks.append({'type':'paragraph', 'data':{'text':item['texto']}})

            cat_slides_list = banco.executarConsulta('select categoria from slides where id_musica = %s order by pos' % destino)

        return render_template('save_musica.jinja', info=info, cat_slides=cat_slides, blocks=blocks, categoria=categoria, status=status, vinculos=vinculos, cat_slides_list=cat_slides_list, destino=destino)

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
    global render_temp
    render_temp = request.json

    return jsonify(True)

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

            filename = banco.executarConsulta('select * from capas where id_musica = %s' % id['id'])
    
            if (len(filename) > 0):
                capa = '/static/images/capas/' + filename[0]['filename']
            else:
                capa = '/static/images/upload_image.jpg'

            return jsonify({'vinculos':vinculos, 'letras':letras, 'capa':capa})

@app.route('/verificarSenha', methods=['GET', 'POST'])
def verificarSenha():
    if request.method == "POST":
        senha = request.form.getlist('senha')[0]
        destino = request.form.getlist('destino')[0]
        
        if senha == '120393':
            if destino == '0':
                return render_template('editor_musica.jinja', lista_texto=[], blocks=[], blocks_s=[], titulo='', destino='0')
            else: # ele vai editar e não salvar um novo
                blocks = []
                blocks_s = []
                titulo = banco.executarConsulta('select titulo from musicas where id = %s' % destino)[0]['titulo']
                lista_texto = banco.executarConsulta("select pos, `text-slide`, `text-legenda` as subtitle, ifnull(anotacao, '') as anotacao from slides where id_musica = %s order by pos" % destino)
                
                # recriar lista pro editor
                for item in lista_texto:
                    blocks.append({'type':'paragraph', 'data':{'text':item['text-slide']}})
                    blocks_s.append({'type':'paragraph', 'data':{'text':item['subtitle']}})

                return render_template('editor_musica.jinja', lista_texto=lista_texto, blocks=blocks, blocks_s=blocks_s, titulo=titulo, destino=destino)
            
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

@app.route('/pesquisarLetra', methods=['GET', 'POST'])
def pesquisarLetra():

    if request.method == 'POST':
        if 'pesquisa' in request.form:
            pesquisa = request.form['pesquisa'].replace("'", '’')
            pesquisa_original = pesquisa
            status = ''

            if pesquisa != '':
                if len(pesquisa) > 2:
                    lista_palavras = pesquisa.split(' ')
                    pesquisa = r'%' + pesquisa.replace(' ', r'%') + r'%'


                    resultado_pesquisa = banco.executarConsulta("select letras.id_musica, musicas.titulo, replace(texto, '<br>', ' ') as texto from letras inner join musicas on musicas.id = letras.id_musica where letras.texto like '%s' or musicas.titulo like '%s' group by id_musica order by titulo" % (pesquisa, pesquisa))

                    for item in resultado_pesquisa:

                        texto = converHTML_to_List(item['texto'])
                        texto_final = ''

                        for element in texto:
                            if len(element['text']) > 0:
                                aux = element['text'][0]
                                #print(aux)
                                for palavra in lista_palavras:
                                    if len(palavra) > 2:
                                        compiled = re.compile(re.escape(palavra), re.IGNORECASE)
                                        res = compiled.sub('<span class="highlight">' + palavra + "</span>", aux)
                                        aux = str(res)

                                if element['css'] == 'mark':
                                    texto_final += '<span class="cdx-marker">' + aux + '</span>&nbsp;'
                                elif element['css'] == 'b':
                                    texto_final += '<b>' + aux + '</b>&nbsp;'
                                elif element['css'] == 'u':
                                    texto_final += '<u class="cdx-underline">' + aux + '</u>&nbsp;'
                                elif element['css'] == 'u-b':
                                    texto_final += '<u class="cdx-underline"><b>' + aux + '</b></u>&nbsp;'
                                else:
                                    texto_final += aux + '&nbsp;'



                        item['texto'] = texto_final

                    if len(resultado_pesquisa) > 0:
                        return render_template('resultado_pesquisa.jinja', resultado_pesquisa=resultado_pesquisa, lista_palavras=lista_palavras, pesquisa=pesquisa_original)
                    else:
                        status= '<div class="alert alert-warning alert-dismissible fade show" role="alert"><strong>Atenção!</strong> Sem resultados encontrados, por favor revise os termos pesquisados.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
                else:
                    status= '<div class="alert alert-warning alert-dismissible fade show" role="alert"><strong>Atenção!</strong> Por favor utilize uma palavra de três letras ou mais.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
            else:
                status= '<div class="alert alert-warning alert-dismissible fade show" role="alert"><strong>Atenção!</strong> Por favor digite algumas palavras na pesquisa.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
            
            musicas = banco.executarConsulta('select id, titulo, (select group_concat(id_vinculo) from vinculos_x_musicas where id_musica = id) as vinc from musicas order by titulo')
            categoria = banco.executarConsulta('select * from categoria_departamentos')
            
            for item in categoria:
                item['subcategoria'] = banco.executarConsulta('select id, descricao from subcategoria_departamentos where supercategoria = %s' % item['id'])

            return render_template('musicas.jinja', musicas=musicas, status=status, categoria=categoria)


@app.route('/iniciar_apresentacao', methods=['GET', 'POST'])
def iniciar_apresentacao():

    global current_presentation
    global estado
    global index
    global roteiro

    if request.method == 'POST':
        if request.is_json:
            info = request.json
            current_presentation = {'id':info['id'], 'tipo':info['tipo']}
            estado = 1
            index = 0

            socketio.emit('refresh', 1)
            socketio.emit('update_roteiro', 1)

            return jsonify(True)
        
        elif 'proximaPRS' in request.form: # pediu para iniciar nova apresentação na lista do roteiro 
            for item in roteiro:
                if (not item['check']):
                    item['check'] = True
                    current_presentation = {'id':item['id'], 'tipo':item['tipo']}
                    estado = 1
                    index = 0

                    socketio.emit('refresh', 1)
                    break

            return redirect('/')

@app.route('/proxima_prs', methods=['GET', 'POST'])
def proxima_prs():

    global current_presentation
    global estado
    global roteiro
    global index

    if request.method == 'POST':
        if request.is_json:
            msg = request.json
            if msg == 1:
                if len(roteiro) > 0:
                    for item in roteiro:
                        if not item['check']:
                            item['check'] = True
                            estado = 1
                            current_presentation = {'id':item['id'], 'tipo':item['tipo']}
                            index = 0

                            socketio.emit('refresh', 1)
                            return jsonify(True)

    estado = 0
    current_presentation = {'id':0, 'tipo':''}
    index = 0

    socketio.emit('refresh', 1)
    return jsonify(True)


@app.route('/encerrar_apresentacao', methods=['GET', 'POST'])
def encerrar_apresentacao():

    global current_presentation
    global estado
    global index


    if request.method == 'POST':
        if request.is_json:
            if int(request.json) == 1:
                estado = 0
                current_presentation = {'id':0, 'tipo':''}
                index = 0

                socketio.emit('refresh', 1)          
                socketio.emit('update_roteiro', 1)  


                return jsonify(True)
            else:
                return jsonify(False)


@app.route('/adicionar_roteiro', methods=['GET', 'POST'])
def adicionar_roteiro():   

    global roteiro

    if request.method == 'POST':
        if request.is_json:
            info = request.json
            roteiro.append(info)
            #print(roteiro)

            socketio.emit('update_roteiro', 1)
            return jsonify(True) 


@app.route('/update_roteiro', methods=['GET', 'POST'])
def update_roteiro():
    if request.method == 'POST':
        if request.is_json:

            global roteiro

            info = request.json
            roteiro = info

            socketio.emit('update_roteiro', 1)
            return jsonify(len(roteiro))


if __name__ == '__main__':
    app.run('0.0.0.0',port=120)
    #serve(app, host='0.0.0.0', port=80, threads=8)
    #eventlet.wsgi.server(eventlet.listen(('', 80)), app)
    #socketio.run(app, port=80,host='0.0.0.0', debug=True) 
    #monkey.patch_all()
    #http_server = WSGIServer(('0.0.0.0', 80), app)
    #http_server.serve_forever()