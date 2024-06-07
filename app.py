from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, Response
from flask_socketio import SocketIO, emit
from flask_cors import CORS
#from threading import Lock
from waitress import serve
from PowerPoint import getListText, getListTextHarpa
from read_csv import readCSVHarpa
#from MySQL import db
from SQLite_DB import db
from SQLite_DB import insert_log, get_all_hook, get_photos, inserir_calendario_semanal, executarConsultaCalendario
from HTML_U import converHTML_to_List
import locale
import math
import json
import os
import os.path
import re
import datetime
import random
from pyppeteer import launch
from pptx_file import ppt_to_png
from utils_crip import encriptar

app=Flask(__name__)
app.secret_key = "abc123"
app.config['SECRET_KEY'] = 'justasecretkeythatishouldputhere'
#app.config['UPLOAD_FOLDER'] = r'C:\Users\Operador\OneDrive - Secretaria da Educação do Estado de São Paulo\IGREJA\Backup\sistema-slide\static\uploads'
socketio = SocketIO(app, async_mode='threading')
#socketio = SocketIO(app)
CORS(app)

estado = 0
current_presentation = {'id':0, 'tipo':''}
index = 0
roteiro = []
temp_pdf = None

musicas_dir = r'C:\Users' + '\\' + os.getenv("USERNAME") + r'\OneDrive - Secretaria da Educação do Estado de São Paulo\IGREJA\Músicas\Escuro' + '\\'
harpa_dir = r'C:\Users' + '\\' + os.getenv("USERNAME") + r'\OneDrive - Secretaria da Educação do Estado de São Paulo\IGREJA\HARPA' + '\\'
locale.setlocale(locale.LC_ALL, "")
banco = db()

@app.route('/', methods=['GET', 'POST'])
def home():

    number = None
    nome_autor = None

    if estado == 1:
        titulo = banco.executarConsulta('select titulo from %s where id = %s' % (current_presentation['tipo'], current_presentation['id']))[0]['titulo']

        tipo = 'Música'

        ls_capa = banco.executarConsulta('select filename from capas where id_musica = %s' % current_presentation['id'])
        
        if (len(ls_capa) > 0):
            capa = 'static/images/capas/' + ls_capa[0]['filename']
        else:
            capa = 'static/images/Background.jpeg'    
    
    elif estado == 2:
        titulo = banco.executarConsultaVetor('select descricao from livro_biblia where id = %s' % current_presentation['id'])[0] + ' ' + current_presentation['cap'] + ':' + str(index + 1)
        tipo = 'Bíblia'
        capa = 'static/images/Biblia.jpg'
    elif estado == 3:
        titulo = banco.executarConsultaVetor('select descricao from harpa where id = %s' % current_presentation['id'])[0]
        number = 'HINO %s' % '{0:03}'.format(int(current_presentation['id']))
        nome_autor = banco.executarConsultaVetor('select nome from autor_harpa where id = (select autor from harpa where id = %s)' % current_presentation['id'])[0]
        tipo = 'Harpa'
        capa = 'static/images/Harpa.jpg'
    elif estado == 4:
        id_harpa = banco.executarConsultaVetor('select id_harpa from harpa_versionada where id = %s' % current_presentation['id'])[0]
        titulo = banco.executarConsultaVetor('select descricao from harpa where id = %s' % id_harpa)[0]
        number = 'HINO %s' % '{0:03}'.format(int(id_harpa))
        nome_autor = banco.executarConsultaVetor('select nome from autor_harpa where id = (select autor from harpa where id = %s)' % id_harpa)[0]
        tipo = 'Harpa'
        capa = 'static/images/Harpa.jpg'
    elif estado == 5: # apresentação PowerPoint
        titulo = current_presentation['titulo']
        tipo = 'Apresentação PowerPoint'
        capa = 'static/images/SlidesPPTX/0.png'
    else:
        titulo = None
        tipo = None
        capa = 'static/images/Background.jpeg'

    return render_template('home.jinja', roteiro=roteiro, estado=estado, titulo=titulo, tipo=tipo, capa=capa, number=number, autor=nome_autor, status='')

@app.route('/render_pdf', methods=['GET', 'POST'])
def render_pdf():
    lista_final = []
    cont = 1
    now = datetime.date.today()

    # convert to string
    hoje = now.strftime("%d/%m/%Y") 

    #ls = request.json
    ls = request.args.get('ls')
    
    if (ls == 'render_preview'):
        global temp_pdf
        return render_template('render_pdf.jinja', lista=temp_pdf, completo='false', lista_categoria=[], total=0, data='')


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
    
    #montar o sumário
    if (len(lista_musicas) > 30):
        page = math.ceil((len(lista_musicas) - 32) / 35) + 4
    else:
        page = 4

    for item in lista_musicas:
        letras = banco.executarConsulta('select replace(replace(replace(texto, "<mark ", "<span "), "</mark>", "</span>"), "cdx-underline", "cdx-underline-view") as texto from letras where id_musica = %s and pagina = 1 order by paragrafo' % item['id'])
        letras_2 = banco.executarConsulta('select replace(replace(replace(texto, "<mark ", "<span "), "</mark>", "</span>"), "cdx-underline", "cdx-underline-view") as texto from letras where id_musica = %s and pagina = 2 order by paragrafo' % item['id'])
        lista_final.append({'titulo':item['titulo'], 'letras':letras, 'letras_2':letras_2, 'cont':'{:02d}'.format(cont), 'pag':page})
        
        if (len(letras_2) > 0):
            page += 1
        
        cont += 1
        page += 1

    return render_template('render_pdf.jinja', lista=lista_final, completo='true', lista_categoria=lista_categoria, total=len(lista_final), data=hoje)


@app.route('/render_pdf_harpa', methods=['GET', 'POST'])
def render_pdf_harpa():
    tipo = int(request.args.get('tipo'))

    now = datetime.date.today()

    # convert to string
    hoje = now.strftime("%d/%m/%Y") 

    lista_final = []

    if tipo == 3: # apenas as versões alternativas
        lista_harpa = banco.executarConsulta('select harpa_versionada.id as id_versao, harpa.id, harpa.descricao, harpa_versionada.titulo_versao from harpa_versionada inner join harpa on harpa.id = harpa_versionada.id_harpa order by harpa.id')
    else: # todas as versões
        lista_harpa = banco.executarConsulta('select id, descricao from harpa')

    match tipo:
        case 1: # geral
            total = banco.executarConsultaVetor('select (select count(*) from harpa) + (select count(*) from harpa_versionada) as total')[0]
        case 2: # apenas o formato clássico dos hinos
            total = banco.executarConsultaVetor('select count(*) from harpa as total')[0]
        case 3: # apenas as versões alternativas 
            total = banco.executarConsultaVetor('select count(*) from harpa_versionada as total')[0]

    #montar o sumário
    if (total > 30):
        page = math.ceil((total - 32) / 35) + 4
    else:
        page = 4

    if (tipo == 3): # no caso de ser apenas versões alternativas
        for item in lista_harpa:

            pagina_1 = banco.executarConsultaVetor('select texto from letras_harpa_versionada where id_harpa_versionada = %s and pagina = 1 order by paragrafo' % item['id_versao'])
            pagina_2 = banco.executarConsultaVetor('select texto from letras_harpa_versionada where id_harpa_versionada = %s and pagina = 2 order by paragrafo' % item['id_versao'])


            lista_final.append({'numero':'%03d' % item['id'], 'titulo':item['descricao'], 'letras':pagina_1, 'letras_2':pagina_2, 'versao':item['titulo_versao'], 'pag':page})

            if (len(pagina_2) > 0):
                page += 1

            page += 1

        return render_template('render_pdf_harpa.jinja', lista=lista_final, total=total, data=hoje, tipo=tipo) # encerra a função e retorna a harpa versionada

    # a partir daqui será executado no caso de tipo 1 ou 2 (completa ou clássica)
    for item in lista_harpa:

        pagina_1 = banco.executarConsultaVetor('select texto from letras_harpa where id_harpa = %s and pagina = 1 order by paragrafo' % item['id'])
        pagina_2 = banco.executarConsultaVetor('select texto from letras_harpa where id_harpa = %s and pagina = 2 order by paragrafo' % item['id'])

        lista_final.append({'numero':'%03d' % item['id'], 'titulo':item['descricao'], 'letras':pagina_1, 'letras_2':pagina_2, 'versao':'', 'pag':page})

        if (len(pagina_2) > 0):
            page += 1

        page += 1

        if tipo == 1: # se for completa pega também as versões alternativas

            versoes = banco.executarConsulta('select * from harpa_versionada where id_harpa = %s' % item['id'])

            for hino in versoes:

                pagina_1 = banco.executarConsultaVetor('select texto from letras_harpa_versionada where id_harpa_versionada = %s and pagina = 1 order by paragrafo' % hino['id'])
                pagina_2 = banco.executarConsultaVetor('select texto from letras_harpa_versionada where id_harpa_versionada = %s and pagina = 2 order by paragrafo' % hino['id'])

                lista_final.append({'numero':'%03d' % item['id'], 'titulo':item['descricao'], 'letras':pagina_1, 'letras_2':pagina_2, 'versao':hino['titulo_versao'], 'pag':page})

                if (len(pagina_2) > 0):
                    page += 1

                page += 1            

    return render_template('render_pdf_harpa.jinja', lista=lista_final, total=total, data=hoje, tipo=tipo)

@app.route('/controlador', methods=['GET', 'POST'])
def controlador():

    global estado
    global current_presentation
    global index

    if estado == 0: # sem apresentação
        return redirect('/')
    elif estado == 1: # música

        if (current_presentation['tipo'] == 'musicas'):

            config = {'letra':banco.executarConsulta("select valor from config where id = 'cor-musica-letra'")[0]['valor'], 'fundo':banco.executarConsulta("select valor from config where id = 'cor-musica-fundo'")[0]['valor'], 'mark':banco.executarConsulta("select valor from config where id = 'cor-musica-mark'")[0]['valor']}

            fundo = banco.executarConsulta('select filename from capas where id_musica = %s' % current_presentation['id'])

            if len(fundo) < 1:
                fundo = 'images/' + banco.executarConsulta("select valor from config where id = 'background'")[0]['valor']
            else:
                fundo = 'images/capas/' + fundo[0]['filename']

            lista_slides = banco.executarConsulta("select `text-slide`, categoria, ifnull(anotacao, '') as anotacao, pos from slides where id_musica = %s order by pos" % current_presentation['id'])

            return render_template('controlador.jinja', lista_slides=lista_slides, index=index, fundo=fundo, config=config)
        
    elif estado == 2: #biblia

        livro = banco.executarConsulta('select descricao, classificacao from livro_biblia where id = %s' % current_presentation['id'])[0]
        
        if livro['classificacao'] == 8 or livro['classificacao'] == 9:
            descricao_livro = 'Epístola'
        elif livro['classificacao'] == 6:
            descricao_livro = 'Evangelho'
        else:
            descricao_livro = 'Livro'

        if current_presentation['id'] == '19':
            descricao_cap = 'Número'
            descricao_vers = 'Verso'
        else:
            descricao_cap = 'Capítulo'
            descricao_vers = 'Versículo'            

        versao = banco.executarConsultaVetor("select descricao_longa from lista_tabelas_biblia where nome_tabela = '%s'" % current_presentation['versao'])[0]


        head = {'livro':livro['descricao'].replace('1', 'I').replace('2', 'II'), 'descricao_livro':descricao_livro, 'descricao_cap':descricao_cap, 'cap':current_presentation['cap'], 'descricao_vers':descricao_vers, 'versao':versao}
        lista = banco.executarConsulta('select ver, texto from %s where livro = %s and cap = %s order by ver' % (current_presentation['versao'], current_presentation['id'], current_presentation['cap']))

        if (index + 1) > len(lista):
            index = len(lista) - 1

        return render_template('controlador_biblia.jinja', head=head, lista=lista, index=index + 1)
    
    elif estado == 3: #harpa
        config = {'letra':banco.executarConsulta("select valor from config where id = 'cor-harpa-letra'")[0]['valor'], 'fundo':banco.executarConsulta("select valor from config where id = 'cor-harpa-fundo'")[0]['valor'], 'num':banco.executarConsulta("select valor from config where id = 'cor-harpa-num'")[0]['valor'], 'red':banco.executarConsulta("select valor from config where id = 'cor-harpa-red'")[0]['valor']}
        lista_slides = banco.executarConsulta("select `text-slide`, categoria, ifnull(anotacao, '') as anotacao, pos from slides_harpa where id_harpa = %s order by pos" % current_presentation['id'])

        titulo = banco.executarConsultaVetor('select descricao from harpa where id = %s' % current_presentation['id'])[0]
        number = 'HINO %s' % '{0:03}'.format(int(current_presentation['id']))
        nome_autor = banco.executarConsultaVetor('select nome from autor_harpa where id = (select autor from harpa where id = %s)' % current_presentation['id'])[0]

        return render_template('controlador_harpa.jinja', lista_slides=lista_slides, index=index, config=config, titulo=titulo, numero=number, autor=nome_autor, titulo_versao='')
    elif estado == 4: # harpa versionada
        config = {'letra':banco.executarConsulta("select valor from config where id = 'cor-harpa-letra'")[0]['valor'], 'fundo':banco.executarConsulta("select valor from config where id = 'cor-harpa-fundo'")[0]['valor'], 'num':banco.executarConsulta("select valor from config where id = 'cor-harpa-num'")[0]['valor'], 'red':banco.executarConsulta("select valor from config where id = 'cor-harpa-red'")[0]['valor']}
        lista_slides = banco.executarConsulta("select `text-slide`, categoria, ifnull(anotacao, '') as anotacao, pos from slides_harpa_versionada where id_harpa_versionada = %s order by pos" % current_presentation['id'])

        titulo = banco.executarConsultaVetor('select descricao from harpa where id = (select id_harpa from harpa_versionada where id = %s)' % current_presentation['id'])[0]
        number = 'HINO %s' % '{0:03}'.format(int(banco.executarConsultaVetor('select id_harpa from harpa_versionada where id = %s' % current_presentation['id'])[0]))
        nome_autor = banco.executarConsultaVetor('select nome from autor_harpa where id = (select autor from harpa where id = (select id_harpa from harpa_versionada where id = %s))' % current_presentation['id'])[0]
        titulo_versao = banco.executarConsultaVetor('select titulo_versao from harpa_versionada where id = %s' % current_presentation['id'])[0]

        return render_template('controlador_harpa.jinja', lista_slides=lista_slides, index=index, config=config, titulo=titulo, numero=number, autor=nome_autor, titulo_versao=titulo_versao)
    elif estado == 5: # arquivo pptx
        return render_template('controlador_pptx.jinja', total=current_presentation['total'], index=index)

    return 'erro'

@app.route('/abrir_biblia', methods=['GET', 'POST'])
def abrir_biblia():

    if request.method == 'POST':
        if request.is_json:
            info = request.json

            # preciso que liste os capítulos
            if info['destino'] == 1:
                capitulos = banco.executarConsultaVetor("select cap from biblia_arc where livro = %s group by cap order by cap" % info['id'])
                return jsonify(capitulos)
            
            # pegar os versículos
            if info['destino'] == 2:
                tabelas = banco.executarConsultaVetor('select * from lista_tabelas_biblia')

                lista_final = []
                lista_intermediaria = {}
                total = []

                for item in tabelas:
                    texto = banco.executarConsultaVetor('select texto from %s where livro = %s and cap = %s order by ver' % (item, info['livro'], info['cap']))
                    lista_intermediaria[item] = texto
                    total.append(len(texto))

                maximo = max(total)

                for i in range(0, maximo):
                    dict_aux = {'ver':i + 1}

                    for item in tabelas:
                        try:
                            dict_aux[item] = lista_intermediaria[item][i]
                        except:
                            dict_aux[item] = '-'

                    lista_final.append(dict_aux)

                return jsonify(lista_final)
            
            # iniciar apresentação
            if info['destino'] == 3:
                global current_presentation
                global estado
                global index        

                estado = 2 #biblia
                index = info['ver'] - 1
                current_presentation = {'id':info['livro'], 'tipo':'biblia', 'cap':info['cap'], 'versao':info['versao']}

                socketio.emit('refresh', 1)
                socketio.emit('update_roteiro', 1)

                insert_log(7, 1, info['livro'], info['cap'])

                return jsonify(True)

    antigo_testamento = banco.executarConsulta("select livro_biblia.id, livro_biblia.descricao, classificacao from livro_biblia inner join classificacao_livro on classificacao_livro.id = livro_biblia.classificacao inner join testamento on classificacao_livro.testamento = testamento.id where testamento.id = 1")
    novo_testamento = banco.executarConsulta("select livro_biblia.id, livro_biblia.descricao, classificacao from livro_biblia inner join classificacao_livro on classificacao_livro.id = livro_biblia.classificacao inner join testamento on classificacao_livro.testamento = testamento.id where testamento.id = 2")

    return render_template('biblia.jinja', novo=novo_testamento, antigo=antigo_testamento, status='')


@app.route('/abrir_musica', methods=['GET', 'POST'])
def abrir_musica():

    musicas = banco.executarConsulta('select id, titulo, (select group_concat(id_vinculo) from vinculos_x_musicas where id_musica = id) as vinc from musicas')
    musicas.sort(key=lambda t: (locale.strxfrm(t['titulo'])))
    categoria = banco.executarConsulta('select * from categoria_departamentos')
    for item in categoria:
        item['subcategoria'] = banco.executarConsulta('select id, descricao from subcategoria_departamentos where supercategoria = %s' % item['id'])

    return render_template('musicas.jinja', musicas=musicas, status='', categoria=categoria)

@app.route('/abrir_harpa', methods=['GET', 'POST'])
def abrir_harpa():

    harpa = banco.executarConsulta('select * from harpa order by id')

    return render_template('harpa.jinja', status='', harpa=harpa)



@app.route('/calendar', methods=['GET', 'POST'])
def calendar():
    return redirect('/slide')


@app.route('/calendario', methods=['GET', 'POST'])
def calendario():

    status = ''

    if request.method == 'POST':
        if 'calendario_semanal' in request.form:
            
            calendario = json.loads(request.form.getlist('calendario_semanal')[0]) 
            
            if inserir_calendario_semanal(calendario):
                status = '<div class="alert alert-success alert-dismissible fade show" role="alert"><strong>Operação concluída com sucesso!</strong> Calendário Semanal alterado!<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
            else:
                status = '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Erro fatal!</strong> Falha ao tentar inserir dados no banco.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'

    semana = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
    
    
    # Obtém a data atual
    data_atual = datetime.datetime.now()

    # Calcula a segunda-feira anterior
    segunda_feira_anterior = data_atual - datetime.timedelta(days=data_atual.weekday())
    
    # montar calendário da semana
    calendario_semanal = []
    blocks_sem = []

    for i in range(0, 7):
        dia = segunda_feira_anterior + datetime.timedelta(days=i)
        posicao_mensal = (dia.day - 1) // 7 + 1
        
        sql = 'SELECT texto, case when ativo = 1 then "checked" else "" end as checkbox FROM calendario_semanal WHERE dia_semana = %s and (dia_mensal = 0 or dia_mensal = %s) ORDER BY plain_text' % (i, posicao_mensal)
        lista = executarConsultaCalendario(sql)

        calendario_semanal.append({'dia':dia.strftime('%d'), 'desc':semana[i], 'eventos':lista, 'mes':dia.strftime('%m'), 'ano':dia.strftime('%Y')})

        aux = [] # montar bloco para edição
        new_list = executarConsultaCalendario('select texto, dia_mensal from calendario_semanal where dia_semana = %s order by dia_semana, dia_mensal, plain_text' % i)
        for item in new_list:
            aux.append({'type':'paragraph', 'data':{'text':item['texto']}})

        blocks_sem.append({'paragrafos':aux, 'dia_mensal':aux[0]['dia_mensal']})


    return render_template('calendario.jinja', semana=semana, status=status, calendario_semanal=calendario_semanal, blocks_sem=blocks_sem)



@app.route('/slide', methods=['GET', 'POST'])
def slide():

    global estado
    global current_presentation
    global index

    if estado == 0:
        fundo = 'images/Wallpaper/' + banco.executarConsulta("select valor from config where id = 'wallpaper'")[0]['valor']
        config = {'fundo':'black', 'mark':'white', 'letra':'white'}
        return render_template('PowerPoint.jinja', fundo=fundo, lista_slides=[], index=0, config=config)
    elif estado == 1: # se iniciou uma apresentação de música

        # estabelecer configuração da música
        config = {'letra':banco.executarConsulta("select valor from config where id = 'cor-musica-letra'")[0]['valor'], 'fundo':banco.executarConsulta("select valor from config where id = 'cor-musica-fundo'")[0]['valor'], 'mark':banco.executarConsulta("select valor from config where id = 'cor-musica-mark'")[0]['valor']}

        if (current_presentation['tipo'] == 'musicas'):
            fundo = banco.executarConsulta('select filename from capas where id_musica = %s' % current_presentation['id'])

            if len(fundo) < 1:
                fundo = 'images/' + banco.executarConsulta("select valor from config where id = 'background'")[0]['valor']
            else:
                fundo = 'images/capas/' + fundo[0]['filename']

            lista_slides = banco.executarConsulta('select `text-slide`, categoria from slides where id_musica = %s order by pos' % current_presentation['id'])

            return render_template('PowerPoint.jinja', fundo=fundo, lista_slides=lista_slides, index=index, config=config)

    elif estado == 2: # iniciou uma apresentação da Bíblia

        livro = banco.executarConsultaVetor('select descricao from livro_biblia where id = %s' % current_presentation['id'])[0].replace('1', 'I').replace('2', 'II')
        head = {'nome':livro, 'cap':current_presentation['cap'], 'versao':current_presentation['versao'].replace('biblia_', '').upper()}

        lista = banco.executarConsultaVetor('select texto from %s where livro = %s and cap = %s order by ver' % (current_presentation['versao'], current_presentation['id'], current_presentation['cap']))

        config = {'letra':banco.executarConsulta("select valor from config where id = 'cor-biblia-letra'")[0]['valor'], 'fundo':banco.executarConsulta("select valor from config where id = 'cor-biblia-fundo'")[0]['valor'], 'seta':banco.executarConsulta("select valor from config where id = 'cor-biliba-arrow'")[0]['valor']}

        if (index + 1) > len(lista):
            index = len(lista) - 1        

        return render_template('PowerPoint_Biblia.jinja', head=head, lista=lista, index=index, versiculo=index + 1, config=config)

    elif estado == 3: #harpa
        config = {'letra':banco.executarConsulta("select valor from config where id = 'cor-harpa-letra'")[0]['valor'], 'fundo':banco.executarConsulta("select valor from config where id = 'cor-harpa-fundo'")[0]['valor'], 'num':banco.executarConsulta("select valor from config where id = 'cor-harpa-num'")[0]['valor'], 'red':banco.executarConsulta("select valor from config where id = 'cor-harpa-red'")[0]['valor']}
        fundo = 'images/Harpa.jpg'
        info = banco.executarConsulta('select harpa.descricao as nome, autor_harpa.nome as autor from harpa inner join autor_harpa on autor_harpa.id = harpa.autor where harpa.id = %s' % current_presentation['id'])[0]

        lista_slides = banco.executarConsulta('select `text-slide`, categoria from slides_harpa where id_harpa = %s order by pos' % current_presentation['id'])
        numero = 'HINO %s' % '{0:03}'.format(int(current_presentation['id']))

        return render_template('PowerPoint_Harpa.jinja', fundo=fundo, config=config, lista_slides=lista_slides, index=index, info=info, num=numero, titulo_versao='')

    elif estado == 4: # harpa versionada
        config = {'letra':banco.executarConsulta("select valor from config where id = 'cor-harpa-letra'")[0]['valor'], 'fundo':banco.executarConsulta("select valor from config where id = 'cor-harpa-fundo'")[0]['valor'], 'num':banco.executarConsulta("select valor from config where id = 'cor-harpa-num'")[0]['valor'], 'red':banco.executarConsulta("select valor from config where id = 'cor-harpa-red'")[0]['valor']}
        fundo = 'images/Harpa.jpg'
        info = banco.executarConsulta('select harpa.descricao as nome, autor_harpa.nome as autor from harpa inner join autor_harpa on autor_harpa.id = harpa.autor where harpa.id = (select id_harpa from harpa_versionada where id = %s)' % current_presentation['id'])[0]

        lista_slides = banco.executarConsulta('select `text-slide`, categoria from slides_harpa_versionada where id_harpa_versionada = %s order by pos' % current_presentation['id'])
        numero = 'HINO %s' % '{0:03}'.format(int(banco.executarConsultaVetor('select id_harpa from harpa_versionada where id = %s' % current_presentation['id'])[0]))
        titulo_versao = banco.executarConsultaVetor('select titulo_versao from harpa_versionada where id = %s' % current_presentation['id'])[0]

        return render_template('PowerPoint_Harpa.jinja', fundo=fundo, config=config, lista_slides=lista_slides, index=index, info=info, num=numero, titulo_versao=titulo_versao)
    elif estado == 5: # Arquivo pptx

        return render_template('PowerPoint_Verdadeiro.jinja', index=index, total=current_presentation['total'])


@app.route('/updateSlide', methods=['GET', 'POST'])
def updateSlide():
    if request.method == 'POST':

        if request.is_json: # application/json
            # handle your ajax request here!

    
            global index

            index = int(request.json)

            socketio.emit('update', index)
          
            return jsonify(True)


@app.route('/updateBiblia', methods=['GET', 'POST'])
def updateBiblia():            
    if request.method == 'POST':

        if request.is_json: # application/json
            # handle your ajax request here!

            info = request.json

            if info['destino'] == 'scroll':
                socketio.emit('scroll_biblia', info['direcao'])

            if info['destino'] == 'change':
                global index
                index = info['index']
                socketio.emit('update', index)

            return jsonify(True)

@app.route('/changeBackground', methods=['GET', 'POST'])
def changeBackground():
    if request.method == 'POST':

        if request.is_json: # application/json
            # handle your ajax request here!
            file = request.json
            completo = '/static/videos/' + file

            socketio.emit('change', completo)
            return jsonify(True)

@app.route('/addHarpa_versionada', methods=['GET', 'POST'])
def addHarpa_versionada():
    if request.method == 'POST':   
        info = json.loads(request.form.getlist('json_send')[0]) 
        
        if info['destino'] == '-1': # inserir novo hino versionado
            if banco.inserirNovoHinoVersionado(info):
                status = '<div class="alert alert-success alert-dismissible fade show" role="alert"><strong>Operação concluída com sucesso!</strong> Nova Versão do Hino de número <strong>' + info['numero'] + '. ' + info['titulo'] + '</strong> criada com sucesso!.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
                insert_log(3, 3, info['numero'], 0)
            else:
                status = '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Erro falta!</strong> Falha ao tentar inserir slides e letra no Banco, favor verificar o problema.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
        else: # editar hino versionado
            if banco.editarNovoHinoVersionado(info['destino'], info):
                status = '<div class="alert alert-success alert-dismissible fade show" role="alert"><strong>Operação concluída com sucesso!</strong> <b>"' + info['titulo_versao'] + '"</b> do Hino de número <strong>' + info['numero'] + '. ' + info['titulo'] + '</strong> editada com sucesso!.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
            else:
                status = '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Erro falta!</strong> Falha ao tentar inserir slides e letra no Banco, favor verificar o problema.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'

        harpa = banco.executarConsulta('select * from harpa order by id')

        return render_template('harpa.jinja', harpa=harpa, status=status)

@app.route('/addHarpa', methods=['GET', 'POST'])
def addHarpa():
    if request.method == 'POST':   
        info = json.loads(request.form.getlist('json_send')[0]) 
        
        # inserir harpa
        if banco.insertOrUpdate({'id':info['numero'], 'descricao':"'" + info['titulo'] + "'", 'autor':info['autor']}, 'id', 'harpa'):
            if banco.inserirNovoHino(info):
                status= '<div class="alert alert-success alert-dismissible fade show" role="alert"><strong>Operação concluída com sucesso!</strong> Informações do Hino de número <strong>' + info['numero'] + '. ' + info['titulo'] + '</strong> inseridas com sucesso!.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
                insert_log(3, 3, info['numero'], 0)
            else:
                status= '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Erro falta!</strong> Falha ao tentar inserir slides e letra no Banco, favor verificar o problema.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
        else:
            status= '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Erro falta!</strong> Falha ao tentar inserir dados, favor verificar o problema.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
        
        harpa = banco.executarConsulta('select * from harpa order by id')

        return render_template('harpa.jinja', harpa=harpa, status=status)


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
def subtitle():
    
    global current_presentation
    global estado
    global index

    head = None
    align='center'

    if (estado == 1): #música
        legenda = banco.executarConsulta('select `text-legenda` from slides where id_musica = %s order by pos' % current_presentation['id'])
        lista = [banco.executarConsulta('select titulo from musicas where id = %s' % current_presentation['id'])[0]['titulo']]
        for item in legenda:
            lista.append(item['text-legenda'])

        tamanho = 20

    elif (estado == 2): #biblia
        livro = banco.executarConsultaVetor('select descricao from livro_biblia where id = %s' % current_presentation['id'])[0].replace('1', 'I').replace('2', 'II')
        head = {'nome':livro, 'cap':current_presentation['cap'], 'versao':current_presentation['versao'].replace('biblia_', '').upper()}
        lista = banco.executarConsultaVetor('select texto from %s where livro = %s and cap = %s order by ver' % (current_presentation['versao'], current_presentation['id'], current_presentation['cap']))

        if (index + 1) > len(lista):
            index = len(lista) - 1  

        if len(lista[index]) > 199:
            tamanho = 30
        else:
            tamanho = 20  

        align = 'justify'
        
    elif (estado == 3): #harpa
        legenda = banco.executarConsulta('select `text-legenda` from slides_harpa where id_harpa = %s order by pos' % current_presentation['id'])
        lista = [banco.executarConsulta('select descricao from harpa where id = %s' % current_presentation['id'])[0]['descricao']]
        for item in legenda:
            lista.append(item['text-legenda'])

        tamanho = 20
    elif (estado == 4): #harpa versionada
        legenda = banco.executarConsulta('select `text-legenda` from slides_harpa_versionada where id_harpa_versionada = %s order by pos' % current_presentation['id'])
        lista = [banco.executarConsulta('select descricao from harpa where id = (select id_harpa from harpa_versionada where id = %s)' % current_presentation['id'])[0]['descricao']]
        for item in legenda:
            lista.append(item['text-legenda'])

        tamanho = 20
    elif (estado == 5): # Arquivo PPTX
        lista = current_presentation['lista']

        if len(lista[index]) > 199:
            tamanho = 30
        else:
            tamanho = 20 
    else:
        lista = []
        tamanho = 0

    return render_template('subtitle.jinja', legenda=lista, index=index, tamanho=tamanho, head=head, estado=estado, align=align)

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

@app.route('/edit_harpa_versionada', methods=['GET', 'POST'])
def edit_harpa_versionada():

    lista_texto = []
    blocks = []
    blocks_s = []
    titulo = ''
    autor = 0
    destino = '0'

    autores = banco.executarConsulta('select id, abreviacao from autor_harpa order by abreviacao')

    if request.method == "POST":

        destino = '0'

        if 'json_back' in request.form:
            info = json.loads(request.form.getlist('json_back')[0])

            titulo = info['listaGeral']['titulo']
            titulo_versao = info['listaGeral']['titulo_versao']
            desc_versao = info['listaGeral']['desc_versao']
            number = info['listaGeral']['numero']
            autor = info['listaGeral']['autor']
            autor_desc = info['listaGeral']['autor_desc']
            lista_texto = info['listaGeral']['slides']
            destino = info['destino']
        else:
            nome = request.form.getlist('file')[0]
            lista_texto = getListTextHarpa(harpa_dir + nome)
            
            number = int(nome.replace('.pptx', '').replace('HINO ', ''))
            titulo = readCSVHarpa(number)
            

        # recriar lista pro editor
        for item in lista_texto:
            blocks.append({'type':'paragraph', 'data':{'text':item['text-slide']}})
            blocks_s.append({'type':'paragraph', 'data':{'text':item['subtitle']}})

    
    return render_template('editor_harpa_versionada.jinja', lista_texto=lista_texto, blocks=blocks, blocks_s=blocks_s, titulo=titulo, number=number, destino=destino, autores=autores, autor=autor, autor_desc=autor_desc, titulo_versao=titulo_versao, desc_versao=desc_versao)


@app.route('/edit_harpa', methods=['GET', 'POST'])
def edit_harpa():

    lista_texto = []
    blocks = []
    blocks_s = []
    titulo = ''
    autor = 0
    destino = '0'

    autores = banco.executarConsulta('select id, abreviacao from autor_harpa order by abreviacao')

    if request.method == "POST":

        destino = '0'

        if 'json_back' in request.form:
            info = json.loads(request.form.getlist('json_back')[0])

            titulo = info['listaGeral']['titulo']
            number = info['listaGeral']['numero']
            autor = info['listaGeral']['autor']
            lista_texto = info['listaGeral']['slides']
            destino = info['destino']
        else:
            nome = request.form.getlist('file')[0]
            lista_texto = getListTextHarpa(harpa_dir + nome)
            
            number = int(nome.replace('.pptx', '').replace('HINO ', ''))
            titulo = readCSVHarpa(number)
            

        # recriar lista pro editor
        for item in lista_texto:
            blocks.append({'type':'paragraph', 'data':{'text':item['text-slide']}})
            blocks_s.append({'type':'paragraph', 'data':{'text':item['subtitle']}})

    
    return render_template('editor_harpa.jinja', lista_texto=lista_texto, blocks=blocks, blocks_s=blocks_s, titulo=titulo, number=number, destino=destino, autores=autores, autor=autor)

@app.route('/enviarDadosNovaVersaoHino', methods=['GET', 'POST'])
def enviarDadosNovaVersaoHino():
    if request.method == "POST":
        info = json.loads(request.form.getlist('json_data_send')[0])

        cat_slides = banco.executarConsulta('select * from categoria_slide')
        cat_slides_list = []

        nome_autor = banco.executarConsulta('select nome from autor_harpa where id = %s' % info['autor'])[0]['nome']

        blocks = []
        blocks_2 = []
        for item in info['slides']:
            blocks.append({'type':'paragraph', 'data':{'text':item['text-slide']}})

        destino = request.form.getlist('destino')[0]
        if destino != '-1': # significa que é edição e não acréscimo
            letras = banco.executarConsulta('select * from letras_harpa_versionada where id_harpa_versionada = %s and pagina = 1 order by paragrafo' % destino)
            blocks = []

            for item in letras:
                blocks.append({'type':'paragraph', 'data':{'text':item['texto']}})

            letras = banco.executarConsulta('select * from letras_harpa_versionada where id_harpa_versionada = %s and pagina = 2 order by paragrafo' % destino)
            blocks_2 = []

            for item in letras:
                blocks_2.append({'type':'paragraph', 'data':{'text':item['texto']}})

            cat_slides_list = banco.executarConsulta('select categoria from slides_harpa_versionada where id_harpa_versionada = %s order by pos' % destino)
        else: # significa que é acréscimo, portanto vai buscar a letra da harpa padrão
            letras = banco.executarConsulta('select * from letras_harpa where id_harpa = %s and pagina = 1 order by paragrafo' % info['numero'])
            blocks = []

            for item in letras:
                blocks.append({'type':'paragraph', 'data':{'text':item['texto']}})

            letras = banco.executarConsulta('select * from letras_harpa where id_harpa = %s and pagina = 2 order by paragrafo' % info['numero'])
            blocks_2 = []

            for item in letras:
                blocks_2.append({'type':'paragraph', 'data':{'text':item['texto']}})

            cat_slides_list = banco.executarConsulta('select categoria from slides_harpa where id_harpa = %s order by pos' % info['numero'])


        return render_template('save_harpa_versionada.jinja', info=info, cat_slides=cat_slides, blocks=blocks, blocks_2=blocks_2, cat_slides_list=cat_slides_list, destino=destino, autor=nome_autor, titulo_versao=info['titulo_versao'], desc_versao=info['desc_versao'], desc_autor=info['autor_desc'])


@app.route('/enviarDadosNovoHino', methods=['GET', 'POST'])
def enviarDadosNovoHino():
    if request.method == "POST":
        info = json.loads(request.form.getlist('json_data_send')[0])
        cat_slides = banco.executarConsulta('select * from categoria_slide')
        cat_slides_list = []

        nome_autor = banco.executarConsulta('select nome from autor_harpa where id = %s' % info['autor'])[0]['nome']

        blocks = []
        blocks_2 = []
        texto = ''
        for item in info['slides']:
            texto = item['text-slide'].replace('<b>', '').replace('</b>', '').replace('<br>', ' ') # retirando o negrito e os espaços

            # inserindo negrito na numeração
            if texto[0:22] == '<span class="cdx-num">':
                texto = '<b>' + texto
                pos = texto.find('</span>')

                texto = texto[:pos] + '</b>' + texto[pos:]

            blocks.append({'type':'paragraph', 'data':{'text':texto}})


        destino = request.form.getlist('destino')[0]
        if destino != '0': # significa que é edição e não acréscimo
            letras = banco.executarConsulta('select * from letras_harpa where id_harpa = %s and pagina = 1 order by paragrafo' % destino)
            blocks = []

            for item in letras:
                blocks.append({'type':'paragraph', 'data':{'text':item['texto']}})

            letras = banco.executarConsulta('select * from letras_harpa where id_harpa = %s and pagina = 2 order by paragrafo' % destino)
            blocks_2 = []

            for item in letras:
                blocks_2.append({'type':'paragraph', 'data':{'text':item['texto']}})

            cat_slides_list = banco.executarConsulta('select categoria from slides_harpa where id_harpa = %s order by pos' % destino)

        return render_template('save_harpa.jinja', info=info, cat_slides=cat_slides, blocks=blocks, blocks_2=blocks_2, cat_slides_list=cat_slides_list, destino=destino, autor=nome_autor)


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
        blocks_2 = []
        for item in info['slides']:
            blocks.append({'type':'paragraph', 'data':{'text':item['text-slide']}})

        destino = request.form.getlist('destino')[0]
        if destino != '0': # significa que é edição e não acréscimo
            vinculos = banco.executarConsulta('select * from vinculos_x_musicas where id_musica = %s' % destino)
            letras = banco.executarConsulta('select * from letras where id_musica = %s and pagina = 1 order by paragrafo' % destino)
            blocks = []

            for item in letras:
                blocks.append({'type':'paragraph', 'data':{'text':item['texto']}})

            letras = banco.executarConsulta('select * from letras where id_musica = %s and pagina = 2 order by paragrafo' % destino)
            blocks_2 = []

            for item in letras:
                blocks_2.append({'type':'paragraph', 'data':{'text':item['texto']}})            

            cat_slides_list = banco.executarConsulta('select categoria from slides where id_musica = %s order by pos' % destino)

        return render_template('save_musica.jinja', info=info, cat_slides=cat_slides, blocks=blocks, blocks_2=blocks_2, categoria=categoria, status=status, vinculos=vinculos, cat_slides_list=cat_slides_list, destino=destino)

@app.route('/upload_capa',  methods=['GET', 'POST'])
def upload_capa():
    isthisFile = request.files.get('file')
    id = request.form.getlist('id')[0]
    filename = str(id) + os.path.splitext(isthisFile.filename)[1]

    isthisFile.save('./static/images/capas/' + filename)

    banco.insertOrUpdate({'id_musica':id, 'filename':"'" + filename + "'"}, 'id_musica', 'capas')

    return jsonify('./static/images/capas/' + filename)

@app.route('/converto_to_pdf_list', methods=['GET', 'POST'])
async def converto_to_pdf_list():
    global temp_pdf
    temp_pdf = request.json

    pdf_path = 'static/docs/musica.pdf'

    browser = await launch(
        handleSIGINT=False,
        handleSIGTERM=False,
        handleSIGHUP=False
    )

    hostname = request.headers.get('Host')

    page = await browser.newPage()
    #await page.goto('http://localhost:120/render_pdf?ls=render_preview')
    await page.goto('http://%s/render_pdf?ls=render_preview' % (hostname), {'waitUntil':'networkidle2'})
    await page.pdf({'path': pdf_path, 'format':'A5', 'scale':1.95, 'margin':{'top':18}, 'printBackground':True})
    await browser.close()

    return jsonify(pdf_path)


@app.route('/get_info_harpa', methods=['GET', 'POST'])
def get_info_harpa():
    if request.method == "POST":
        if request.is_json:

            id = request.json
            letras = banco.executarConsulta('select texto from letras_harpa where id_harpa = %s order by paragrafo' % id['id'])
            numero = 'HINO %s' % '{0:03}'.format(int(id['id']))
            titulo = banco.executarConsultaVetor('select descricao from harpa where id = %s' % id['id'])[0]
            autor = banco.executarConsultaVetor('select nome from autor_harpa where id = (select autor from harpa where id = %s)' % id['id'])[0]
            versoes = banco.executarConsulta('select id, titulo_versao, desc_versao from harpa_versionada where id_harpa = %s' % id['id'])


            return jsonify({'letras':letras, 'numero':numero, 'titulo':titulo, 'autor':autor, 'versoes':versoes})
        
@app.route('/get_info_harpa_versionada', methods=['GET', 'POST'])
def get_info_harpa_versionada():
    if request.method == "POST":
        if request.is_json:

            info = request.json

            letras = banco.executarConsulta('select * from letras_harpa_versionada where id_harpa_versionada = %s' % info['id'])
            desc_versao = banco.executarConsultaVetor('select desc_versao from harpa_versionada where id = %s' % info['id'])[0]


            return {'letras':letras, 'desc_versao':desc_versao}

@app.route('/get_info_musica', methods=['GET', 'POST'])
def get_info_musica():

    if request.method == "POST":
        if request.is_json:

            id = request.json

            sql = 'select ' + \
                    "categoria_departamentos.descricao || ' - ' || subcategoria_departamentos.descricao as vinculo, " + \
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
        senha = encriptar(request.form.getlist('senha')[0])
        destino = request.form.getlist('destino')[0]
        
        if senha == banco.executarConsultaVetor("select valor from config where id = 'senha_adm'")[0]:
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
            musicas = banco.executarConsulta('select id, titulo, (select group_concat(id_vinculo) from vinculos_x_musicas where id_musica = id) as vinc from musicas order by titulo')
            status= '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Senha incorreta!</strong> Por favor digite a senha correta para abrir a área de Cadastro e Alteração.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'

            categoria = banco.executarConsulta('select * from categoria_departamentos')
            for item in categoria:
                item['subcategoria'] = banco.executarConsulta('select id, descricao from subcategoria_departamentos where supercategoria = %s' % item['id'])

            return render_template('musicas.jinja', musicas=musicas, status=status, categoria=categoria)

    return render_template('erro.jinja', log='Erro fatal ao tentar redirecionar para área de Administrador.')

@app.route('/verificarSenhaLog', methods=['GET', 'POST'])
def verificarSenhaLog():
    if request.method == "POST":
        senha = encriptar(request.form.getlist('senha')[0])

        if senha == banco.executarConsultaVetor("select valor from config where id = 'senha_adm'")[0]:
            return redirect('/log')
        else:
            status = status = '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Senha Incorreta!</strong> A senha está incorreta, não será possível acessar a página do log.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'

            number = None
            nome_autor = None

            if estado == 1:
                titulo = banco.executarConsulta('select titulo from %s where id = %s' % (current_presentation['tipo'], current_presentation['id']))[0]['titulo']

                tipo = 'Música'

                ls_capa = banco.executarConsulta('select filename from capas where id_musica = %s' % current_presentation['id'])
                
                if (len(ls_capa) > 0):
                    capa = 'static/images/capas/' + ls_capa[0]['filename']
                else:
                    capa = 'static/images/Background.jpeg'    
            
            elif estado == 2:
                titulo = banco.executarConsultaVetor('select descricao from livro_biblia where id = %s' % current_presentation['id'])[0] + ' ' + current_presentation['cap'] + ':' + str(index + 1)
                tipo = 'Bíblia'
                capa = 'static/images/Biblia.jpg'
            elif estado == 3:
                titulo = banco.executarConsultaVetor('select descricao from harpa where id = %s' % current_presentation['id'])[0]
                number = 'HINO %s' % '{0:03}'.format(int(current_presentation['id']))
                nome_autor = banco.executarConsultaVetor('select nome from autor_harpa where id = (select autor from harpa where id = %s)' % current_presentation['id'])[0]
                tipo = 'Harpa'
                capa = 'static/images/Harpa.jpg'
            elif estado == 4:
                id_harpa = banco.executarConsultaVetor('select id_harpa from harpa_versionada where id = %s' % current_presentation['id'])[0]
                titulo = banco.executarConsultaVetor('select descricao from harpa where id = %s' % id_harpa)[0]
                number = 'HINO %s' % '{0:03}'.format(int(id_harpa))
                nome_autor = banco.executarConsultaVetor('select nome from autor_harpa where id = (select autor from harpa where id = %s)' % id_harpa)[0]
                tipo = 'Harpa'
                capa = 'static/images/Harpa.jpg'
            elif estado == 5: # apresentação PowerPoint
                titulo = current_presentation['titulo']
                tipo = 'Apresentação PowerPoint'
                capa = 'static/images/SlidesPPTX/0.png'
            else:
                titulo = None
                tipo = None
                capa = 'static/images/Background.jpeg'

            return render_template('home.jinja', roteiro=roteiro, estado=estado, titulo=titulo, tipo=tipo, capa=capa, number=number, autor=nome_autor, status=status)

@app.route('/verificarSenhaHarpa', methods=['GET', 'POST'])
def verificarSenhaHarpa():
    if request.method == "POST":
        senha = encriptar(request.form.getlist('senha')[0])
        destino = request.form.getlist('destino')[0]

        if senha == banco.executarConsultaVetor("select valor from config where id = 'senha_adm'")[0]:

            autores = banco.executarConsulta('select id, abreviacao from autor_harpa order by abreviacao')

            if destino == '0':
                return render_template('editor_harpa.jinja', lista_texto=[], blocks=[], blocks_s=[], titulo='', destino='0', autores=autores, autor=0)
            elif destino == '-1': # ele vai adicionar uma nova versão da música da harpa
                id_versao = request.form.getlist('id_versao')[0]

                blocks = []
                blocks_s = []
                titulo = banco.executarConsulta('select descricao from harpa where id = %s' % id_versao)[0]['descricao']
                autor = banco.executarConsultaVetor('select autor from harpa where id = %s' % id_versao)[0]
                desc_autor = banco.executarConsulta('select abreviacao from autor_harpa where id = %s' % autor)[0]['abreviacao']
                lista_texto = banco.executarConsulta("select pos, `text-slide`, `text-legenda` as subtitle, ifnull(anotacao, '') as anotacao from slides_harpa where id_harpa = %s order by pos" % id_versao)

                # recriar lista pro editor
                for item in lista_texto:
                    blocks.append({'type':'paragraph', 'data':{'text':item['text-slide']}})
                    blocks_s.append({'type':'paragraph', 'data':{'text':item['subtitle']}})

                return render_template('editor_harpa_versionada.jinja', lista_texto=lista_texto, blocks=blocks, blocks_s=blocks_s, titulo=titulo, destino=destino, autores=autores, number=id_versao, autor=autor, autor_desc=desc_autor)
            elif destino == '-2': # ele vai editar a versão do hino da harpa
                id_versao = request.form.getlist('id_versao')[0]

                blocks = []
                blocks_s = []
                numero = banco.executarConsultaVetor('select id_harpa from harpa_versionada where id = %s' % id_versao)[0]
                titulo = banco.executarConsulta('select descricao from harpa where id = (select id_harpa from harpa_versionada where id = %s)' % id_versao)[0]['descricao']
                autor = banco.executarConsultaVetor('select autor from harpa where id = (select id_harpa from harpa_versionada where id = %s)' % id_versao)[0]
                desc_autor = banco.executarConsulta('select abreviacao from autor_harpa where id = %s' % autor)[0]['abreviacao']
                lista_texto = banco.executarConsulta("select pos, `text-slide`, `text-legenda` as subtitle, ifnull(anotacao, '') as anotacao from slides_harpa_versionada where id_harpa_versionada = %s order by pos" % id_versao)
                titulo_versao = banco.executarConsultaVetor('select titulo_versao from harpa_versionada where id = %s' % id_versao)[0]
                desc_versao = banco.executarConsultaVetor('select desc_versao from harpa_versionada where id = %s' % id_versao)[0]

                # recriar lista pro editor
                for item in lista_texto:
                    blocks.append({'type':'paragraph', 'data':{'text':item['text-slide']}})
                    blocks_s.append({'type':'paragraph', 'data':{'text':item['subtitle']}})

                return render_template('editor_harpa_versionada.jinja', lista_texto=lista_texto, blocks=blocks, blocks_s=blocks_s, titulo=titulo, destino=id_versao, autores=autores, number=numero, autor=autor, autor_desc=desc_autor, titulo_versao=titulo_versao, desc_versao=desc_versao)
            else: # ele vai editar e não salvar um novo
                blocks = []
                blocks_s = []
                titulo = banco.executarConsulta('select descricao from harpa where id = %s' % destino)[0]['descricao']
                autor = banco.executarConsultaVetor('select autor from harpa where id = %s' % destino)[0]
                lista_texto = banco.executarConsulta("select pos, `text-slide`, `text-legenda` as subtitle, ifnull(anotacao, '') as anotacao from slides_harpa where id_harpa = %s order by pos" % destino)

                # recriar lista pro editor
                for item in lista_texto:
                    blocks.append({'type':'paragraph', 'data':{'text':item['text-slide']}})
                    blocks_s.append({'type':'paragraph', 'data':{'text':item['subtitle']}})

                return render_template('editor_harpa.jinja', lista_texto=lista_texto, blocks=blocks, blocks_s=blocks_s, titulo=titulo, destino=destino, autores=autores, number=destino, autor=autor)
            
        else:
            harpa = banco.executarConsulta('select * from harpa order by id')
            status= '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Senha incorreta!</strong> Por favor digite a senha correta para abrir a área de Cadastro e Alteração.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'

            return render_template('harpa.jinja', harpa=harpa, status=status)

    return render_template('erro.jinja', log='Erro fatal ao tentar redirecionar para área de Administrador.')


@app.route('/gerar_pdf', methods=['GET', 'POST'])
async def gerar_pdf():
    ls = request.json
    pdf_path = 'static/docs/musica.pdf'

    browser = await launch(
        handleSIGINT=False,
        handleSIGTERM=False,
        handleSIGHUP=False
    )

    hostname = request.headers.get('Host')

    page = await browser.newPage()
    await page.goto('http://%s/render_pdf?ls=%s' % (hostname, ls), {'waitUntil':'networkidle2'})
    await page.pdf({'path': pdf_path, 'format':'A5', 'scale':1.95, 'margin':{'top':18}, 'printBackground':True})
    await browser.close()

    return jsonify(pdf_path)

@app.route('/gerar_pdf_harpa', methods=['GET', 'POST'])
async def gerar_pdf_harpa():
    pdf_path = 'static/docs/harpa.pdf'

    info = request.json

    browser = await launch(
        handleSIGINT=False,
        handleSIGTERM=False,
        handleSIGHUP=False
    )

    hostname = request.headers.get('Host')

    page = await browser.newPage()

    await page.goto('http://%s/render_pdf_harpa?tipo=%s' % (hostname, info['tipo']), {'waitUntil':'networkidle2'})
    await page.pdf({'path': pdf_path, 'format':'A5', 'scale':1.95, 'margin':{'top':18}, 'printBackground':True})
    await browser.close()

    return jsonify(pdf_path)

@app.route('/pesquisarBiblia', methods=['GET', 'POST'])
def pesquisarBiblia():

    if request.method == 'POST':
        if 'pesquisa' in request.form:
            pesquisa = request.form['pesquisa'].replace("'", "''")
            pesquisa_original = request.form['pesquisa']
            status = ''


        if len(pesquisa) > 2:
            tabelas = banco.executarConsultaVetor('select nome_tabela from lista_tabelas_biblia')

            pesquisa = '%' + pesquisa.replace(' ', '%') + '%'

            resultados = banco.executarConsulta("select livro, cap, ver from biblia_arc where texto like '%s' union select livro, cap, ver from biblia_naa where texto like '%s' union select livro, cap, ver from biblia_nvi where texto like '%s' union select livro, cap, ver from biblia_nvt where texto like '%s' order by livro, cap, ver" % (pesquisa, pesquisa, pesquisa, pesquisa))
            

            for item in resultados:

                item['desc_livro'] = banco.executarConsultaVetor('select descricao from livro_biblia where id = %s'  % item['livro'])[0]

                sql = 'select '
                for tb in tabelas:
                    sql += '%s.texto as %s, ' % (tb, tb)

                sql = sql[:-2] + ' from %s ' % tabelas[0]

                for i in range(1, 4):
                    sql += 'inner join %s on %s.livro = %s.livro and %s.cap = %s.cap and %s.ver = %s.ver ' % (tabelas[i], tabelas[0], tabelas[i], tabelas[0], tabelas[i], tabelas[0], tabelas[i])

                sql += 'where %s.livro = %s and %s.cap = %s and %s.ver = %s' % (tabelas[0], item['livro'], tabelas[0], item['cap'], tabelas[0], item['ver'])

                texto = banco.executarConsulta(sql)[0]

                
                lista_palavras = pesquisa_original.split(' ')
                for tb in tabelas:
                    txt_aux = converHTML_to_List(texto[tb])
                    texto_final = ''

                    for element in txt_aux:
                        if len(element['text']) > 0:
                            for txt in element['text']:
                                aux = txt
                                for palavra in lista_palavras:
                                    if len(palavra) > 1:
                                        compiled = re.compile(re.escape(palavra), re.IGNORECASE)
                                        res = compiled.sub('<span class="highlight">' + palavra + "</span>", aux)
                                        aux = str(res)
                                
                                texto_final += aux + '&nbsp;'

                    item[tb] = texto_final


            
            if len(resultados) > 0:
                return render_template('resultado_pesquisa_biblia.jinja', resultados=resultados, tabelas=tabelas, pesquisa=pesquisa_original)
            else:
                status= '<div style="margin-top:1vh;" class="alert alert-warning alert-dismissible fade show" role="alert"><strong>Atenção!</strong> Sem resultados encontrados, verifique os termos utilizados.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'    
        else:
            status= '<div style="margin-top:1vh;" class="alert alert-warning alert-dismissible fade show" role="alert"><strong>Atenção!</strong> Por favor utilize uma palavra de três letras ou mais.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'

        
        antigo_testamento = banco.executarConsulta("select livro_biblia.id, livro_biblia.descricao, classificacao from livro_biblia inner join classificacao_livro on classificacao_livro.id = livro_biblia.classificacao inner join testamento on classificacao_livro.testamento = testamento.id where testamento.id = 1")
        novo_testamento = banco.executarConsulta("select livro_biblia.id, livro_biblia.descricao, classificacao from livro_biblia inner join classificacao_livro on classificacao_livro.id = livro_biblia.classificacao inner join testamento on classificacao_livro.testamento = testamento.id where testamento.id = 2")

        return render_template('biblia.jinja', novo=novo_testamento, antigo=antigo_testamento, status=status)

@app.route('/pesquisarLetraHarpa', methods=['GET', 'POST'])
def pesquisarLetraHarpa():

    if request.method == 'POST':
        if 'pesquisa' in request.form:
            pesquisa = request.form['pesquisa'].replace("'", '’')
            pesquisa_original = pesquisa
            status = ''

            if pesquisa != '':
                if len(pesquisa) > 2:
                    lista_palavras = pesquisa.split(' ')
                    pesquisa = r'%' + pesquisa.replace(' ', r'%') + r'%'


                    resultado_pesquisa = banco.executarConsulta("select letras_harpa.id_harpa, harpa.descricao, replace(texto, '<br>', ' ') as texto from letras_harpa inner join harpa on harpa.id = letras_harpa.id_harpa where letras_harpa.texto like '%s' or harpa.descricao like '%s' group by id_harpa order by harpa.id" % (pesquisa, pesquisa))

                    for item in resultado_pesquisa:

                        texto = converHTML_to_List(item['texto'])
                        texto_final = ''

                        for element in texto:
                            if len(element['text']) > 0:
                                aux = element['text'][0]
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
                        return render_template('resultado_pesquisa_harpa.jinja', resultado_pesquisa=resultado_pesquisa, lista_palavras=lista_palavras, pesquisa=pesquisa_original)
                    else:
                        status= '<div class="alert alert-warning alert-dismissible fade show" role="alert"><strong>Atenção!</strong> Sem resultados encontrados, por favor revise os termos pesquisados.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
                else:
                    status= '<div class="alert alert-warning alert-dismissible fade show" role="alert"><strong>Atenção!</strong> Por favor utilize uma palavra de três letras ou mais.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
            else:
                status= '<div class="alert alert-warning alert-dismissible fade show" role="alert"><strong>Atenção!</strong> Por favor digite algumas palavras na pesquisa.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
            
            harpa = banco.executarConsulta('select * from harpa order by id')

            return render_template('harpa.jinja', status=status, harpa=harpa)


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

@app.route('/alterar_fundo', methods=['GET', 'POST'])
def alterar_fundo():

    if request.method == 'POST':
        if request.is_json:
            info = request.json
            
            banco.change_config(info)

            socketio.emit('refresh', 1)

            return jsonify(True)


    destino = request.args.get('destino')

    if (destino == 'm'):

        config = {'letra':banco.executarConsulta("select valor from config where id = 'cor-musica-letra'")[0]['valor'], 'fundo':banco.executarConsulta("select valor from config where id = 'cor-musica-fundo'")[0]['valor'], 'mark':banco.executarConsulta("select valor from config where id = 'cor-musica-mark'")[0]['valor']}

        #pegar um texto aleatório pra testar o preview
        texto = banco.executarConsulta("select * from slides where `text-slide` like '" + '%<mark class="cdx-marker">%' + "' and categoria = 1")
        result = texto[random.randint(0, len(texto))]['text-slide']

        return render_template('alterar_fundo.jinja', titulo='Música', preview=result, config=config)

    return 'yes'


@app.route('/slide_pix', methods=['GET', 'POST'])
def slide_pix():

    if request.method == 'POST': # significa que o comando de solicitação de troca foi feito
        socketio.emit('pix', 1)
        return jsonify(True)

    pix = banco.executarConsultaVetor("select valor from config where id = 'chave-pix-igreja'")[0]

    return render_template('slide_pix.jinja', pix=pix)

@app.route('/wallpaper', methods=['GET', 'POST'])
def wallpaper():

    if request.method == 'POST':
        
        if 'nome_arquivo' in request.form:

            arquivo = "'%s'" % request.form['nome_arquivo']

            info = [{'id':"'wallpaper'", 'valor':arquivo}]

            banco.change_config(info)


            socketio.emit('change_wallpaper', 1)
            
            

    path = os.path.dirname(os.path.realpath(__file__)) + '\\static\\images\\Wallpaper'

    onlyfiles = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    atual = '/static/images/Wallpaper/' + banco.executarConsultaVetor("select valor from config where id='wallpaper'")[0]

    return render_template('wallpaper.jinja', lista=onlyfiles, atual=atual)


@app.route('/abrir_pptx', methods=['GET', 'POST'])
def abrir_pptx():

    global current_presentation
    global estado
    global index    

    status = ''

    if request.method == 'POST':

        file = request.files.get('file')

        path = os.path.dirname(os.path.realpath(__file__)) + '\\static\\uploads\\file.pptx'
        path_img = os.path.dirname(os.path.realpath(__file__)) + '\\static\\images\\SlidesPPTX'

        file.save(path) # processo de salvamento do arquivo

        # agora que salvei o arquivo, preciso acessar e convertê-lo em uma lista de imagens e salvá-las
        lista_prs_pptx = ppt_to_png(path, path_img)

        if len(lista_prs_pptx) > 0:
            status = '<div class="alert alert-success alert-dismissible fade show" role="alert"><strong>Apresentação Iniciada com sucesso!</strong> Arquivo <strong>' + file.filename + '</strong> do PowerPoint importado e convertido em apresentação com sucesso! <a href="/controlador">Clique aqui para abrir o Controlador</a>.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'

            estado = 5 # apresentação de arquivo pptx
            index = 0
            current_presentation = {'titulo':file.filename, 'lista':lista_prs_pptx, 'total':len(lista_prs_pptx)} # estrutura pra esse tipo de apresentação se difere dos outros

            socketio.emit('refresh', 1)

            return redirect('/controlador')

        else:
            status = '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Erro falta!</strong> Arquivo não selecionado ou falha em tentar importar arquivo do PowerPoint.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'

        # iniciar comando para exportar os slides
        #result = prs.convertToListJPG()

    return render_template('abrir_pptx.jinja', status=status)

@app.route('/log', methods=['GET', 'POST'])
def log():

    sql = "SELECT " + \
          r"strftime('%d/%m/%Y às %H:%M',data_hora) as data, " + \
          "cat_log.descricao as atividade, " + \
          r'CASE WHEN tipo = 1 THEN livro_biblia.descricao || " - Cap. " || capitulo WHEN tipo = 2 THEN musicas.titulo ELSE PRINTF("%03d", harpa.id) || " - " || harpa.descricao END as alvo, ' + \
          "log.atividade as num_atividdade " + \
          "FROM log " + \
          "INNER JOIN cat_log ON cat_log.id = log.atividade " + \
          "LEFT JOIN musicas ON musicas.id = log.id_musica LEFT JOIN harpa ON harpa.id = log.id_harpa LEFT JOIN livro_biblia ON livro_biblia.id = log.livro_biblia order by data_hora desc"
    
    log = banco.executarConsulta(sql)

    cont = 1

    for item in log:
        item['order'] = cont
        cont += 1

    return render_template('log.jinja', log=log)

@app.route('/hook', methods=['GET', 'POST'])
def hook():

    if request.method == 'POST':

        if request.is_json:
            info = request.json

            fotos = get_photos(info['id'])

            return jsonify(fotos)


    acessos = get_all_hook()

    return render_template('hook.jinja', acessos=acessos)



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

            if info['tipo'] == 'musicas':
                estado = 1
                insert_log(5, 2, info['id'], 0)
            elif info['tipo'] == 'harpa':
                estado = 3
                insert_log(5, 3, info['id'], 0)
            elif info['tipo'] == 'harpa_versionada':
                estado = 4
                insert_log(5, 3, banco.executarConsultaVetor('select id_harpa from harpa_versionada where id = %s' % info['id'])[0], 0)

            index = 0

            socketio.emit('refresh', 1)
            socketio.emit('update_roteiro', 1)

            return jsonify(True)
        
        elif 'proximaPRS' in request.form: # pediu para iniciar nova apresentação na lista do roteiro 
            for item in roteiro:
                if (not item['check']):
                    item['check'] = True
                    current_presentation = {'id':item['id'], 'tipo':item['tipo']}

                    if (item['tipo'] == 'musicas'):
                        estado = 1
                        insert_log(5, 2, current_presentation['id'], 0)
                    elif (item['tipo'] == 'harpa'):
                        estado = 3
                        insert_log(5, 3, current_presentation['id'], 0)
                    elif item['tipo'] == 'harpa_versionada':
                        estado = 4
                        insert_log(5, 3, banco.executarConsultaVetor('select id_harpa from harpa_versionada where id = %s' % info['id'])[0], 0)

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

                            if (item['tipo'] == 'musicas'):
                                estado = 1
                            elif (item['tipo'] == 'harpa'):
                                estado = 3
                            elif (item['tipo'] == 'harpa_versionada'):
                                estado = 4                                
                            
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

            if info['tipo'] == 'harpa':
                insert_log(9, 3, info['id'], 0)
            elif info['tipo'] == 'musicas':
                insert_log(6, 2, info['id'], 0)
            elif info['tipo'] == 'harpa_versionada':
                insert_log(9, 3, banco.executarConsultaVetor('select id_harpa from harpa_versionada where id = %s' % info['id'])[0], 0)

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