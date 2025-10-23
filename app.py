from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, Response
from flask_socketio import SocketIO, emit
from flask_cors import CORS
#from threading import Lock
from waitress import serve
from PowerPoint import getListText, getListTextHarpa
from read_csv import readCSVHarpa
#from MySQL import db
from SQLite_DB import db
from SQLite_DB import insert_log, get_all_hook, get_photos, inserir_calendario_semanal, executarConsultaCalendario, alterarEventoAtivo, inserir_calendario_mensal, inserirFestaDepCalendario, inserirFestaDepSedeCalendario, executarConsultaOldMusic
from HTML_U import converHTML_to_List
import locale
import math
import json
import os
import os.path
import re
import datetime
import random
import calendar
import base64
import subprocess
from pptx_file import ppt_to_png
from utils_crip import encriptar
from utilitarios import pegarListaSemanas, pegarTrimestre, pegarLicoes
from playwright.sync_api import sync_playwright
from playwright_pdf_generator import run_pdf_generation
from collections import defaultdict

app=Flask(__name__)
app.secret_key = "abc123"
app.config['SECRET_KEY'] = 'justasecretkeythatishouldputhere'
#app.config['UPLOAD_FOLDER'] = r'C:\Users\Operador\OneDrive - Secretaria da Educação do Estado de São Paulo\IGREJA\Backup\sistema-slide\static\uploads'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
#socketio = SocketIO(app)
CORS(app)

estado = 0
current_presentation = {'id':0, 'tipo':''}
index = 0
pause_index = 0
ponteiro_musical = 0
roteiro = []
temp_pdf = None
window_browser = None

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
            capa = 'static/images/Wallpaper/' + banco.executarConsulta("select valor from config where id = 'wallpaper'")[0]['valor']
    
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
    elif estado == 6: # calendário
        titulo = 'Calendário Semanal e Mensal'
        tipo = "Apresentação do Calendário"
        capa = 'static/images/Calendar.png'
    elif estado == 7: # video player
        titulo = 'VideoPlayer'
        tipo = 'Vídeo MP4'
        capa = 'static/images/VideoPlayer.avif'
    elif estado == 8: #EBD
        licoes = pegarLicoes(datetime.datetime.now())
        id = int(current_presentation['id'])
        titulo = "Lição %02d - %s" % (id, licoes[id - 1]['dia'].strftime('%d/%m/%Y'))
        tipo = "Abertura da Lição de Domingo"
        capa = 'static/images/EBD.png'
    elif estado == 9: # musical
        titulo = banco.executarConsulta("select valor from config where id = 'titulo_musical'")[0]['valor']
        tipo = 'Musical'
        capa = 'static/' + banco.executarConsulta("select valor from config where id = 'capa_musical'")[0]['valor']
    elif estado == 10: # poesia
        titulo = banco.executarConsulta("select titulo from poesia where id = %s" % current_presentation['id'])[0]['titulo']
        tipo = 'Poesia'
        capa = 'static/images/Poesia.jpg'

    else:
        titulo = None
        tipo = None
        capa = 'static/images/Wallpaper/' + banco.executarConsulta("select valor from config where id = 'wallpaper'")[0]['valor']

    return render_template('home.jinja', roteiro=roteiro, estado=estado, titulo=titulo, tipo=tipo, capa=capa, number=number, autor=nome_autor, status='')

@app.route('/render_slide_pdf', methods=['GET', 'POST'])
def render_slide_pdf():

    id = request.args.get('id')
    destino = request.args.get('destino')
    id_name = request.args.get('id_name')
    classe = request.args.get('classe')

    cores = banco.executarConsulta("SELECT (SELECT valor FROM config WHERE id = 'cor-harpa-fundo') as cor_harpa_fundo, (SELECT valor FROM config WHERE id = 'cor-harpa-letra') as cor_harpa_letra, (SELECT valor FROM config WHERE id = 'cor-harpa-num') as cor_harpa_num, (SELECT valor FROM config WHERE id = 'cor-harpa-red') as cor_harpa_red, (SELECT valor FROM config WHERE id = 'cor-musica-fundo') as cor_musica_fundo, (SELECT valor FROM config WHERE id = 'cor-musica-letra') as cor_musica_letra, (SELECT valor FROM config WHERE id = 'cor-musica-mark') as cor_musica_mark")[0]
    slides = banco.executarConsulta('select `text-slide`, categoria from %s where %s = %s' % (destino, id_name, id))

    if classe == 'musica':
        capa = banco.executarConsultaVetor('select filename from capas where id_musica = %s' % id)
        if len(capa) > 0:
            capa = 'static/images/capas/' + capa[0]
        else:
            capa = 'static/images/upload_image.jpg'

    else: # capa da harpa

        if destino == 'slides_harpa_versionada':
            harpa_id = banco.executarConsultaVetor('select id_harpa from harpa_versionada where id = %s' % id)[0]
        else:
            harpa_id = id

        hostname = request.headers.get('Host')
        info = {'url':'http://%s/render_capa_harpa?id=%s' % (hostname, harpa_id), 'tipo':'capa'}

        try:
            with sync_playwright() as playwright:
                capa = run_pdf_generation(playwright, info)
                capa = base64.b64encode(capa).decode('utf-8')

        except Exception as e:
            print({"message": "Erro ao gerar Imagem", "error": str(e)}), 500


    for item in slides:
        item['categoria'] = 'cat-' + str(item['categoria']) + '-' + classe

    return render_template('render_slide_pdf.jinja', slides=slides, cores=cores, capa=capa, tipo=classe)

@app.route('/render_pdf', methods=['GET', 'POST'])
def render_pdf():
    lista_final = []
    cont = 1
    now = datetime.date.today()
    where_query = ''

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
            for cats in banco.executarConsulta('select id, descricao from subcategoria_departamentos where supercategoria = %s order by id' % item['id']):
                aux.append((cats['id'], cats['descricao']))

            lista_categoria.append({'descricao':item['descricao'], 'cats':aux})
    else: # fazer o processo reverso pra pegar isso daqui
        lista = ls[:-1].split(',')
        lista_categoria = []

        supercategoria = 0
        aux = []

        where_query = " WHERE id_subcategoria in (%s)" % ls[:-1]

        for item in lista:
            cat = banco.executarConsulta('select * from subcategoria_departamentos where id = %s' % item)[0]

            if cat['supercategoria'] != supercategoria:
                
                if len(aux) > 0:
                    descricao = banco.executarConsulta('select id, descricao from categoria_departamentos where id = %s' % supercategoria)[0]['descricao']
                    lista_categoria.append({'descricao':descricao, 'cats':aux})
                    aux = []

                supercategoria = cat['supercategoria']

            aux.append((cat['id'], cat['descricao']))

        descricao = banco.executarConsulta('select descricao from categoria_departamentos where id = %s' % supercategoria)[0]['descricao']
        lista_categoria.append({'descricao':descricao, 'cats':aux})

        lista_musicas = banco.executarConsulta('SELECT DISTINCT musicas.id, musicas.titulo ' + \
                                               'FROM musicas ' + \
                                               'INNER JOIN vinculos_x_musicas ON vinculos_x_musicas.id_musica = musicas.id ' + \
                                               'WHERE vinculos_x_musicas.id_vinculo IN (%s) ' % ls[:-1] + \
                                               'ORDER BY musicas.titulo')
    

    # ordenar
    lista_musicas.sort(key=lambda t: (locale.strxfrm(t['titulo'])))

    pages_sumario = []

    start_sumario_pages = {'start_1':0, 'end_1':32, 'start_2':32, 'end_2':64}

    #montar o sumário e pegar as letras das músicas
    if (len(lista_musicas) > 64):
        page = math.ceil((len(lista_musicas) - 64) / 70) + 4
        count_pages_sumario = math.ceil((len(lista_musicas) - 64) / 70)

        # criar um array rápido para dividir as páginas do sumário
        count_musica = 64
        for n in range(0, count_pages_sumario):
            pages_sumario.append({'start_1':count_musica, 'end_1': count_musica + 35, 'start_2': count_musica + 35, 'end_2':count_musica + 70})
            count_musica += 70

        pages_sumario[-1]['end_2'] = len(lista_musicas)

        if len(lista_musicas) < pages_sumario[-1]['end_1']:
            pages_sumario[-1]['end_1'] = len(lista_musicas)
            pages_sumario[-1]['start_2'] = 0
            pages_sumario[-1]['end_2'] = 0

    else:
        page = 4

        start_sumario_pages['end_2'] = len(lista_musicas)

        if len(lista_musicas) < start_sumario_pages['end_1']:
            start_sumario_pages['end_1'] = len(lista_musicas)
            start_sumario_pages['start_2'] = 0
            start_sumario_pages['end_2'] = 0

    # Buscar todas as letras antes do loop principal
    todas_letras = banco.executarConsulta(
        'SELECT id_musica, pagina, paragrafo, ' +
        'replace(replace(replace(texto, "<mark ", "<span "), "</mark>", "</span>"), "cdx-underline", "cdx-underline-view") as texto ' +
        'FROM letras ORDER BY id_musica, pagina, paragrafo'
    )

    # Indexar por música e página
    letras_indexadas = {}
    for linha in todas_letras:
        key = (linha['id_musica'], linha['pagina'])
        letras_indexadas.setdefault(key, []).append({'texto': linha['texto']})

    for item in lista_musicas:
        letras = letras_indexadas.get((item['id'], 1), [])
        letras_2 = letras_indexadas.get((item['id'], 2), [])
        
        titulo_sumario = item['titulo']
        if len(titulo_sumario) > 26:
            titulo_sumario = titulo_sumario[:23] + "..."
        
        lista_final.append({'id':item['id'], 'titulo':item['titulo'], 'titulo_sumario':titulo_sumario, 'letras':letras, 'letras_2':letras_2, 'cont':'{:02d}'.format(cont), 'pag':page})
        
        if (len(letras_2) > 0):
            page += 1
        
        cont += 1
        page += 1

    # Criar Sumário Final
    query = """
    SELECT
        m.id as id_musica,
        m.titulo,
        cd.descricao as categoria,
        sd.descricao as subcategoria,
        sd.id AS id_subcategoria
    FROM musicas m
    JOIN vinculos_x_musicas vm ON vm.id_musica = m.id
    JOIN subcategoria_departamentos sd ON sd.id = vm.id_vinculo
    JOIN categoria_departamentos cd ON cd.id = sd.supercategoria""" + where_query + """
    ORDER BY cd.id, sd.id, m.titulo
    """

    vinculos = banco.executarConsulta(query)

    sumario_categorico = defaultdict(lambda: defaultdict(list))

    for item in vinculos:
        categoria = item['categoria']
        subcat_nome = item['subcategoria']
        subcat_id = item['id_subcategoria']
        musica = {'id': item['id_musica'], 'titulo': item['titulo']}

        sumario_categorico[categoria][(subcat_nome, subcat_id)].append(musica)

    for categoria, subcats in sumario_categorico.items():
        for subcat_key in subcats:
            subcats[subcat_key].sort(key=lambda m: locale.strxfrm(m['titulo']))        

    return render_template('render_pdf.jinja', lista=lista_final, completo='true', lista_categoria=lista_categoria, total=len(lista_final), data=hoje, pages_sumario=pages_sumario, start_sumario_pages=start_sumario_pages, sumario_final=sumario_categorico, pagina_final=page)


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

@app.route('/render_capa_harpa', methods=['GET', 'POST'])
def render_capa_harpa():

    id = request.args.get('id')

    info = banco.executarConsulta('select harpa.id, descricao, autor_harpa.nome as autor from harpa inner join autor_harpa on autor_harpa.id = harpa.autor where harpa.id = %s' % id)[0]

    return render_template('render_capa_harpa.jinja', info=info)


@app.route('/render_capa_poesia', methods=['GET', 'POST'])
def render_capa_poesia():

    id = request.args.get('id')

    titulo = banco.executarConsultaVetor('select titulo from poesia where id = %s' % id)[0]

    return render_template('render_capa_poesia.jinja', titulo=titulo)


@app.route('/render_calendario_mensal', methods=['GET', 'POST'])
def render_calendario_mensal():

    # pegar agora os eventos mensais
    mes = request.args.get('mes')
    ano = request.args.get('ano')
    slides = []
    cont = 0
    
    semana = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
    semana_sqlite = ['Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado']
    mes_desc = calendar.month_name[int(mes)]

    # Cria um objeto de calendário
    cal = calendar.Calendar()

    # Obtém todos os dias do mês com os respectivos dias da semana
    dias_do_mes = [[dia, (dia_semana + 1) % 7, 'white'] for dia, dia_semana in cal.itermonthdays2(int(ano), int(mes)) if dia != 0]
    

    ultimo_dia_semana = 6 - dias_do_mes[len(dias_do_mes) - 1][1]

    sql = "SELECT id, inicio, fim, 'isolado' as tipo, strftime('%w', inicio) as semana, strftime('%w', fim) as semana_fim FROM calendario_mensal WHERE strftime('%m', inicio) = '" + str(mes).zfill(2) + "' AND strftime('%Y', inicio) = '" + str(ano) + "' AND fim > date('now') group by(inicio) "
    sql += "UNION ALL SELECT 0 as id, min(data_de) as inicio, max(date_ate) as fim, 'dep_jan' as tipo, strftime('%w', data_de) as semana, strftime('%w', date_ate) as semana_fim FROM calendario_festa_dep_sede WHERE strftime('%m', data_de) = '" + str(mes).zfill(2) + "' "
    sql += "UNION ALL SELECT id_congregacao as id, inicio, fim, 'dep' as tipo, strftime('%w', inicio) as semana, strftime('%w', fim) as semana_fim FROM calendario_festa_dep WHERE strftime('%m', inicio) = '" + str(mes).zfill(2) + "' AND strftime('%Y', inicio) = '" + str(ano) + "' AND fim > date('now')  ORDER BY inicio"

    eventos_mensais = executarConsultaCalendario(sql)

    for evento in eventos_mensais:
        info = {}

        if not evento['inicio'] is None:

            for i in range(int(evento['inicio'][8:10]), int(evento['fim'][8:10]) + 1):
                dias_do_mes[i - 1][2] = 'yellow'

        if evento['tipo'] == 'isolado':
            if evento['inicio'] == evento['fim']:
                desc_dia = '<span class="text-dark fw-bold">%s (</span><span class="fw-bold text-primary">%s</span><span class="fw-bold text-dark">)</span>' % (evento['inicio'][8:], semana_sqlite[int(evento['semana'])])
            else:
                desc_dia = '<span class="text-dark fw-bold">%s a %s (</span><span class="fw-bold text-primary">%s a %s</span><span class="fw-bold text-dark">)</span>' % (evento['inicio'][8:], evento['fim'][8:], semana_sqlite[int(evento['semana'])].replace('-feira', ''), semana_sqlite[int(evento['semana_fim'])].replace('-feira', ''))

            ls_aux = []
            for item in executarConsultaCalendario("SELECT texto FROM calendario_mensal where inicio = '%s' ORDER BY plain_text" % evento['inicio']):
                ls_aux.append(item['texto'])

            info['tipo'] = evento['tipo']
            info['desc_dia'] = desc_dia
            info['eventos'] = ls_aux
            info['pos'] = cont
            slides.append(info)

            cont += 1

        elif evento['tipo'] == 'dep':
            descricao = '<span class="fw-bold">RESUMO FESTA DE DEP. </span> - <span class="text-danger fw-bold">%s</span>' % executarConsultaCalendario('select descricao from congregacoes where id = %s' % evento['id'])[0]['descricao'].upper()

            ls_aux = []
            temp_segunda = datetime.datetime.strptime(evento['inicio'], r"%Y-%m-%d").date()
            temp_segunda = temp_segunda - datetime.timedelta(days=temp_segunda.weekday(), weeks=0)
            for item in executarConsultaCalendario(r"select dia_semana, strftime('%Hh%M', horario) as horario, " + "id_evento, eventos.descricao_curta as evento from eventos_festa_dep inner join eventos on eventos.id = eventos_festa_dep.id_evento where id_congregacao = %s order by dia_semana, horario" % evento['id']):
                ls_aux.append("<b>%s (<span class='text-primary mono'>%s</span>)</b> - Às <b class='text-danger'>%s, </b> <b class='text-decoration-underline'>%s</b>" % (int(temp_segunda.strftime("%d")) + item['dia_semana'], semana[int(item['dia_semana'])][0:3], item['horario'], item['evento']))
            
            info['tipo'] = evento['tipo']
            info['desc_dia'] = descricao
            info['eventos'] = ls_aux
            info['pos'] = cont
            slides.append(info)

            cont += 1

        elif evento['tipo'] == 'dep_jan' and not evento['inicio'] is None:
            descricao = '<span class="fw-bold">CONGRESSO UNIFICADO - </span><span class="text-danger fw-bold">IGREJA SEDE</span>'

            ls_aux = []
            eventos = executarConsultaCalendario(r'SELECT CASE WHEN data_de = date_ate THEN strftime("%d", data_de) ELSE strftime("%d", data_de) || " a " || strftime("%d", date_ate) END as dia, strftime("%w", data_de) as semana_inicio, strftime("%w", date_ate) as semana_fim, desc_curta as texto FROM calendario_festa_dep_sede ORDER BY data_de')

            for item in eventos:
                dia_semana = semana_sqlite[int(item['semana_inicio'])][0:3]
                if item['semana_inicio'] != item['semana_fim']:
                    dia_semana = semana_sqlite[int(item['semana_inicio'])][0:3] + ' a ' + semana_sqlite[int(item['semana_fim'])][0:3]

                ls_aux.append("<b>%s (<span class='text-primary'>%s</span>)</b> - %s" % (item['dia'], dia_semana, item['texto']))

            info['tipo'] = 'dep'
            info['desc_dia'] = descricao
            info['eventos'] = ls_aux
            info['pos'] = cont
            slides.append(info)

            cont += 1

    return render_template('render_calendario_mensal.jinja', slides=slides,  ano=ano, mes_desc=mes_desc, dias_do_mes=dias_do_mes, ultimo_dia_semana=ultimo_dia_semana)


@app.route('/render_calendario', methods=['GET', 'POST'])
def render_calendario():

    slides = []
    semana = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']

    # começar a criar o vetor com as informações
    segunda = datetime.datetime.strptime(request.args.get('semana'), r"%Y-%m-%d").date()
    #segunda = datetime.datetime.strptime('2024-09-02', r"%Y-%m-%d").date()
    domingo = segunda + datetime.timedelta(days=6)
    
    cont = 0

    for i in range(7):
        info = {}

        dia = segunda + datetime.timedelta(days=i)
        posicao_mensal = (dia.day - 1) // 7 + 1
        
        sql = 'SELECT id, texto, plain_text FROM calendario_semanal WHERE dia_semana = %s and (dia_mensal = 0 or dia_mensal = %s) and ativo = 1 UNION ALL ' % (i, posicao_mensal)
        sql += "select id, texto, plain_text from calendario_mensal where '%s' between inicio and fim UNION ALL " % dia.strftime(r"%Y-%m-%d")
        sql += "SELECT 0 as id, desc_longa as texto, plain_text FROM calendario_festa_dep_sede WHERE '%s' BETWEEN data_de AND date_ate UNION ALL " % dia.strftime(r"%Y-%m-%d")
        sql += "SELECT id_congregacao as id, 'Às <b class=\"text-danger\">' || replace(replace(horario, ':', 'h'), 'h00','h') || ',</b> Festa de Dep. <b class=\"text-decoration-underline\">' || congregacoes.descricao || CASE WHEN eventos_festa_dep.id_evento NOT IN (7, 8) THEN '</b>, Culto com participação do <b class=""text-decoration-underline"">' ELSE '</b> - <b>' END || eventos.descricao_curta || '</b>' as text, " \
                "'Às ' || replace(replace(horario, ':', 'h'), 'h00','h') || ', Festa de Dep. ' || congregacoes.descricao || CASE WHEN eventos_festa_dep.id_evento NOT IN (7, 8) THEN ', Culto com participação do ' ELSE ' - ' END || eventos.descricao_curta as plain_text " \
                r"FROM eventos_festa_dep INNER JOIN congregacoes ON congregacoes.id = eventos_festa_dep.id_congregacao INNER JOIN eventos on eventos.id = eventos_festa_dep.id_evento WHERE dia_semana_sqlite = strftime('%w', '" + dia.strftime(r"%Y-%m-%d") + "') "
        sql += "AND id_congregacao = (select id_congregacao from calendario_festa_dep where '%s' between inicio and fim) ORDER BY plain_text" % dia.strftime(r"%Y-%m-%d")

        info['dia'] = dia.strftime('%d')
        info['semana'] = semana[i]
        info['eventos'] = executarConsultaCalendario(sql)
        info['tipo'] = 'semanal'
        info['pos'] = cont + 2

        if len(info['eventos']) > 0:
            slides.append(info)
            cont += 1

    return render_template('render_calendario_semanal.jinja', slides=slides, inicio='%s/%s' % (slides[0]['dia'], request.args.get('semana')[5:7]), fim='%s' % domingo.strftime(r"%d/%m/%Y"))

@app.route('/add_historico', methods=['GET', 'POST'])
def add_historico():

    feedback = ''

    data_atual = datetime.datetime.now()

    if request.method == 'POST':
        if 'data_reload' in request.form:
            data_atual = datetime.datetime.strptime(request.form['data_reload'], '%Y-%m-%d')

        if 'lista' in request.form:
            dia = "'" + request.form['data'] + "'"
            tema = request.form['tipo']
            obs = "'" + request.form['obs'] + "'" if request.form['obs'] != '' else 'null'
            url = "'" + request.form['url'] + "'" if request.form['url'] != '' else 'null'

            lista = json.loads(request.form['lista'])
            
            if banco.inserirHistorico(dia, tema, obs, url, lista):
                tem_data = datetime.datetime.strptime(request.form['data'], '%Y-%m-%d')
                feedback = f'''<div class="alert alert-success alert-dismissible fade show" role="alert"><strong>Operação concluída com sucesso!</strong> Evento do dia <b>{tem_data.strftime('%d/%m/%Y')}</b> criado com sucesso! <a href= "/historico">Clique aqui</a> para ver os eventos.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'''
            else:
                feedback = '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Falha na operação!</strong>Erro de banco de dados! Não foi possível inserir registro de evento.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'


    tipos = banco.executarConsulta("select * from Historico_Tema order by descricao")
    query = f'''SELECT DISTINCT
                    CASE WHEN tipo = 1 THEN 1 WHEN tipo = 2 THEN 3 WHEN tipo = 3 THEN 2 END AS tipo_evento,
                    CASE 
                        WHEN tipo = 1 THEN (SELECT descricao FROM Historico_Evento WHERE Historico_Evento.id = 1)
                        WHEN tipo = 2 THEN (SELECT descricao FROM Historico_Evento WHERE Historico_Evento.id = 3)
                        WHEN tipo = 3 THEN (SELECT descricao FROM Historico_Evento WHERE Historico_Evento.id = 2)
                    END AS descricao_evento,
                    CASE
                        WHEN tipo = 1 THEN livro_biblia
                        WHEN tipo = 2 THEN id_musica
                        WHEN tipo = 3 THEN id_harpa
                    END AS id_item,
                    CASE
                        WHEN tipo = 1 THEN (SELECT descricao FROM livro_biblia WHERE id = livro_biblia)
                        WHEN tipo = 2 THEN (SELECT titulo FROM musicas WHERE id = id_musica)
                        WHEN tipo = 3 THEN id_harpa || ' - ' || (SELECT descricao FROM harpa WHERE id = id_harpa)
                    END AS descricao_item,
                    capitulo,
                    CASE
                        WHEN tipo = 1 THEN 'table-warning'
                        WHEN tipo = 2 THEN 'table-primary'
                        ELSE 'table-success' END AS cor
                FROM log
                WHERE data_hora LIKE '{data_atual.strftime('%Y-%m-%d')}%' AND atividade IN (5, 6, 7, 8, 9) AND tipo in (1, 2, 3) ORDER BY data_hora'''
    
    items = banco.executarConsulta(query)
    tipos_items = banco.executarConsulta("select id, descricao from Historico_Evento order by id")
    livros = banco.executarConsulta("select id, descricao from livro_biblia order by id")
    musicas = banco.executarConsulta("select id, titulo from musicas order by titulo")
    harpas = banco.executarConsulta("select id, descricao from harpa order by id")
    departamentos = banco.executarConsulta("select id, descricao from Historico_Departamentos order by id")
    forma_musical = banco.executarConsulta("select id, descricao from Historico_Evento_Musica_Cat order by id")
    tipos_leitura = banco.executarConsulta("select id, descricao from Historico_Evento_Biblia_Cat order by id")

    return render_template('add_historico.jinja', data=data_atual.strftime('%Y-%m-%d'), tipos=tipos, items=items, tipos_items=tipos_items, musicas=musicas, livros=livros, harpas=harpas, departamentos=departamentos, forma_musical=forma_musical, tipos_leitura=tipos_leitura, feedback=feedback)

@app.route('/historico', methods=['GET', 'POST'])
def historico():

    semana_sqlite = ['Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado']
    status = ''

    if request.method == 'GET':
        status = request.args.get('status', '')

    if request.method == 'POST':
        if request.is_json:
            info = request.json

            if info['destino'] == 1:

                id = info['id']

                query = f'''SELECT 
                            id_roteiro,
                            Historico_Evento.descricao AS tipo,
                            CASE
                                WHEN id_tipo_evento = 1 THEN id_livro_biblia || '-' || cap_biblia
                                WHEN id_tipo_evento = 2 THEN harpa.id
                                WHEN id_tipo_evento = 3 THEN musicas.id
                            END AS id_item,
                            CASE
                                WHEN id_tipo_evento = 1 THEN livro_biblia.descricao || ', ' || cap_biblia
                                WHEN id_tipo_evento = 2 THEN harpa.id || ' - ' || harpa.descricao
                                WHEN id_tipo_evento = 3 THEN musicas.titulo
                            END AS desc_item,
                            CASE
                                WHEN id_tipo_evento = 1 THEN Historico_Evento_Biblia_Cat.descricao
                                ELSE Historico_Departamentos.descricao
                            END as departamento,
                            CASE
                                WHEN id_tipo_evento = 1 THEN iif(id_livro_biblia < 40,'AT','NT')
                                ELSE Historico_Evento_Musica_Cat.descricao
                            END as formato,
                            CASE
                                WHEN id_tipo_evento = 1 THEN 'table-warning'
                                WHEN id_tipo_evento = 2 THEN 'table-primary'
                                ELSE 'table-success' END AS cor       
                        FROM Historico_Registro_Eventos
                        INNER JOIN Historico_Evento ON Historico_Evento.id = Historico_Registro_Eventos.id_tipo_evento
                        LEFT JOIN livro_biblia ON livro_biblia.id = Historico_Registro_Eventos.id_livro_biblia
                        LEFT JOIN harpa ON harpa.id = Historico_Registro_Eventos.id_harpa
                        LEFT JOIN musicas ON musicas.id = Historico_Registro_Eventos.id_musica
                        LEFT JOIN Historico_Evento_Biblia_Cat ON Historico_Evento_Biblia_Cat.id = Historico_Registro_Eventos.id_cat_biblia
                        LEFT JOIN Historico_Departamentos ON Historico_Departamentos.id = Historico_Registro_Eventos.id_departamento
                        LEFT JOIN Historico_Evento_Musica_Cat ON Historico_Evento_Musica_Cat.id = Historico_Registro_Eventos.id_cat_musica
                        WHERE Historico_Registro_Eventos.id_roteiro = {id}'''

                detalhes = banco.executarConsulta(f"SELECT Historico_Roteiro.id, Tema, STRFTIME('%d/%m/%Y', Dia) as desc_dia, STRFTIME('%w', Dia) as semana, Historico_Tema.descricao as tipo, IFNULL(OBS, '-') as OBS, IFNULL(URL, '#') as URL FROM Historico_Roteiro INNER JOIN Historico_Tema ON Historico_Tema.id = Historico_Roteiro.Tema WHERE Historico_Roteiro.id = {id} ORDER BY Dia DESC")[0]
                itens = banco.executarConsulta(query)

                detalhes['semana'] = semana_sqlite[int(detalhes['semana'])]

                return jsonify({'detalhes':detalhes, 'itens':itens})

            elif info['destino'] == 2:
                
                ano = info['ano']

                eventos = banco.executarConsulta(r"SELECT Historico_Roteiro.id, strftime('%m', Dia) as mes, strftime('%Y', Dia) as ano, strftime('%d/%m/%Y', Dia) as data, strftime('%w', Dia) as semana, Historico_Tema.descricao as tema, Tema as tema_id FROM Historico_Roteiro INNER JOIN Historico_Tema ON Historico_Tema.id = Historico_Roteiro.Tema WHERE strftime('%Y', Dia) = '" + ano + "' ORDER BY Date(Dia) DESC")

                for evento in eventos:
                    evento['semana'] = semana_sqlite[int(evento['semana'])]

                return jsonify(eventos)

            elif info['destino'] == 3:

                tipo = info['tipo']
                id = info['id_item']

                match tipo:
                    case 'Harpa': # Harpa
                        titulo = '<b>%s.</b> %s' % (id, banco.executarConsultaVetor('SELECT descricao FROM harpa WHERE id = %s' % id)[0])
                        letras = banco.executarConsulta('SELECT pagina, paragrafo, replace(replace(replace(texto, "<mark ", "<span "), "</mark>", "</span>"), "cdx-underline", "cdx-underline-view") as texto FROM letras_harpa WHERE id_harpa = %s ORDER BY pagina, paragrafo' % id)
                        return jsonify({'titulo':titulo, 'letras':letras, 'destino':'abrir_musica'})
                    case 'Música': # Música
                        titulo = banco.executarConsultaVetor('SELECT titulo FROM musicas WHERE id = %s' % id)[0]
                        letras = banco.executarConsulta('SELECT pagina, paragrafo, replace(replace(replace(texto, "<mark ", "<span "), "</mark>", "</span> "), "cdx-underline", "cdx-underline-view") as texto FROM letras WHERE id_musica = %s ORDER BY pagina, paragrafo' % id)
                        return jsonify({'titulo':titulo, 'letras':letras, 'destino':'abrir_musica'})
                    case 'Leitura Bíblica': # Biblia
                        tabelas = banco.executarConsultaVetor('select * from lista_tabelas_biblia')

                        lista_final = []
                        lista_intermediaria = {}
                        total = []

                        livro = id.split('-')[0]
                        cap = id.split('-')[1] if len(id.split('-')) > 1 else '1'

                        for item in tabelas:
                            texto = banco.executarConsultaVetor('select texto from %s where livro = %s and cap = %s order by ver' % (item, livro, cap))
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

                        return jsonify({'lista':lista_final, 'destino':'abrir_biblia', 'cap':cap, 'livro':livro, 'titulo':banco.executarConsultaVetor('select descricao from livro_biblia where id = %s' % livro)[0], 'versoes':tabelas})

                return jsonify(None)

            elif info['destino'] == 4:

                if info['ano'] == '0':
                    top_10_harpa = banco.executarConsulta('select id_harpa, harpa.descricao as titulo, count(*) as qtd from Historico_Registro_Eventos inner join harpa on harpa.id = Historico_Registro_Eventos.id_harpa where id_tipo_evento = 2 group by id_harpa, titulo order by qtd desc limit 10')
                    top_10_musicas = banco.executarConsulta('select id_musica, musicas.titulo as titulo, count(*) as qtd from Historico_Registro_Eventos inner join musicas on musicas.id = Historico_Registro_Eventos.id_musica where id_tipo_evento = 3 group by id_musica, titulo order by qtd desc limit 10')
                    top_10_biblia = banco.executarConsulta('select livro_biblia.descricao || ", " || Historico_Registro_Eventos.cap_biblia as titulo, count(*) as qtd from Historico_Registro_Eventos inner join livro_biblia on livro_biblia.id = Historico_Registro_Eventos.id_livro_biblia where id_tipo_evento = 1 group by (titulo) order by qtd desc limit 10')                
                else:
                    top_10_harpa = banco.executarConsulta(f'''select id_harpa, harpa.descricao as titulo, count(*) as qtd from Historico_Registro_Eventos inner join harpa on harpa.id = Historico_Registro_Eventos.id_harpa inner join Historico_Roteiro on Historico_Roteiro.id = Historico_Registro_Eventos.id_roteiro where id_tipo_evento = 2 and strftime('%Y', Dia) = '{info['ano']}' group by id_harpa, titulo order by qtd desc limit 10''')
                    top_10_musicas = banco.executarConsulta(f'''select id_musica, musicas.titulo as titulo, count(*) as qtd from Historico_Registro_Eventos inner join musicas on musicas.id = Historico_Registro_Eventos.id_musica inner join Historico_Roteiro on Historico_Roteiro.id = Historico_Registro_Eventos.id_roteiro where id_tipo_evento = 3 and strftime('%Y', Dia) = '{info['ano']}' group by id_musica, titulo order by qtd desc limit 10''')
                    top_10_biblia = banco.executarConsulta(f'''select livro_biblia.descricao || ", " || Historico_Registro_Eventos.cap_biblia as titulo, count(*) as qtd from Historico_Registro_Eventos inner join livro_biblia on livro_biblia.id = Historico_Registro_Eventos.id_livro_biblia inner join Historico_Roteiro on Historico_Roteiro.id = Historico_Registro_Eventos.id_roteiro where id_tipo_evento = 1 and strftime('%Y', Dia) = '{info['ano']}' group by (titulo) order by qtd desc limit 10''')

                return jsonify({'biblia':top_10_biblia, 'harpa':top_10_harpa, 'musicas':top_10_musicas})

        elif 'Tema' in request.form:

            tema = request.form['Tema']
            id_tipo_evento = request.form['id_tipo_evento']
            obs = request.form['OBS']

            roteiros = banco.executarConsulta(r"SELECT Historico_Roteiro.id, strftime('%m', Dia) as mes, strftime('%Y', Dia) as ano, strftime('%d/%m/%Y', Dia) as data, strftime('%w', Dia) as semana, Historico_Tema.descricao as tema, Tema as tema_id, OBS, URL FROM Historico_Roteiro INNER JOIN Historico_Tema ON Historico_Tema.id = Historico_Roteiro.Tema WHERE (Tema = " + tema + " OR " + tema + " = 0) AND (OBS like '%" + obs + "%' OR '" + obs + "' = '') ORDER BY Date(Dia) DESC")

            where = 'WHERE id_tipo_evento = ' + id_tipo_evento

            match id_tipo_evento:
                case '0': # Todos os tipos de evento
                    where = ''
                case '1': # Biblia
                    where += f''' AND (id_livro_biblia = {request.form['id_livro_biblia']} OR {request.form['id_livro_biblia']} = 0) AND (id_cat_biblia = {request.form['id_cat_biblia']} OR {request.form['id_cat_biblia']} = 0)'''
                    cap_biblia = request.form['cap_biblia']
                    if cap_biblia != '':
                        where += f' AND cap_biblia = {cap_biblia}'
                case '2': # Harpa
                    where += f''' AND (id_harpa = {request.form['id_harpa']} OR {request.form['id_harpa']} = 0) AND (id_departamento = {request.form['id_departamento']} OR {request.form['id_departamento']} = 0)'''                    
                case '3': # Música
                    where += f''' AND (id_musica = {request.form['id_musica']} OR {request.form['id_musica']} = 0) AND (id_cat_musica = {request.form['id_cat_musica']} OR {request.form['id_cat_musica']} = 0) AND (id_departamento = {request.form['id_departamento']} OR {request.form['id_departamento']} = 0)'''

            query = f'''SELECT 
                        id_roteiro,
                        Historico_Evento.descricao AS tipo,
                        CASE
                            WHEN id_tipo_evento = 1 THEN id_livro_biblia || '-' || cap_biblia
                            WHEN id_tipo_evento = 2 THEN harpa.id
                            WHEN id_tipo_evento = 3 THEN musicas.id
                        END AS id_item,                        
                        CASE
                            WHEN id_tipo_evento = 1 THEN livro_biblia.descricao || ', ' || cap_biblia
                            WHEN id_tipo_evento = 2 THEN harpa.id || ' - ' || harpa.descricao
                            WHEN id_tipo_evento = 3 THEN musicas.titulo
                        END AS desc_item,
                        CASE
                            WHEN id_tipo_evento = 1 THEN Historico_Evento_Biblia_Cat.descricao
                            ELSE Historico_Departamentos.descricao
                        END as departamento,
                        CASE
                            WHEN id_tipo_evento = 1 THEN iif(id_livro_biblia < 40,'AT','NT')
                            ELSE Historico_Evento_Musica_Cat.descricao
                        END as formato,
                        CASE
                            WHEN id_tipo_evento = 1 THEN 'table-warning'
                            WHEN id_tipo_evento = 2 THEN 'table-primary'
                            ELSE 'table-success' END AS cor       
                    FROM Historico_Registro_Eventos
                    INNER JOIN Historico_Evento ON Historico_Evento.id = Historico_Registro_Eventos.id_tipo_evento
                    LEFT JOIN livro_biblia ON livro_biblia.id = Historico_Registro_Eventos.id_livro_biblia
                    LEFT JOIN harpa ON harpa.id = Historico_Registro_Eventos.id_harpa
                    LEFT JOIN musicas ON musicas.id = Historico_Registro_Eventos.id_musica
                    LEFT JOIN Historico_Evento_Biblia_Cat ON Historico_Evento_Biblia_Cat.id = Historico_Registro_Eventos.id_cat_biblia
                    LEFT JOIN Historico_Departamentos ON Historico_Departamentos.id = Historico_Registro_Eventos.id_departamento
                    LEFT JOIN Historico_Evento_Musica_Cat ON Historico_Evento_Musica_Cat.id = Historico_Registro_Eventos.id_cat_musica {where}'''

            lista_eventos = banco.executarConsulta(query)
            print(query)

            lista_final = []

            # Indexar por id do roteiro
            eventos_indexados = {}
            for item in lista_eventos:
                key = (item['id_roteiro'])
                eventos_indexados.setdefault(key, []).append({'desc_item': item['desc_item'], 'tipo': item['tipo'], 'departamento': item['departamento'], 'formato': item['formato'], 'cor': item['cor'], 'id_item': item['id_item']})

            for item in roteiros:
                eventos = eventos_indexados.get((item['id']), [])

                if len(eventos) > 0:
                    lista_final.append({'id':item['id'], 'mes':item['mes'], 'ano':item['ano'], 'data':item['data'], 'semana':semana_sqlite[int(item['semana'])], 'tema':item['tema'], 'tema_id':item['tema_id'], 'obs':item['OBS'], 'url':item['URL'], 'eventos':eventos})

            return render_template('resultado_pesquisa_historico.jinja', lista_final=lista_final)

    anos = banco.executarConsultaVetor(r"select distinct strftime('%Y', Dia) as ano from Historico_Roteiro order by ano desc")
    eventos = banco.executarConsulta(r"SELECT Historico_Roteiro.id, strftime('%m', Dia) as mes, strftime('%Y', Dia) as ano, strftime('%d/%m/%Y', Dia) as data, strftime('%w', Dia) as semana, Historico_Tema.descricao as tema, Tema as tema_id FROM Historico_Roteiro INNER JOIN Historico_Tema ON Historico_Tema.id = Historico_Roteiro.Tema WHERE strftime('%Y', Dia) = '" + anos[0] + "' ORDER BY Date(Dia) DESC")

    filtro_temas = banco.executarConsulta('select * from Historico_Tema order by descricao')
    filtro_eventos = banco.executarConsulta('select * from Historico_Evento')
    filtro_departamentos = banco.executarConsulta('select * from Historico_Departamentos')
    filtro_cat_musicas = banco.executarConsulta("select * from Historico_Evento_Musica_Cat")
    filtro_tipos_leitura = banco.executarConsulta("select * from Historico_Evento_Biblia_Cat")
    musicas = banco.executarConsulta('select id, titulo, (select group_concat(id_vinculo) from vinculos_x_musicas where id_musica = id) as vinc from musicas')
    musicas.sort(key=lambda t: (locale.strxfrm(t['titulo'])))
    harpa = banco.executarConsulta('select id, descricao as titulo from harpa order by id')
    livros = banco.executarConsulta('select id, descricao as titulo from livro_biblia order by id')
    top_10_harpa = banco.executarConsulta('select id_harpa, harpa.descricao as titulo, count(*) as qtd from Historico_Registro_Eventos inner join harpa on harpa.id = Historico_Registro_Eventos.id_harpa where id_tipo_evento = 2 group by id_harpa, titulo order by qtd desc limit 10')
    top_10_musicas = banco.executarConsulta('select id_musica, musicas.titulo as titulo, count(*) as qtd from Historico_Registro_Eventos inner join musicas on musicas.id = Historico_Registro_Eventos.id_musica where id_tipo_evento = 3 group by id_musica, titulo order by qtd desc limit 10')
    top_10_biblia = banco.executarConsulta('select livro_biblia.descricao || ", " || Historico_Registro_Eventos.cap_biblia as titulo, count(*) as qtd from Historico_Registro_Eventos inner join livro_biblia on livro_biblia.id = Historico_Registro_Eventos.id_livro_biblia where id_tipo_evento = 1 group by (titulo) order by qtd desc limit 10')

    for item in musicas:

        if len(item['titulo']) > 26:
            item['titulo'] = item['titulo'][:23] + "..."

    for item in harpa:
        if len(item['titulo']) > 26:
            item['titulo'] = item['titulo'][:23] + "..."

    return render_template('historico.jinja', anos=anos, eventos=eventos, semana_sqlite=semana_sqlite, filtro_temas=filtro_temas, filtro_eventos=filtro_eventos, filtro_departamentos=filtro_departamentos, filtro_cat_musicas=filtro_cat_musicas, musicas=musicas, harpa=harpa, filtro_tipos_leitura=filtro_tipos_leitura, livros=livros, feedback=status, top_10_harpa=top_10_harpa, top_10_musicas=top_10_musicas, top_10_biblia=top_10_biblia)

@app.route('/controlador', methods=['GET', 'POST'])
def controlador():

    global estado
    global current_presentation
    global index

    if estado == 0: # sem apresentação
        return redirect('/')
    elif estado == 1: # música

        if (current_presentation['tipo'] == 'musicas'):

            rows = banco.executarConsulta("SELECT id, valor FROM config")
            rows_dict = {row['id']: row['valor'] for row in rows}
            config = {'letra':rows_dict['cor-musica-letra'], 'fundo':rows_dict['cor-musica-fundo'], 'mark':rows_dict['cor-musica-mark'],  'alternante':rows_dict['cor-musica-alternante']}

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
    
    elif estado == 6: # calendario

        slides = []
        semana = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
        semana_sqlite = ['Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado']

        # começar a criar o vetor com as informações
        segunda = datetime.datetime.strptime(current_presentation['semana'], r"%Y-%m-%d").date()
        domingo = segunda + datetime.timedelta(days=6)
        
        cont = 0

        for i in range(7):
            info = {}

            dia = segunda + datetime.timedelta(days=i)
            posicao_mensal = (dia.day - 1) // 7 + 1
            
            sql = 'SELECT id, texto, plain_text FROM calendario_semanal WHERE dia_semana = %s and (dia_mensal = 0 or dia_mensal = %s) and ativo = 1 UNION ALL ' % (i, posicao_mensal)
            sql += "select id, texto, plain_text from calendario_mensal where '%s' between inicio and fim UNION ALL " % dia.strftime(r"%Y-%m-%d")
            sql += "SELECT 0 as id, desc_longa as texto, plain_text FROM calendario_festa_dep_sede WHERE '%s' BETWEEN data_de AND date_ate UNION ALL " % dia.strftime(r"%Y-%m-%d")
            sql += "SELECT id_congregacao as id, 'Às <b class=\"text-danger\">' || replace(replace(horario, ':', 'h'), 'h00','h') || ',</b> Festa de Dep. <b class=\"text-decoration-underline\">' || congregacoes.descricao || CASE WHEN eventos_festa_dep.id_evento NOT IN (7, 8) THEN '</b>, Culto com participação do <b class=""text-decoration-underline"">' ELSE '</b> - <b>' END || eventos.descricao_curta || '</b>' as text, " \
                  "'Às ' || replace(replace(horario, ':', 'h'), 'h00','h') || ', Festa de Dep. ' || congregacoes.descricao || CASE WHEN eventos_festa_dep.id_evento NOT IN (7, 8) THEN ', Culto com participação do ' ELSE ' - ' END || eventos.descricao_curta as plain_text " \
                  r"FROM eventos_festa_dep INNER JOIN congregacoes ON congregacoes.id = eventos_festa_dep.id_congregacao INNER JOIN eventos on eventos.id = eventos_festa_dep.id_evento WHERE dia_semana_sqlite = strftime('%w', '" + dia.strftime(r"%Y-%m-%d") + "') "
            sql += "AND id_congregacao = (select id_congregacao from calendario_festa_dep where '%s' between inicio and fim) ORDER BY plain_text" % dia.strftime(r"%Y-%m-%d")

            info['dia'] = dia.strftime('%d')
            info['semana'] = semana[i]
            info['eventos'] = executarConsultaCalendario(sql)
            info['tipo'] = 'semanal'
            info['pos'] = cont + 2

            if len(info['eventos']) > 0:
                slides.append(info)
                cont += 1


        # pegar agora os eventos mensais
        mes = current_presentation['mes']
        ano = current_presentation['id']

        sql = "SELECT id, inicio, fim, 'isolado' as tipo, strftime('%w', inicio) as semana, strftime('%w', fim) as semana_fim FROM calendario_mensal WHERE strftime('%m', inicio) = '" + str(mes).zfill(2) + "' AND strftime('%Y', inicio) = '" + str(ano) + "' AND fim > date('now') group by(inicio) "
        sql += "UNION ALL SELECT 0 as id, min(data_de) as inicio, max(date_ate) as fim, 'dep_jan' as tipo, strftime('%w', data_de) as semana, strftime('%w', date_ate) as semana_fim FROM calendario_festa_dep_sede WHERE strftime('%m', data_de) = '" + str(mes).zfill(2) + "' "
        sql += "UNION ALL SELECT id_congregacao as id, inicio, fim, 'dep' as tipo, strftime('%w', inicio) as semana, strftime('%w', fim) as semana_fim FROM calendario_festa_dep WHERE strftime('%m', inicio) = '" + str(mes).zfill(2) + "' AND strftime('%Y', inicio) = '" + str(ano) + "' AND fim > date('now')  ORDER BY inicio"

        eventos_mensais = executarConsultaCalendario(sql)

        for evento in eventos_mensais:
            info = {}

            if evento['tipo'] == 'isolado':
                if evento['inicio'] == evento['fim']:
                    desc_dia = '<span class="text-dark fw-bold">%s (</span><span class="fw-bold text-primary">%s</span><span class="fw-bold text-dark">)</span>' % (evento['inicio'][8:], semana_sqlite[int(evento['semana'])])
                else:
                    desc_dia = '<span class="text-dark fw-bold">%s a %s (</span><span class="fw-bold text-primary">%s a %s</span><span class="fw-bold text-dark">)</span>' % (evento['inicio'][8:], evento['fim'][8:], semana_sqlite[int(evento['semana'])].replace('-feira', ''), semana_sqlite[int(evento['semana_fim'])].replace('-feira', ''))

                ls_aux = []
                for item in executarConsultaCalendario("SELECT texto FROM calendario_mensal where inicio = '%s' ORDER BY plain_text" % evento['inicio']):
                    ls_aux.append(item['texto'])

                info['tipo'] = evento['tipo']
                info['desc_dia'] = desc_dia
                info['eventos'] = ls_aux
                info['pos'] = cont + 2
                slides.append(info)

                cont += 1

            elif evento['tipo'] == 'dep':
                descricao = '<span class="fw-bold">RESUMO FESTA DE DEP. </span> - <span class="text-danger fw-bold">%s</span>' % executarConsultaCalendario('select descricao from congregacoes where id = %s' % evento['id'])[0]['descricao'].upper()

                ls_aux = []
                temp_segunda = datetime.datetime.strptime(evento['inicio'], r"%Y-%m-%d").date()
                temp_segunda = temp_segunda - datetime.timedelta(days=temp_segunda.weekday(), weeks=0)
                for item in executarConsultaCalendario(r"select dia_semana, strftime('%Hh%M', horario) as horario, " + "id_evento, eventos.descricao_curta as evento from eventos_festa_dep inner join eventos on eventos.id = eventos_festa_dep.id_evento where id_congregacao = %s order by dia_semana, horario" % evento['id']):
                    ls_aux.append("<b>%s (<span class='text-primary'>%s</span>)</b> - Às <b class='text-danger'>%s, </b> <b class='text-decoration-underline'>%s</b>" % (int(temp_segunda.strftime("%d")) + item['dia_semana'], semana[int(item['dia_semana'])].replace('-feira', ''), item['horario'], item['evento']))
                
                info['tipo'] = evento['tipo']
                info['desc_dia'] = descricao
                info['eventos'] = ls_aux
                info['pos'] = cont + 2
                slides.append(info)

                cont += 1

            elif evento['tipo'] == 'dep_jan' and not evento['inicio'] is None:
                descricao = '<span class="fw-bold">CONGRESSO UNIFICADO - </span><span class="text-danger fw-bold">IGREJA SEDE</span>'

                ls_aux = []
                eventos = executarConsultaCalendario(r'SELECT CASE WHEN data_de = date_ate THEN strftime("%d", data_de) ELSE strftime("%d", data_de) || " a " || strftime("%d", date_ate) END as dia, strftime("%w", data_de) as semana_inicio, strftime("%w", date_ate) as semana_fim, desc_curta as texto FROM calendario_festa_dep_sede ORDER BY data_de')

                for item in eventos:
                    dia_semana = semana_sqlite[int(item['semana_inicio'])].replace('-feira', '')
                    if item['semana_inicio'] != item['semana_fim']:
                        dia_semana = semana_sqlite[int(item['semana_inicio'])].replace('-feira', '') + ' a ' + semana_sqlite[int(item['semana_fim'])].replace('-feira', '')

                    ls_aux.append("<b>%s (<span class='text-primary'>%s</span>)</b> - %s" % (item['dia'], dia_semana, item['texto']))

                info['tipo'] = 'dep'
                info['desc_dia'] = descricao
                info['eventos'] = ls_aux
                info['pos'] = cont + 2
                slides.append(info)

                cont += 1              

        # após tudo isso criar uma lista tbm com as imagens presentes na tela de wallpaper para serem visualizadas
        path = os.path.dirname(os.path.realpath(__file__)) + '\\static\\images\\Wallpaper'

        onlyfiles = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

        for file in onlyfiles:
            slides.append({'url':file, 'tipo':'wallpaper', 'pos':cont + 2})        
            cont += 1


        return render_template('controlador_calendario.jinja', slides=slides, index=index, inicio='%s/%s' % (slides[0]['dia'], current_presentation['semana'][5:7]), fim='%s' % domingo.strftime(r"%d/%m/%Y"), ano=ano)

    
    elif estado == 7: #video_player

        return render_template('controlador_video.jinja')

    elif estado == 8: #EBD

        dados = []
        leitura = []
        licoes = pegarLicoes(datetime.datetime.now())

        data = licoes[int(current_presentation['id']) - 1]['dia'].strftime('%d/%m/%Y')

        dados = banco.executarConsulta('select * from licao_ebd where id = %s' % current_presentation['id'])[0]
        leitura = json.loads(dados['leitura_biblica'])

        total = 1

        for biblia in leitura:
            biblia['desc_livro'] = banco.executarConsulta('select descricao from livro_biblia where id = %s' % biblia['livro'])[0]['descricao']
            biblia['texto'] = banco.executarConsulta('select ver, texto from biblia_arc where livro = %s and cap = %s and ver BETWEEN %s and %s' % (biblia['livro'], biblia['cap'], biblia['ver1'], biblia['ver2']))

            total += len(biblia['texto'])

        return render_template('controlador_ebd.jinja', dados=dados, leitura=leitura, data=data, licao='%02d' % int(current_presentation['id']), index=index, total=total)

    elif estado == 9: # musical

        global ponteiro_musical

        query = '''SELECT
                    id_origem,
                    `tabela-origem`,
                    CASE WHEN capa_url IS NULL THEN 
                        CASE WHEN `tabela-origem` = 'musicas' THEN 'images/capas/' || capas.filename
                        WHEN `tabela-origem` = 'poesia' THEN '[SEM_CAPA_POESIA]'
                        ELSE '[SEM_CAPA_HARPA]' END
                    ELSE capa_url END as capa_url,
                    CASE WHEN `tabela-origem` = 'musicas' THEN musicas.titulo
                        WHEN `tabela-origem` = 'harpa' THEN harpa.descricao
                        WHEN `tabela-origem` = 'harpa_versionada' THEN (SELECT descricao FROM harpa WHERE id = (SELECT id_harpa FROM harpa_versionada WHERE id = id_origem)) 
                    END AS titulo
                FROM roteiro_musical
                LEFT JOIN musicas ON musicas.id = id_origem
                LEFT JOIN harpa ON harpa.id = id_origem
                LEFT JOIN capas ON capas.id_musica = musicas.id'''

        roteiro_musical = banco.executarConsulta(query)

        lista_final = []

        # adicionado capa principal
        capa_padrao = banco.executarConsulta("select valor from config where id = 'capa_musical'")[0]['valor']
        lista_final.append({'tipo':'capa_img', 'url':capa_padrao})

        item_atual = roteiro_musical[ponteiro_musical]


        # adicionando capa
        if item_atual['capa_url'] == '[SEM_CAPA_HARPA]':

            id_harpa = item_atual['id_origem']

            if item_atual['tabela-origem'] == 'harpa_versionada':
                id_harpa = banco.executarConsultaVetor('select id_harpa from harpa_versionada where id = %s' % id_harpa)[0]

            hostname = request.headers.get('Host')
            info = {'url':'http://%s/render_capa_harpa?id=%s' % (hostname, id_harpa), 'tipo':'capa'}

            try:
                with sync_playwright() as playwright:
                    capa = run_pdf_generation(playwright, info)
                    capa = base64.b64encode(capa).decode('utf-8')

            except Exception as e:
                print({"message": "Erro ao gerar Imagem", "error": str(e)}), 500             

            lista_final.append({'tipo':'capa_base64', 'url':capa})
            
        elif item_atual['capa_url'] == '[SEM_CAPA_POESIA]':

            hostname = request.headers.get('Host')
            info = {'url':'http://%s/render_capa_poesia?id=%s' % (hostname, item_atual['id_origem']), 'tipo':'capa'}


            try:
                with sync_playwright() as playwright:
                    capa = run_pdf_generation(playwright, info)
                    capa = base64.b64encode(capa).decode('utf-8')

            except Exception as e:
                print({"message": "Erro ao gerar Imagem", "error": str(e)}), 500             

            lista_final.append({'tipo':'capa_base64', 'url':capa})                

        else:
            lista_final.append({'tipo':'capa_img', 'url':item_atual['capa_url']})

        # adicionando slides
        if item_atual['tabela-origem'] == 'musicas':
            letras = banco.executarConsulta('select `text-slide`, categoria, ifnull(anotacao, "") as anotacao from slides where id_musica = %s' % item_atual['id_origem'])
            for sld in letras:
                lista_final.append({'tipo':'letra', 'cat':sld['categoria'], 'categoria':'cat-' + str(sld['categoria']) + '-musica', 'anotacao':sld['anotacao'], 'texto':sld['text-slide']})
        elif item_atual['tabela-origem'] == 'harpa_versionada':
            letras = banco.executarConsulta('select `text-slide`, categoria, ifnull(anotacao, "") as anotacao from slides_harpa_versionada where id_harpa_versionada = %s' % item_atual['id_origem'])
            for sld in letras:
                lista_final.append({'tipo':'letra', 'cat':sld['categoria'], 'categoria':'cat-' + str(sld['categoria']) + '-harpa', 'anotacao':sld['anotacao'], 'texto':sld['text-slide']})
        elif item_atual['tabela-origem'] == 'poesia':
            letras = banco.executarConsulta('select `text-slide`, ifnull(anotacao, "") as anotacao from slide_poesia where id_poesia = %s' % item_atual['id_origem'])
            for sld in letras:
                lista_final.append({'tipo':'letra', 'cat':'poesia', 'categoria':'cat-poesia', 'anotacao':sld['anotacao'], 'texto':sld['text-slide']})
        else:
            letras = banco.executarConsulta('select `text-slide`, categoria, ifnull(anotacao, "") as anotacao from slides_harpa where id_harpa = %s' % item_atual['id_origem'])
            for sld in letras:
                lista_final.append({'tipo':'letra', 'cat':sld['categoria'], 'categoria':'cat-' + str(sld['categoria']) + '-harpa', 'anotacao':sld['anotacao'], 'texto':sld['text-slide']})

        # adicionando capa inicial no final da música
        lista_final.append({'tipo':'capa_img', 'url':capa_padrao})

        
        # adicionando cores
        cores = banco.executarConsulta("SELECT (SELECT valor FROM config WHERE id = 'cor-harpa-fundo') as cor_harpa_fundo, (SELECT valor FROM config WHERE id = 'cor-harpa-letra') as cor_harpa_letra, (SELECT valor FROM config WHERE id = 'cor-harpa-num') as cor_harpa_num, (SELECT valor FROM config WHERE id = 'cor-harpa-red') as cor_harpa_red, (SELECT valor FROM config WHERE id = 'cor-musica-fundo') as cor_musica_fundo, (SELECT valor FROM config WHERE id = 'cor-musica-letra') as cor_musica_letra, (SELECT valor FROM config WHERE id = 'cor-musica-mark') as cor_musica_mark")[0]

        return render_template('controlador_musical.jinja', lista_final=lista_final, cores=cores, index=index, roteiro_musical=roteiro_musical, ponteiro_musical=ponteiro_musical)

    elif estado == 10: # poesia

        titulo = banco.executarConsulta('select titulo from poesia where id = %s' % current_presentation['id'])[0]['titulo']
        config = {'letra':banco.executarConsulta("select valor from config where id = 'cor-musica-letra'")[0]['valor'], 'fundo':banco.executarConsulta("select valor from config where id = 'cor-musica-fundo'")[0]['valor'], 'mark':banco.executarConsulta("select valor from config where id = 'cor-musica-mark'")[0]['valor']}
        lista_slides = banco.executarConsulta("select `text-slide`, ifnull(anotacao, '') as anotacao, pos from slide_poesia where id_poesia = %s order by pos" % current_presentation['id'])

        return render_template('controlador_poesia.jinja', lista_slides=lista_slides, index=index, config=config, titulo=titulo)
    
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

@app.route('/abrir_poesia', methods=['GET', 'POST'])
def abrir_poesia():

    poesias = banco.executarConsulta('select * from poesia order by titulo')


    return render_template('poesias.jinja', poesias=poesias)

@app.route('/abrir_musica', methods=['GET', 'POST'])
def abrir_musica():

    musicas = banco.executarConsulta('select id, titulo, (select group_concat(id_vinculo) from vinculos_x_musicas where id_musica = id) as vinc from musicas')
    musicas.sort(key=lambda t: (locale.strxfrm(t['titulo'])))
    categoria = banco.executarConsulta('select * from categoria_departamentos')
    config = {'letra':banco.executarConsulta("select valor from config where id = 'cor-musica-letra'")[0]['valor'], 'fundo':banco.executarConsulta("select valor from config where id = 'cor-musica-fundo'")[0]['valor'], 'mark':banco.executarConsulta("select valor from config where id = 'cor-musica-mark'")[0]['valor']}
    for item in categoria:
        item['subcategoria'] = banco.executarConsulta('select id, descricao from subcategoria_departamentos where supercategoria = %s' % item['id'])

    return render_template('musicas.jinja', musicas=musicas, status='', categoria=categoria, config=config)

@app.route('/abrir_harpa', methods=['GET', 'POST'])
def abrir_harpa():

    harpa = banco.executarConsulta('select * from harpa order by id')
    config = {'letra':banco.executarConsulta("select valor from config where id = 'cor-harpa-letra'")[0]['valor'], 'fundo':banco.executarConsulta("select valor from config where id = 'cor-harpa-fundo'")[0]['valor'], 'num':banco.executarConsulta("select valor from config where id = 'cor-harpa-num'")[0]['valor'], 'red':banco.executarConsulta("select valor from config where id = 'cor-harpa-red'")[0]['valor']}

    return render_template('harpa.jinja', status='', harpa=harpa, config=config)



@app.route('/calendario', methods=['GET', 'POST'])
def calendario():

    status = ''
    semana = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
    semana_sqlite = ['Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado']

    if request.method == 'POST':
        if 'calendario_semanal' in request.form:
            
            calendario = json.loads(request.form.getlist('calendario_semanal')[0]) 
            
            if inserir_calendario_semanal(calendario):
                status = '<div class="alert alert-success alert-dismissible fade show" role="alert"><strong>Operação concluída com sucesso!</strong> Calendário Semanal alterado!<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
            else:
                status = '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Erro fatal!</strong> Falha ao tentar inserir dados no banco.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'

        elif 'calendario_mensal' in request.form:

            calendario = json.loads(request.form.getlist('calendario_mensal')[0]) 

            mes = calendario[0]['data_inicial'][5:7]

            if inserir_calendario_mensal(calendario, mes):
                status = '<div class="alert alert-success alert-dismissible fade show" role="alert"><strong>Operação concluída com sucesso!</strong> Calendário Mensal atualizado com sucesso!<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
            else:
                status = '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Erro fatal!</strong> Falha ao tentar inserir dados no banco.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'


        elif 'festa_dep' in request.form:
            info = json.loads(request.form.getlist('festa_dep')[0])

            print(info)

            if inserirFestaDepCalendario(info):
                status = '<div class="alert alert-success alert-dismissible fade show" role="alert"><strong>Operação concluída com sucesso!</strong> Calendário da Festa de Dep. da Congregação atualizado com sucesso!<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
            else:
                status = '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Erro fatal!</strong> Falha ao tentar inserir dados no banco.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'                

        elif 'festa_dep_jan' in request.form:
            info = json.loads(request.form.getlist('festa_dep_jan')[0]) 

            if inserirFestaDepSedeCalendario(info):
                status = '<div class="alert alert-success alert-dismissible fade show" role="alert"><strong>Operação concluída com sucesso!</strong> Calendário da Festa de Dep. da Sede atualizado com sucesso!<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
            else:
                status = '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Erro fatal!</strong> Falha ao tentar inserir dados no banco.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'

        elif request.is_json:
            info = request.json

            if info['tipo'] == 0: # alterar atividade de evento semanal
                return jsonify({'result':alterarEventoAtivo(info['valor'], info['id_evento']), 'valor':info['valor']})

            elif info['tipo'] == 1: # alterar exibição do calendário semanal

                segunda_feira = datetime.datetime.strptime(info['segunda'], '%Y-%m-%d').date()
                            
                # montar calendário da semana
                calendario_semanal = []

                for i in range(0, 7):
                    dia = segunda_feira + datetime.timedelta(days=i)
                    posicao_mensal = (dia.day - 1) // 7 + 1
                    
                    sql = 'SELECT id, texto, plain_text, case when ativo = 1 then "checked" else "" end as checkbox, case when ativo = 0 then "disabled" else "" end as disabled FROM calendario_semanal WHERE dia_semana = %s and (dia_mensal = 0 or dia_mensal = %s) ' % (i, posicao_mensal)
                    sql += 'UNION ALL '
                    sql += "select id, texto, plain_text, 'checked disabled' as checkbox, '' as disabled from calendario_mensal where '%s' between inicio and fim " % dia.strftime('%Y-%m-%d')
                    sql += 'UNION ALL '
                    sql += "select 0 as id, desc_longa as texto, plain_text, 'checked disabled' as checkbox, '' as disabled from calendario_festa_dep_sede where '%s' between data_de and date_ate " % dia.strftime('%Y-%m-%d')
                    sql += 'UNION ALL '
                    sql += "SELECT id_congregacao as id, 'Às <b class=\"text-danger\">' || replace(replace(horario, ':', 'h'), 'h00','h') || ',</b> Festa de Dep. <b class=\"text-decoration-underline\">' || congregacoes.descricao || CASE WHEN eventos_festa_dep.id_evento NOT IN (7, 8) THEN '</b>, Culto com participação do <b class=""text-decoration-underline"">' ELSE '</b> - <b>' END || eventos.descricao_curta || '</b>' as texto, " \
                        "'Às ' || replace(replace(horario, ':', 'h'), 'h00','h') || ', Festa de Dep. ' || congregacoes.descricao || CASE WHEN eventos_festa_dep.id_evento NOT IN (7, 8) THEN ', Culto com participação do ' ELSE ' - ' END || eventos.descricao_curta as plain_text, " \
                        "'checked disabled' as checkbox, '' as disabled " \
                        r"FROM eventos_festa_dep INNER JOIN congregacoes ON congregacoes.id = eventos_festa_dep.id_congregacao INNER JOIN eventos on eventos.id = eventos_festa_dep.id_evento WHERE dia_semana_sqlite = strftime('%w', '" + dia.strftime(r"%Y-%m-%d") + "')"
                    sql += "AND id_congregacao = (select id_congregacao from calendario_festa_dep where '%s' between inicio and fim) ORDER BY plain_text" % dia.strftime(r"%Y-%m-%d")
                    
                    lista = executarConsultaCalendario(sql)
                    print(sql)

                    calendario_semanal.append({'dia':dia.strftime('%d'), 'desc':semana[i], 'eventos':lista, 'mes':dia.strftime('%m'), 'ano':dia.strftime('%Y')})

                    aux = [] # montar bloco para edição
                    new_list = executarConsultaCalendario('select texto, dia_mensal from calendario_semanal where dia_semana = %s order by dia_semana, dia_mensal, plain_text' % i)
                    modo = 0
                    for item in new_list:
                        aux.append({'type':'paragraph', 'data':{'text':item['texto']}})
                        if item['dia_mensal'] != 0:
                            modo = 1

                return jsonify(calendario_semanal)   

            elif info['tipo'] == 2: # alterar o bloco de edição dos eventos menais
                ls_aux = executarConsultaCalendario(r"SELECT id, inicio, fim, texto, strftime('%w', inicio) as semana, strftime('%w', fim) as semana_fim FROM calendario_mensal WHERE strftime('%m', inicio) = '" + ('%02d' % int(info['mes'])) + r"' AND strftime('%Y', inicio) = '" + info['ano'] + "' ORDER BY inicio, plain_text")
                dia_aux = ''
                ls_dias_aux = []
                paragrafo_aux = []   

                blocks_mem = []             

                # a lista deverá ser percorrida adicionando os eventos do mesmo dia numa lista para que fiquem juntos
                if len(ls_aux) > 0:
                    dia_aux = {'inicio':ls_aux[0]['inicio'], 'fim':ls_aux[0]['fim'], 'semana':ls_aux[0]['semana'], 'semana_fim':ls_aux[0]['semana_fim']}

                for item in ls_aux:
                    # montar lista para exibição na página inicial
                    if dia_aux['inicio'] == item['inicio']:
                        ls_dias_aux.append(item['texto'])
                        paragrafo_aux.append({'type':'paragraph', 'data':{'text':item['texto']}})
                    else:
                        if dia_aux['inicio'] == dia_aux['fim']:
                            desc_dia = '<span class="text-dark fw-bold">%s (</span><span class="fw-bold text-primary">%s</span><span class="fw-bold text-dark">)</span>' % (dia_aux['inicio'][8:], semana_sqlite[int(dia_aux['semana'])])
                        else:
                            desc_dia = '<span class="text-dark fw-bold">%s a %s (</span><span class="fw-bold text-primary">%s a %s</span><span class="fw-bold text-dark">)</span>' % (dia_aux['inicio'][8:], dia_aux['fim'][8:], semana_sqlite[int(dia_aux['semana'])].replace('-feira', ''), semana_sqlite[int(dia_aux['semana_fim'])].replace('-feira', ''))
                        
                        blocks_mem.append({'inicio':dia_aux['inicio'], 'fim':dia_aux['fim'], 'paragrafos':paragrafo_aux})

                        paragrafo_aux = [{'type':'paragraph', 'data':{'text':item['texto']}}]
                        ls_dias_aux = [item['texto']]
                        dia_aux = {'inicio':item['inicio'], 'fim':item['fim'], 'semana':item['semana'], 'semana_fim':item['semana_fim']}

                
                if len(ls_aux) > 0:
                    blocks_mem.append({'inicio':dia_aux['inicio'], 'fim':dia_aux['fim'], 'paragrafos':paragrafo_aux})   

                str_dia = info['ano'] + '-' + info['mes'] + '-1'
                primeiro_dia = datetime.datetime.strptime(str_dia , '%Y-%m-%d').date()
                ultimo_dia = primeiro_dia.replace(day=calendar.monthrange(primeiro_dia.year, primeiro_dia.month)[1])

                return jsonify({'blocos':blocks_mem, 'data-min':primeiro_dia.strftime('%Y-%m-%d'), 'data-max':ultimo_dia.strftime('%Y-%m-%d')})


            elif info['tipo'] == 3: # validação de senha
                senha = encriptar(info['senha'])

                if senha == banco.executarConsultaVetor("select valor from config where id = 'senha_adm'")[0]:
                    return jsonify(True)
                else:
                    return jsonify(False)
                
            elif info['tipo'] == 4: # alterar exibição do calendário mensal
                #ls_aux = executarConsultaCalendario(r"SELECT id, inicio, fim, texto, strftime('%w', inicio) as semana, strftime('%w', fim) as semana_fim FROM calendario_mensal WHERE strftime('%m', inicio) = '" + str(info['mes']).zfill(2) + r"' AND strftime('%Y', inicio) = '" + str(info['ano']) + "' ORDER BY inicio, plain_text")
                eventos_mensais = executarConsultaCalendario("SELECT id, inicio, fim, 'isolado' as tipo, strftime('%w', inicio) as semana, strftime('%w', fim) as semana_fim, CASE WHEN fim < DATE('now') THEN 'text-decoration-line-through disabled' ELSE '' END as risco  FROM calendario_mensal WHERE strftime('%m', inicio) = '" + str(info['mes']).zfill(2) + "' AND strftime('%Y', inicio) = '" + str(info['ano']) + "' group by(inicio) UNION ALL SELECT 0 as id, min(data_de) as inicio, max(date_ate) as fim, 'dep_jan' as tipo, strftime('%w', data_de) as semana, strftime('%w', date_ate) as semana_fim, CASE WHEN date_ate < DATE('now') THEN 'text-decoration-line-through disabled' ELSE '' END as risco FROM calendario_festa_dep_sede WHERE strftime('%m', data_de) = '" + str(info['mes']).zfill(2) + "' UNION ALL SELECT id_congregacao as id, inicio, fim, 'dep' as tipo, strftime('%w', inicio) as semana, strftime('%w', fim) as semana_fim, CASE WHEN fim < DATE('now') THEN 'text-decoration-line-through disabled' ELSE '' END as risco  FROM calendario_festa_dep WHERE strftime('%m', inicio) = '" + str(info['mes']).zfill(2) + "' AND strftime('%Y', inicio) = '" + str(info['ano']) + "' ORDER BY inicio")

                ls_final = []

                for evento in eventos_mensais:
                    if evento['tipo'] == 'isolado':
                        if evento['inicio'] == evento['fim']:
                            desc_dia = '<span class="text-dark fw-bold">%s (</span><span class="fw-bold text-primary">%s</span><span class="fw-bold text-dark">)</span>' % (evento['inicio'][8:], semana_sqlite[int(evento['semana'])])
                        else:
                            desc_dia = '<span class="text-dark fw-bold">%s a %s (</span><span class="fw-bold text-primary">%s a %s</span><span class="fw-bold text-dark">)</span>' % (evento['inicio'][8:], evento['fim'][8:], semana_sqlite[int(evento['semana'])].replace('-feira', ''), semana_sqlite[int(evento['semana_fim'])].replace('-feira', ''))

                        ls_aux = []
                        for item in executarConsultaCalendario("SELECT texto FROM calendario_mensal where inicio = '%s' ORDER BY plain_text" % evento['inicio']):
                            ls_aux.append(item['texto'])

                        ls_final.append({'descricao':desc_dia, 'eventos':ls_aux, 'risco':evento['risco']})

                    elif evento['tipo'] == 'dep':
                        descricao = '<span class="text-dark fw-bold">RESUMO FESTA DE DEP. </span> - <span class="text-danger fw-bold">%s</span>' % executarConsultaCalendario('select descricao from congregacoes where id = %s' % evento['id'])[0]['descricao'].upper()

                        ls_aux = []
                        temp_segunda = datetime.datetime.strptime(evento['inicio'], r"%Y-%m-%d").date()
                        temp_segunda = temp_segunda - datetime.timedelta(days=temp_segunda.weekday(), weeks=0)
                        for item in executarConsultaCalendario("select dia_semana, horario, id_evento, eventos.descricao_curta as evento from eventos_festa_dep inner join eventos on eventos.id = eventos_festa_dep.id_evento where id_congregacao = %s order by dia_semana, horario" % evento['id']):
                            ls_aux.append("<b>%s (<span class='text-primary'>%s</span>)</b> - Às <b class='text-danger'>%s, </b> <b class='text-decoration-underline'>%s</b>" % (int(temp_segunda.strftime("%d")) + item['dia_semana'], semana[int(item['dia_semana'])].replace('-feira', ''), item['horario'], item['evento']))

                        ls_final.append({'descricao':descricao, 'eventos':ls_aux, 'risco':evento['risco']})

                    elif evento['tipo'] == 'dep_jan' and not evento['inicio'] is None:
                        descricao = '<span class="text-dark fw-bold">CONGRESSO UNIFICADO - </span><span class="text-danger fw-bold">IGREJA SEDE</span>'

                        ls_aux = []

                        eventos = executarConsultaCalendario(r'SELECT CASE WHEN data_de = date_ate THEN strftime("%d", data_de) ELSE strftime("%d", data_de) || " a " || strftime("%d", date_ate) END as dia, strftime("%w", data_de) as semana_inicio, strftime("%w", date_ate) as semana_fim, desc_curta as texto FROM calendario_festa_dep_sede ORDER BY data_de')
                        for item in eventos:
                            dia_semana = semana_sqlite[int(item['semana_inicio'])].replace('-feira', '')
                            if item['semana_inicio'] != item['semana_fim']:
                                dia_semana = semana_sqlite[int(item['semana_inicio'])].replace('-feira', '') + ' a ' + semana_sqlite[int(item['semana_fim'])].replace('-feira', '')

                            ls_aux.append("<b>%s (<span class='text-primary'>%s</span>)</b> - %s" % (item['dia'], dia_semana, item['texto']))

                        ls_final.append({'descricao':descricao, 'eventos':ls_aux, 'risco':evento['risco']})

                
                return jsonify(ls_final)
            
            elif info['tipo'] == 5: # alterar exibição da tela de cadastro dos eventos de departamento

                detalhes_cong = executarConsultaCalendario('SELECT dia_semana, horario, id_evento FROM eventos_festa_dep WHERE id_congregacao = %s ORDER BY dia_semana, horario' % info['cong'])
                detalhes = executarConsultaCalendario('SELECT inicio, fim FROM calendario_festa_dep WHERE id_congregacao = %s' % info['cong'])


                return jsonify({'info':detalhes, 'detalhes_cong':detalhes_cong})


    
    # Obtém a data atual
    data_atual = datetime.datetime.now()

    # primeiro dia do mês
    mes_atual = data_atual.strftime('%Y-%m-') + '01'
    ultimo_dia = data_atual.replace(day=calendar.monthrange(data_atual.year, data_atual.month)[1])

    # Calcula a segunda-feira anterior
    segunda_feira_anterior = data_atual - datetime.timedelta(days=data_atual.weekday())


    meses = []
    mes_atual_desc = ''

    index = 1
    for mes in list(calendar.month_name)[1:]:
        meses.append({'desc':mes.title(), 'valor':index, 'atual':int(data_atual.strftime("%m")) == index})

        if int(data_atual.strftime("%m")) == index:
            mes_atual_desc = mes.title()

        index += 1

    # montar calendário da semana
    calendario_semanal = []
    blocks_sem = []

    for i in range(0, 7):
        dia = segunda_feira_anterior + datetime.timedelta(days=i)
        posicao_mensal = (dia.day - 1) // 7 + 1
        
        sql = 'SELECT id, texto, plain_text, case when ativo = 1 then "checked" else "" end as checkbox, case when ativo = 0 then "disabled" else "" end as disabled FROM calendario_semanal WHERE dia_semana = %s and (dia_mensal = 0 or dia_mensal = %s) ' % (i, posicao_mensal)
        sql += 'UNION ALL '
        sql += "select id, texto, plain_text, 'checked disabled' as checkbox, '' as disabled from calendario_mensal where '%s' between inicio and fim " % dia.strftime('%Y-%m-%d')
        sql += 'UNION ALL '
        sql += "select 0 as id, desc_longa as texto, plain_text, 'checked disabled' as checkbox, '' as disabled from calendario_festa_dep_sede where '%s' between data_de and date_ate " % dia.strftime('%Y-%m-%d')        
        sql += 'UNION ALL '
        sql += "SELECT id_congregacao as id, 'Às <b class=\"text-danger\">' || replace(replace(horario, ':', 'h'), 'h00','h') || ',</b> Festa de Dep. <b class=\"text-decoration-underline\">' || congregacoes.descricao || CASE WHEN eventos_festa_dep.id_evento NOT IN (7, 8) THEN '</b>, Culto com participação do <b class=""text-decoration-underline"">' ELSE '</b> - <b>' END || eventos.descricao_curta || '</b>' as texto, " \
               "'Às ' || replace(replace(horario, ':', 'h'), 'h00','h') || ', Festa de Dep. ' || congregacoes.descricao || CASE WHEN eventos_festa_dep.id_evento NOT IN (7, 8) THEN ', Culto com participação do ' ELSE ' - ' END || eventos.descricao_curta as plain_text, " \
               "'checked disabled' as checkbox, '' as disabled " \
               r"FROM eventos_festa_dep INNER JOIN congregacoes ON congregacoes.id = eventos_festa_dep.id_congregacao INNER JOIN eventos on eventos.id = eventos_festa_dep.id_evento WHERE dia_semana_sqlite = strftime('%w', '" + dia.strftime(r"%Y-%m-%d") + "')"
        sql += "AND id_congregacao = (select id_congregacao from calendario_festa_dep where '%s' between inicio and fim) ORDER BY plain_text" % dia.strftime(r"%Y-%m-%d")
        
        lista = executarConsultaCalendario(sql)

        calendario_semanal.append({'dia':dia.strftime('%d'), 'desc':semana[i], 'eventos':lista, 'mes':dia.strftime('%m'), 'ano':dia.strftime('%Y')})

        aux = [] # montar bloco para edição
        new_list = executarConsultaCalendario('select texto, dia_mensal from calendario_semanal where dia_semana = %s order by dia_semana, dia_mensal, plain_text' % i)
        modo = new_list[0]['dia_mensal']
        for item in new_list:
            aux.append({'type':'paragraph', 'data':{'text':item['texto']}})
            
            if modo != item['dia_mensal']:
                modo = 6


        blocks_sem.append({'paragrafos':aux, 'modo':modo})

    # montar calendário mensal
    calendario_mensal = []
    blocks_mem = []

    mes = data_atual.strftime('%m')

    # pegar todos os dias de eventos do calendário mensal
    eventos_mensais = executarConsultaCalendario("SELECT id, inicio, fim, 'isolado' as tipo, strftime('%w', inicio) as semana, strftime('%w', fim) as semana_fim, CASE WHEN fim < DATE('now') THEN 'text-decoration-line-through disabled' ELSE '' END as risco FROM calendario_mensal WHERE strftime('%m', inicio) = '" + mes + "' AND strftime('%Y', inicio) = '" + data_atual.strftime('%Y') + "' group by(inicio) UNION ALL SELECT 0 as id, min(data_de) as inicio, max(date_ate) as fim, 'dep_jan' as tipo, strftime('%w', data_de) as semana, strftime('%w', date_ate) as semana_fim, CASE WHEN date_ate < DATE('now') THEN 'text-decoration-line-through disabled' ELSE '' END as risco FROM calendario_festa_dep_sede WHERE strftime('%m', data_de) = '" + mes + "' UNION ALL SELECT id_congregacao as id, inicio, fim, 'dep' as tipo, strftime('%w', inicio) as semana, strftime('%w', fim) as semana_fim, CASE WHEN fim < DATE('now') THEN 'text-decoration-line-through disabled' ELSE '' END as risco  FROM calendario_festa_dep WHERE strftime('%m', inicio) = '" + mes + "' AND strftime('%Y', inicio) = '" + data_atual.strftime('%Y') + "' ORDER BY inicio")

    for evento in eventos_mensais:
        if evento['tipo'] == 'isolado':
            paragrafo_aux = []
            if evento['inicio'] == evento['fim']:
                desc_dia = '<span class="text-dark fw-bold">%s (</span><span class="fw-bold text-primary">%s</span><span class="fw-bold text-dark">)</span>' % (evento['inicio'][8:], semana_sqlite[int(evento['semana'])])
            else:
                desc_dia = '<span class="text-dark fw-bold">%s a %s (</span><span class="fw-bold text-primary">%s a %s</span><span class="fw-bold text-dark">)</span>' % (evento['inicio'][8:], evento['fim'][8:], semana_sqlite[int(evento['semana'])].replace('-feira', ''), semana_sqlite[int(evento['semana_fim'])].replace('-feira', ''))

            ls_aux = []
            for item in executarConsultaCalendario("SELECT texto FROM calendario_mensal where inicio = '%s' ORDER BY plain_text" % evento['inicio']):
                ls_aux.append(item['texto'])
                paragrafo_aux.append({'type':'paragraph', 'data':{'text':item['texto']}})

            calendario_mensal.append({'descricao':desc_dia, 'eventos':ls_aux, 'risco':evento['risco']})
            blocks_mem.append({'inicio':evento['inicio'], 'fim':evento['fim'], 'paragrafos':paragrafo_aux})
        elif evento['tipo'] == 'dep':
            descricao = '<span class="text-dark fw-bold">RESUMO FESTA DE DEP. </span> - <span class="text-danger fw-bold">%s</span>' % executarConsultaCalendario('select descricao from congregacoes where id = %s' % evento['id'])[0]['descricao'].upper()

            ls_aux = []
            temp_segunda = datetime.datetime.strptime(evento['inicio'], r"%Y-%m-%d").date()
            temp_segunda = temp_segunda - datetime.timedelta(days=temp_segunda.weekday(), weeks=0)            
            for item in executarConsultaCalendario("select dia_semana, horario, id_evento, eventos.descricao_curta as evento from eventos_festa_dep inner join eventos on eventos.id = eventos_festa_dep.id_evento where id_congregacao = %s order by dia_semana, horario" % evento['id']):
                ls_aux.append("<b>%s (<span class='text-primary'>%s</span>)</b> - Às <b class='text-danger'>%s, </b> <b class='text-decoration-underline'>%s</b>" % (int(temp_segunda.strftime("%d")) + item['dia_semana'], semana[int(item['dia_semana'])].replace('-feira', ''), item['horario'], item['evento']))

            calendario_mensal.append({'descricao':descricao, 'eventos':ls_aux, 'risco':evento['risco']})
        elif evento['tipo'] == 'dep_jan' and not evento['inicio'] is None:
            descricao = '<span class="text-dark fw-bold">CONGRESSO UNIFICADO - </span><span class="text-danger fw-bold">IGREJA SEDE</span>'

            ls_aux = []

            eventos = executarConsultaCalendario(r'SELECT CASE WHEN data_de = date_ate THEN strftime("%d", data_de) ELSE strftime("%d", data_de) || " a " || strftime("%d", date_ate) END as dia, strftime("%w", data_de) as semana_inicio, strftime("%w", date_ate) as semana_fim, desc_curta as texto FROM calendario_festa_dep_sede ORDER BY data_de')
            for item in eventos:
                dia_semana = semana_sqlite[int(item['semana_inicio'])].replace('-feira', '')
                if item['semana_inicio'] != item['semana_fim']:
                    dia_semana = semana_sqlite[int(item['semana_inicio'])].replace('-feira', '') + ' a ' + semana_sqlite[int(item['semana_fim'])].replace('-feira', '')

                ls_aux.append("<b>%s (<span class='text-primary'>%s</span>)</b> - %s" % (item['dia'], dia_semana, item['texto']))

            calendario_mensal.append({'descricao':descricao, 'eventos':ls_aux, 'risco':evento['risco']})


    # pegar as semanas disponíveis
    semanas_disponiveis = pegarListaSemanas(data_atual.strftime('%Y'), data_atual.strftime("%m"))

    # listar todas as congregações pro cadastro da Festa de Dep.
    congregacoes = executarConsultaCalendario('select * from congregacoes order by descricao')

    # listar os nomes dos eventos que ocorrem na Festa de Departamentos
    eventos = executarConsultaCalendario('select * from eventos order by descricao')

    # pegar lista completa do evento do primeiro registro (caso exista)
    detalhes_evento_primeira_cong = {}
    detalhes_evento_primeira_cong['info'] = executarConsultaCalendario('SELECT inicio, fim FROM calendario_festa_dep WHERE id_congregacao = %s' % congregacoes[0]['id'])
    detalhes_evento_primeira_cong['detalhes_cong'] = executarConsultaCalendario('SELECT dia_semana, horario, id_evento FROM eventos_festa_dep WHERE id_congregacao = %s ORDER BY dia_semana, horario' % congregacoes[0]['id'])

    # montar os dados da Festa de Dep. da Sede
    lista_festa_dep_sede = executarConsultaCalendario('SELECT * FROM calendario_festa_dep_sede ORDER BY data_de');

    return render_template('calendario.jinja', hoje_value=data_atual.strftime('%Y-%m-%d'), hoje=data_atual.strftime('%d/%m/%Y'), segunda_dia=segunda_feira_anterior.strftime('%d/%m'), semana=semana, status=status, calendario_semanal=calendario_semanal, calendario_mensal=calendario_mensal, blocks_sem=blocks_sem, meses=meses, mes_atual=mes_atual, ultimo_dia=ultimo_dia.strftime('%Y-%m-%d'), mes_atual_desc=mes_atual_desc, blocks_mem=blocks_mem, semanas_disponiveis=semanas_disponiveis, congregacoes=congregacoes, eventos=eventos, detalhes_evento_primeira_cong=detalhes_evento_primeira_cong, lista_festa_dep_sede=lista_festa_dep_sede)

@app.route('/musical', methods=['GET', 'POST'])
def musical():

    global pause_index
    global ponteiro_musical

    msg = ''

    if request.method == 'POST':
        if 'lista' in request.form:
            lista = json.loads(request.form['lista'])
            titulo = request.form['titulo']

            banco.insertOrUpdate({'id':"'titulo_musical'", 'valor':"'" + titulo + "'"}, 'id', 'config')

            if banco.inserirRoteiroMusical(lista):

                pause_index = 0
                ponteiro_musical = 0

                capa = banco.executarConsulta("select valor from config where id = 'capa_musical'")[0]['valor']

                roteiro_musical = banco.executarConsulta(r"SELECT id_origem, CASE WHEN `tabela-origem` = 'musicas' THEN 'item-musica' WHEN `tabela-origem` = 'harpa_versionada' THEN 'item-harpa-versionada' WHEN `tabela-origem` = 'poesia' THEN 'item-poesia' ELSE 'item-harpa' END as origem, CASE WHEN `tabela-origem` = 'musicas' THEN musicas.titulo WHEN `tabela-origem` = 'poesia' THEN poesia.titulo WHEN `tabela-origem` = 'harpa' THEN printf('%03d', harpa.id) || '. ' || harpa.descricao  ELSE printf('%03d', harpa_versionada.id_harpa) || '. ' || harpa_versionada.titulo_versao END AS titulo, CASE WHEN capa_url IS NULL THEN CASE WHEN `tabela-origem` = 'poesia' THEN '[SEM_CAPA_POESIA]' WHEN `tabela-origem` = 'musicas' THEN 'images/capas/' || capas.filename ELSE '[SEM_CAPA_HARPA]' END ELSE capa_url END as capa_url, CASE WHEN `tabela-origem` = 'harpa_versionada' THEN 'text-danger' ELSE '' END as color FROM roteiro_musical LEFT JOIN musicas ON musicas.id = id_origem LEFT JOIN poesia ON poesia.id = id_origem LEFT JOIN harpa ON harpa.id = id_origem LEFT JOIN harpa_versionada ON harpa_versionada.id = id_origem LEFT JOIN capas ON capas.id_musica = musicas.id")
                print(roteiro_musical)

                if len(roteiro_musical) < 1:
                    msg = '<div class="alert alert-warning alert-dismissible fade show" role="alert"><strong>Operação realizada com sucesso!</strong> Lista do Musical esvaziada com sucesso! Para prosseguir adicione músicas.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
                else:
                    for item in roteiro_musical:
                        if item['capa_url'] == '[SEM_CAPA_HARPA]':

                            id_harpa = item['id_origem']

                            if item['origem'] == 'item-harpa-versionada':
                                id_harpa = banco.executarConsultaVetor('select id_harpa from harpa_versionada where id = %s' % id_harpa)[0]

                            hostname = request.headers.get('Host')
                            info = {'url':'http://%s/render_capa_harpa?id=%s' % (hostname, id_harpa), 'tipo':'capa'}

                            try:
                                with sync_playwright() as playwright:
                                    capa = run_pdf_generation(playwright, info)
                                    capa = base64.b64encode(capa).decode('utf-8')

                            except Exception as e:
                                print({"message": "Erro ao gerar Imagem", "error": str(e)}), 500

                            item['capa_base64l'] = capa

                        elif item['capa_url'] == '[SEM_CAPA_POESIA]':

                            hostname = request.headers.get('Host')
                            info = {'url':'http://%s/render_capa_poesia?id=%s' % (hostname, item['id_origem']), 'tipo':'capa'}

                            try:
                                with sync_playwright() as playwright:
                                    capa = run_pdf_generation(playwright, info)
                                    capa = base64.b64encode(capa).decode('utf-8')

                            except Exception as e:
                                print({"message": "Erro ao gerar Imagem", "error": str(e)}), 500

                            item['capa_base64l'] = capa


                    return render_template('result_musical.jinja', capa=capa, roteiro_musical=roteiro_musical)
            else:
                msg = '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Atenção!</strong> Erro fatal ao tentar cadastrar dados!<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'

    roteiro_musical = banco.executarConsulta(r"SELECT id_origem, CASE WHEN `tabela-origem` = 'musicas' THEN 'item-musica' WHEN `tabela-origem` = 'poesia' THEN 'item-poesia' WHEN `tabela-origem` = 'harpa_versionada' THEN 'item-harpa-versionada' ELSE 'item-harpa' END as origem, CASE WHEN `tabela-origem` = 'poesia' THEN poesia.titulo WHEN `tabela-origem` = 'musicas' THEN musicas.titulo WHEN `tabela-origem` = 'harpa' THEN printf('%03d', harpa.id) || '. ' || harpa.descricao  ELSE printf('%03d', harpa_versionada.id_harpa) || '. ' || harpa_versionada.titulo_versao END AS titulo, CASE WHEN capa_url IS NULL THEN CASE WHEN `tabela-origem` = 'musicas' THEN 'images/capas/' || capas.filename ELSE '[SEM_CAPA_HARPA]' END ELSE capa_url END as capa_url, CASE WHEN `tabela-origem` = 'harpa_versionada' THEN 'text-danger' ELSE '' END as color FROM roteiro_musical LEFT JOIN poesia ON poesia.id = id_origem LEFT JOIN musicas ON musicas.id = id_origem LEFT JOIN harpa ON harpa.id = id_origem LEFT JOIN harpa_versionada ON harpa_versionada.id = id_origem LEFT JOIN capas ON capas.id_musica = musicas.id")
    lista_horizontal_roteiro = banco.executarConsulta("SELECT (SELECT group_concat(id_origem) from roteiro_musical where `tabela-origem` = 'harpa') as harpa, (SELECT group_concat(id_origem) from roteiro_musical where `tabela-origem` = 'musicas') as musicas, (SELECT group_concat(id_origem) from roteiro_musical where `tabela-origem` = 'harpa_versionada') as harpa_versionada, (SELECT group_concat(id_origem) from roteiro_musical where `tabela-origem` = 'poesia') as poesia")[0]
    
    where_harpa = ''
    if lista_horizontal_roteiro['harpa']:
        where_harpa = 'WHERE id NOT IN(%s)' % lista_horizontal_roteiro['harpa']

    where_harpa_versionada = ''
    if lista_horizontal_roteiro['harpa_versionada']:
        where_harpa_versionada = 'WHERE id NOT IN(%s)' % lista_horizontal_roteiro['harpa_versionada']        

    where_musica = ''
    if lista_horizontal_roteiro['musicas']:
        where_musica = 'WHERE id NOT IN(%s)' % lista_horizontal_roteiro['musicas']

    where_poesia = ''
    if lista_horizontal_roteiro['poesia']:
        where_poesia = 'WHERE id NOT IN(%s)' % lista_horizontal_roteiro['poesia']  
    
    harpa = banco.executarConsulta("select id as num, id, descricao, 'item-harpa' as classe, '' as color from harpa %s union all select id_harpa as num, id, titulo_versao, 'item-harpa-versionada' as classe, 'text-danger' as color from harpa_versionada %s order by num" % (where_harpa, where_harpa_versionada))
    musicas = banco.executarConsulta('select * from musicas %s' % where_musica)
    musicas.sort(key=lambda t: (locale.strxfrm(t['titulo'])))
    poesias = banco.executarConsulta('select * from poesia %s order by titulo' % where_poesia)

    titulo = banco.executarConsulta("select valor from config where id = 'titulo_musical'")[0]['valor']

    return render_template('musical.jinja', harpa=harpa, musicas=musicas, roteiro_musical=roteiro_musical, msg=msg, titulo=titulo, poesias=poesias)

@app.route('/licoesebd', methods=['GET', 'POST'])
def licoesebd():

    msg = ''

    hoje = datetime.datetime.now()

    trimestre = pegarTrimestre(hoje)

    capa = banco.executarConsulta("select valor from config where id = 'capa_ebd'")[0]['valor']

    now_txt = hoje.strftime('%d%m%Y%H%M%S')

    licoes = pegarLicoes(hoje)

    livros = banco.executarConsulta('select * from livro_biblia')


    if request.method == 'POST':

        if request.is_json:
            
            info = request.json
            
            if info['destino'] == 1: # pegar dados pro edit

                dados = banco.executarConsulta('select * from licao_ebd where id = %s' % info['id'])

                if len(dados) > 0:
                    dados_licao = dados[0]
                    lst_leitura = json.loads(dados_licao['leitura_biblica'])
                    dados_licao['leitura_biblica'] = dados_licao['leitura_biblica'].replace("'", '"')

                    for item in lst_leitura:
                        item['desc_livro'] = banco.executarConsulta('select descricao from livro_biblia where id = %s' % item['livro'])[0]['descricao']

                    return jsonify({'info':dados_licao, 'lst_leitura':lst_leitura})
                else:
                    return jsonify(False)
                
            elif info['destino'] == 2: # pegar dados view
                dados = banco.executarConsulta('select * from licao_ebd where id = %s' % info['id'])

                if len(dados) > 0:
                    dados_licao = dados[0]
                    leitura = json.loads(dados_licao['leitura_biblica'])

                    for biblia in leitura:
                        biblia['desc_livro'] = banco.executarConsulta('select descricao from livro_biblia where id = %s' % biblia['livro'])[0]['descricao']
                        biblia['texto'] = banco.executarConsulta('select ver, texto from biblia_arc where livro = %s and cap = %s and ver BETWEEN %s and %s' % (biblia['livro'], biblia['cap'], biblia['ver1'], biblia['ver2']))                    
                
                    return jsonify({'info':dados_licao, 'biblia':leitura})
                else:
                    return jsonify(False)
                

        if 'file' in request.files:
            isthisFile = request.files.get('file')
            basename, extension = os.path.splitext(isthisFile.filename)

            isthisFile.save('./static/images/EBD/capa' + extension)

            banco.insertOrUpdate({'id':"'capa_ebd'", 'valor':"'images/EBD/capa" + extension + "'"}, 'id', 'config')

            return jsonify('./static/images/EBD/capa' + extension + "?" + now_txt)
        
        if 'titulo' in request.form:
            info = {'id':request.form['licao'], 'titulo':"'" + request.form['titulo'] + "'", 'ref_texto_aureo':"'" + request.form['referencia'] + "'", 'texto_aureo':"'" + request.form['texto-aureo'] + "'", 'verdade_pratica':"'" + request.form['verdade_pratica'] + "'", 'leitura_biblica':"'" + request.form['leitura'] + "'"}
            print(request.form['leitura'])

            if banco.insertOrUpdate(info, 'id', 'licao_ebd'):
                msg = '<div class="alert alert-success alert-dismissible fade show" role="alert"><strong>Operação concluída!</strong> Informações da Lição de número <b>%02d</b> cadastradas com sucesso!<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>' % int(info['id'])
            else:
                msg = '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Atenção!</strong> Erro fatal ao tentar cadastrar dados!<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'

    
    # info da primeira lição pra ser exibida no canal de edição
    licao_1_edit = banco.executarConsulta('select * from licao_ebd where id = 1')[0]
    lst_leitura = json.loads(licao_1_edit['leitura_biblica'])
    licao_1_edit['leitura_biblica'] = licao_1_edit['leitura_biblica'].replace("'", '"')

    for item in lst_leitura:
        item['desc_livro'] = banco.executarConsulta('select descricao from livro_biblia where id = %s' % item['livro'])[0]['descricao']


    # info da lição ativa
    dados = []
    leitura = []

    for item in licoes:
        if item['selected'] == 'selected':
            dados = banco.executarConsulta('select * from licao_ebd where id = %s' % item['licao'])[0]
            leitura = json.loads(dados['leitura_biblica'])

            for biblia in leitura:
                biblia['desc_livro'] = banco.executarConsulta('select descricao from livro_biblia where id = %s' % biblia['livro'])[0]['descricao']
                biblia['texto'] = banco.executarConsulta('select ver, texto from biblia_arc where livro = %s and cap = %s and ver BETWEEN %s and %s' % (biblia['livro'], biblia['cap'], biblia['ver1'], biblia['ver2']))
                


    return render_template('ebd.jinja', trimestre=trimestre, capa=capa, now_txt=now_txt, licoes=licoes, livros=livros, msg=msg, licao_1_edit=licao_1_edit, lst_leitura=lst_leitura, dados=dados, leitura=leitura)


@app.route('/slide_new', methods=['GET', 'POST'])
def slide_new():
    global estado
    global current_presentation
    global index

    if estado == 0:
        consulta = banco.executarConsulta("SELECT segundos, arquivos FROM slide_show_wallpaper WHERE id = (SELECT valor FROM config WHERE id = 'wallpaper_show_id')")[0]
        imagens = eval(consulta['arquivos'])
        segundos = consulta['segundos']

        ls_final = []
        id = 0

        if len(imagens) > 1: # se for mais de uma imagem, definir a imagem inicial aleatoriamente
            for item in imagens:
                ls_final.append({'class':'hide', 'image':item})

            random_id = random.randint(0, len(imagens) - 1)
            ls_final[random_id]['class'] = 'in'
            id = random_id

        else:
            ls_final.append({'class':'in', 'image':imagens[0]})
        
        return render_template('PowerPoint_StandBy.jinja', fundo=ls_final, id=id, segundos=segundos, limite=len(imagens) - 1)
    elif estado == 1: # se iniciou uma apresentação de música

        # estabelecer configuração da música
        rows = banco.executarConsulta("SELECT id, valor FROM config")
        rows_dict = {row['id']: row['valor'] for row in rows}
        config = {'letra':rows_dict['cor-musica-letra'], 'fundo':rows_dict['cor-musica-fundo'], 'mark':rows_dict['cor-musica-mark'],  'num':rows_dict['cor-harpa-num'], 'red':rows_dict['cor-harpa-red']}

        if (current_presentation['tipo'] == 'musicas'):
            fundo = banco.executarConsulta('select filename from capas where id_musica = %s' % current_presentation['id'])

            if len(fundo) < 1:
                fundo = 'images/' + banco.executarConsulta("select valor from config where id = 'background'")[0]['valor']
            else:
                fundo = 'images/capas/' + fundo[0]['filename']

            lista_slides = banco.executarConsulta('select `text-slide`, categoria from slides where id_musica = %s order by pos' % current_presentation['id'])

            return render_template('PowerPoint_New.jinja', fundo=fundo, lista_slides=lista_slides, index=index, config=config)
    elif estado == 2: # iniciou uma apresentação da Bíblia

        livro = banco.executarConsultaVetor('select descricao from livro_biblia where id = %s' % current_presentation['id'])[0].replace('1', 'I').replace('2', 'II')
        head = {'nome':livro, 'cap':current_presentation['cap'], 'versao':current_presentation['versao'].replace('biblia_', '').upper()}

        lista = banco.executarConsultaVetor('select texto from %s where livro = %s and cap = %s order by ver' % (current_presentation['versao'], current_presentation['id'], current_presentation['cap']))

        config = {'letra':banco.executarConsulta("select valor from config where id = 'cor-biblia-letra'")[0]['valor'], 'fundo':banco.executarConsulta("select valor from config where id = 'cor-biblia-fundo'")[0]['valor'], 'seta':banco.executarConsulta("select valor from config where id = 'cor-biliba-arrow'")[0]['valor']}

        if (index + 1) > len(lista):
            index = len(lista) - 1        

        return render_template('PowerPoint_Biblia.jinja', head=head, lista=lista, index=index, versiculo=index + 1, config=config)
    elif estado == 3: #harpa
        rows = banco.executarConsulta("SELECT id, valor FROM config")
        rows_dict = {row['id']: row['valor'] for row in rows}
        config = {'letra':rows_dict['cor-harpa-letra'], 'fundo':rows_dict['cor-harpa-fundo'], 'num':rows_dict['cor-harpa-num'], 'red':rows_dict['cor-harpa-red'], 'mark':rows_dict['cor-musica-mark']}
        fundo = 'images/Harpa.jpg'
        info = banco.executarConsulta('select harpa.descricao as nome, autor_harpa.nome as autor from harpa inner join autor_harpa on autor_harpa.id = harpa.autor where harpa.id = %s' % current_presentation['id'])[0]

        lista_slides = banco.executarConsulta('select `text-slide`, categoria from slides_harpa where id_harpa = %s order by pos' % current_presentation['id'])
        numero = 'HINO %s' % '{0:03}'.format(int(current_presentation['id']))

        return render_template('PowerPoint_New.jinja', fundo=fundo, config=config, lista_slides=lista_slides, index=index, info=info, num=numero, titulo_versao='')

    elif estado == 4: # harpa versionada
        rows = banco.executarConsulta("SELECT id, valor FROM config")
        rows_dict = {row['id']: row['valor'] for row in rows}        
        config = {'letra':rows_dict['cor-harpa-letra'], 'fundo':rows_dict['cor-harpa-fundo'], 'num':rows_dict['cor-harpa-num'], 'red':rows_dict['cor-harpa-red'], 'mark':rows_dict['cor-musica-mark']}
        fundo = 'images/Harpa.jpg'
        info = banco.executarConsulta('select harpa.descricao as nome, autor_harpa.nome as autor from harpa inner join autor_harpa on autor_harpa.id = harpa.autor where harpa.id = (select id_harpa from harpa_versionada where id = %s)' % current_presentation['id'])[0]

        lista_slides = banco.executarConsulta('select `text-slide`, categoria from slides_harpa_versionada where id_harpa_versionada = %s order by pos' % current_presentation['id'])
        numero = 'HINO %s' % '{0:03}'.format(int(banco.executarConsultaVetor('select id_harpa from harpa_versionada where id = %s' % current_presentation['id'])[0]))
        titulo_versao = banco.executarConsultaVetor('select titulo_versao from harpa_versionada where id = %s' % current_presentation['id'])[0]

        return render_template('PowerPoint_New.jinja', fundo=fundo, config=config, lista_slides=lista_slides, index=index, info=info, num=numero, titulo_versao=titulo_versao)    
    elif estado == 5: # Arquivo pptx

        return render_template('PowerPoint_Verdadeiro.jinja', index=index, total=current_presentation['total'])
    
    elif estado == 6: # Calendário

        slides = []
        semana = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
        semana_sqlite = ['Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado']

        # começar a criar o vetor com as informações
        segunda = datetime.datetime.strptime(current_presentation['semana'], r"%Y-%m-%d").date()
        domingo = segunda + datetime.timedelta(days=6)
        
        cont = 0

        for i in range(7):
            info = {}

            dia = segunda + datetime.timedelta(days=i)
            posicao_mensal = (dia.day - 1) // 7 + 1
            
            sql = 'SELECT id, texto, plain_text FROM calendario_semanal WHERE dia_semana = %s and (dia_mensal = 0 or dia_mensal = %s) and ativo = 1 UNION ALL ' % (i, posicao_mensal)
            sql += "select id, texto, plain_text from calendario_mensal where '%s' between inicio and fim UNION ALL " % dia.strftime(r"%Y-%m-%d")
            sql += "SELECT 0 as id, desc_longa as texto, plain_text FROM calendario_festa_dep_sede WHERE '%s' BETWEEN data_de AND date_ate UNION ALL " % dia.strftime(r"%Y-%m-%d")
            sql += "SELECT id_congregacao as id, 'Às <b class=\"text-danger\">' || replace(replace(horario, ':', 'h'), 'h00','h') || ',</b> Festa de Dep. <b class=\"text-decoration-underline\">' || congregacoes.descricao || CASE WHEN eventos_festa_dep.id_evento NOT IN (7, 8) THEN '</b>, Culto com participação do <b class=""text-decoration-underline"">' ELSE '</b> - <b>' END || eventos.descricao_curta || '</b>' as text, " \
                  "'Às ' || replace(replace(horario, ':', 'h'), 'h00','h') || ', Festa de Dep. ' || congregacoes.descricao || CASE WHEN eventos_festa_dep.id_evento NOT IN (7, 8) THEN ', Culto com participação do ' ELSE ' - ' END || eventos.descricao_curta as plain_text " \
                  r"FROM eventos_festa_dep INNER JOIN congregacoes ON congregacoes.id = eventos_festa_dep.id_congregacao INNER JOIN eventos on eventos.id = eventos_festa_dep.id_evento WHERE dia_semana_sqlite = strftime('%w', '" + dia.strftime(r"%Y-%m-%d") + "') "
            sql += "AND id_congregacao = (select id_congregacao from calendario_festa_dep where '%s' between inicio and fim) ORDER BY plain_text" % dia.strftime(r"%Y-%m-%d")

            info['dia'] = dia.strftime('%d')
            info['semana'] = semana[i]
            info['eventos'] = executarConsultaCalendario(sql)
            info['tipo'] = 'semanal'
            info['pos'] = cont + 2

            if len(info['eventos']) > 0:
                slides.append(info)
                cont += 1


        # pegar agora os eventos mensais
        mes = current_presentation['mes']
        ano = current_presentation['id']

        mes_desc = calendar.month_name[int(mes)]

        sql = "SELECT id, inicio, fim, 'isolado' as tipo, strftime('%w', inicio) as semana, strftime('%w', fim) as semana_fim FROM calendario_mensal WHERE strftime('%m', inicio) = '" + str(mes).zfill(2) + "' AND strftime('%Y', inicio) = '" + str(ano) + "' AND fim > date('now') group by(inicio) "
        sql += "UNION ALL SELECT 0 as id, min(data_de) as inicio, max(date_ate) as fim, 'dep_jan' as tipo, strftime('%w', data_de) as semana, strftime('%w', date_ate) as semana_fim FROM calendario_festa_dep_sede WHERE strftime('%m', data_de) = '" + str(mes).zfill(2) + "' "
        sql += "UNION ALL SELECT id_congregacao as id, inicio, fim, 'dep' as tipo, strftime('%w', inicio) as semana, strftime('%w', fim) as semana_fim FROM calendario_festa_dep WHERE strftime('%m', inicio) = '" + str(mes).zfill(2) + "' AND strftime('%Y', inicio) = '" + str(ano) + "' AND fim > date('now')  ORDER BY inicio"

        eventos_mensais = executarConsultaCalendario(sql)

        for evento in eventos_mensais:
            info = {}

            if evento['tipo'] == 'isolado':
                if evento['inicio'] == evento['fim']:
                    desc_dia = '<span class="text-dark fw-bold">%s (</span><span class="fw-bold text-primary">%s</span><span class="fw-bold text-dark">)</span>' % (evento['inicio'][8:], semana_sqlite[int(evento['semana'])])
                else:
                    desc_dia = '<span class="text-dark fw-bold">%s a %s (</span><span class="fw-bold text-primary">%s a %s</span><span class="fw-bold text-dark">)</span>' % (evento['inicio'][8:], evento['fim'][8:], semana_sqlite[int(evento['semana'])].replace('-feira', ''), semana_sqlite[int(evento['semana_fim'])].replace('-feira', ''))

                ls_aux = []
                for item in executarConsultaCalendario("SELECT texto FROM calendario_mensal where inicio = '%s' ORDER BY plain_text" % evento['inicio']):
                    ls_aux.append(item['texto'])

                info['tipo'] = evento['tipo']
                info['desc_dia'] = desc_dia
                info['eventos'] = ls_aux
                info['pos'] = cont + 2
                slides.append(info)
                cont += 1

            elif evento['tipo'] == 'dep':
                descricao = '<span class="text-dark">RESUMO FESTA DE DEP. </span> - <span class="text-danger">%s</span>' % executarConsultaCalendario('select descricao from congregacoes where id = %s' % evento['id'])[0]['descricao'].upper()

                ls_aux = []
                temp_segunda = datetime.datetime.strptime(evento['inicio'], r"%Y-%m-%d").date()
                temp_segunda = temp_segunda - datetime.timedelta(days=temp_segunda.weekday(), weeks=0)
                for item in executarConsultaCalendario(r"select dia_semana, strftime('%Hh%M', horario) as horario, " + "id_evento, eventos.descricao_curta as evento from eventos_festa_dep inner join eventos on eventos.id = eventos_festa_dep.id_evento where id_congregacao = %s order by dia_semana, horario" % evento['id']):
                    ls_aux.append("<b>%s (<span class='text-primary'>%s</span>)</b> - Às <b class='text-danger'>%s, </b> <b class='text-decoration-underline'>%s</b>" % (int(temp_segunda.strftime("%d")) + item['dia_semana'], semana[int(item['dia_semana'])].replace('-feira', ''), item['horario'], item['evento']))
                
                info['tipo'] = evento['tipo']
                info['desc_dia'] = descricao
                info['eventos'] = ls_aux
                info['pos'] = cont + 2
                slides.append(info)
                cont += 1

            elif evento['tipo'] == 'dep_jan' and not evento['inicio'] is None:
                descricao = '<span class="fw-bold">CONGRESSO UNIFICADO - </span><span class="text-danger fw-bold">IGREJA SEDE</span>'

                ls_aux = []
                eventos = executarConsultaCalendario(r'SELECT CASE WHEN data_de = date_ate THEN strftime("%d", data_de) ELSE strftime("%d", data_de) || " a " || strftime("%d", date_ate) END as dia, strftime("%w", data_de) as semana_inicio, strftime("%w", date_ate) as semana_fim, desc_curta as texto FROM calendario_festa_dep_sede ORDER BY data_de')

                for item in eventos:
                    dia_semana = semana_sqlite[int(item['semana_inicio'])][0:3]
                    if item['semana_inicio'] != item['semana_fim']:
                        dia_semana = semana_sqlite[int(item['semana_inicio'])][0:3] + ' a ' + semana_sqlite[int(item['semana_fim'])][0:3]

                    ls_aux.append("<b>%s (<span class='text-primary'>%s</span>)</b> - %s" % (item['dia'], dia_semana, item['texto']))

                info['tipo'] = 'dep'
                info['desc_dia'] = descricao
                info['eventos'] = ls_aux
                info['pos'] = cont + 2
                slides.append(info)

                cont += 1  

        # após tudo isso criar uma lista tbm com as imagens presentes na tela de wallpaper para serem visualizadas
        path = os.path.dirname(os.path.realpath(__file__)) + '\\static\\images\\Wallpaper'

        onlyfiles = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

        for file in onlyfiles:
            slides.append({'url':file, 'tipo':'wallpaper', 'pos':cont + 2})
            cont += 1

        
        return render_template('PowerPoint_Calendar.jinja', slides=slides, index=index, inicio='%s/%s' % (slides[0]['dia'], current_presentation['semana'][5:7]), fim='%s' % domingo.strftime(r"%d/%m/%Y"), ano=ano, mes_desc=mes_desc)


    elif estado == 7:

        return render_template('video_player.jinja')
    
    elif estado == 8:

        dados = []
        leitura = []
        licoes = pegarLicoes(datetime.datetime.now())

        data = licoes[int(current_presentation['id']) - 1]['dia'].strftime('%d/%m/%Y')

        dados = banco.executarConsulta('select * from licao_ebd where id = %s' % current_presentation['id'])[0]
        capa = banco.executarConsulta("select valor from config where id = 'capa_ebd'")[0]['valor']
        leitura = json.loads(dados['leitura_biblica'])

        total = 1

        trimestre = pegarTrimestre(datetime.datetime.now())

        for biblia in leitura:
            biblia['desc_livro'] = banco.executarConsulta('select descricao from livro_biblia where id = %s' % biblia['livro'])[0]['descricao']
            biblia['texto'] = banco.executarConsulta('select ver, texto from biblia_arc where livro = %s and cap = %s and ver BETWEEN %s and %s' % (biblia['livro'], biblia['cap'], biblia['ver1'], biblia['ver2']))

            total += len(biblia['texto'])

        return render_template('PowerPoint_EBD.jinja', dados=dados, leitura=leitura, data=data, licao='%02d' % int(current_presentation['id']), index=index, total=total, trimestre=trimestre, capa=capa)

    elif estado == 9: # musical 
        global ponteiro_musical

        roteiro_musical = banco.executarConsulta(r"SELECT id_origem, `tabela-origem`, CASE WHEN capa_url IS NULL THEN CASE WHEN `tabela-origem` = 'poesia' THEN '[SEM_CAPA_POESIA]' WHEN `tabela-origem` = 'musicas' THEN 'images/capas/' || capas.filename ELSE '[SEM_CAPA_HARPA]' END ELSE capa_url END as capa_url FROM roteiro_musical LEFT JOIN musicas ON musicas.id = id_origem LEFT JOIN harpa ON harpa.id = id_origem LEFT JOIN capas ON capas.id_musica = musicas.id")

        # adicionado capa principal
        capa_padrao = banco.executarConsulta("select valor from config where id = 'capa_musical'")[0]['valor']

        # rodando o loop de cada música
        for item in roteiro_musical:
            item['lista_final'] = []
            item['lista_final'].append({'tipo':'capa_img', 'url':capa_padrao})
            # adicionando capa
            if item['capa_url'] == '[SEM_CAPA_HARPA]':

                id_harpa = item['id_origem']

                if item['tabela-origem'] == 'harpa_versionada':
                    id_harpa = banco.executarConsultaVetor('select id_harpa from harpa_versionada where id = %s' % id_harpa)[0]

                hostname = request.headers.get('Host')
                info = {'url':'http://%s/render_capa_harpa?id=%s' % (hostname, id_harpa), 'tipo':'capa'}

                try:
                    with sync_playwright() as playwright:
                        capa = run_pdf_generation(playwright, info)
                        capa = base64.b64encode(capa).decode('utf-8')

                except Exception as e:
                    print({"message": "Erro ao gerar Imagem", "error": str(e)}), 500

                item['lista_final'].append({'tipo':'capa_base64', 'url':capa})

            elif item['capa_url'] == '[SEM_CAPA_POESIA]':

                hostname = request.headers.get('Host')
                info = {'url':'http://%s/render_capa_poesia?id=%s' % (hostname, item['id_origem']), 'tipo':'capa'}


                try:
                    with sync_playwright() as playwright:
                        capa = run_pdf_generation(playwright, info)
                        capa = base64.b64encode(capa).decode('utf-8')

                except Exception as e:
                    print({"message": "Erro ao gerar Imagem", "error": str(e)}), 500

                item['lista_final'].append({'tipo':'capa_base64', 'url':capa})

            else:
                item['lista_final'].append({'tipo':'capa_img', 'url':item['capa_url']})

            # adicionando slides
            if item['tabela-origem'] == 'musicas':
                letras = banco.executarConsulta('select `text-slide`, categoria, ifnull(anotacao, "") as anotacao from slides where id_musica = %s' % item['id_origem'])
                for sld in letras:
                    item['lista_final'].append({'tipo':'letra', 'cat':sld['categoria'], 'categoria':'cat-' + str(sld['categoria']) + '-musica', 'anotacao':sld['anotacao'], 'texto':sld['text-slide']})
            elif item['tabela-origem'] == 'harpa_versionada':
                letras = banco.executarConsulta('select `text-slide`, categoria, ifnull(anotacao, "") as anotacao from slides_harpa_versionada where id_harpa_versionada = %s' % item['id_origem'])
                for sld in letras:
                    item['lista_final'].append({'tipo':'letra', 'cat':sld['categoria'], 'categoria':'cat-' + str(sld['categoria']) + '-harpa', 'anotacao':sld['anotacao'], 'texto':sld['text-slide']})            
            elif item['tabela-origem'] == 'poesia':
                letras = banco.executarConsulta('select `text-slide`, ifnull(anotacao, "") as anotacao from slide_poesia where id_poesia = %s' % item['id_origem'])
                for sld in letras:
                    item['lista_final'].append({'tipo':'letra', 'cat':'poesia', 'categoria':'cat-poesia', 'anotacao':sld['anotacao'], 'texto':sld['text-slide']})            
            else:
                letras = banco.executarConsulta('select `text-slide`, categoria, ifnull(anotacao, "") as anotacao from slides_harpa where id_harpa = %s' % item['id_origem'])
                for sld in letras:
                    item['lista_final'].append({'tipo':'letra', 'cat':sld['categoria'], 'categoria':'cat-' + str(sld['categoria']) + '-harpa', 'anotacao':sld['anotacao'], 'texto':sld['text-slide']})

            # adicionando capa inicial no final da música
            item['lista_final'].append({'tipo':'capa_img', 'url':capa_padrao})

        
        # adicionando cores
        cores = banco.executarConsulta("SELECT (SELECT valor FROM config WHERE id = 'cor-harpa-fundo') as cor_harpa_fundo, (SELECT valor FROM config WHERE id = 'cor-harpa-letra') as cor_harpa_letra, (SELECT valor FROM config WHERE id = 'cor-harpa-num') as cor_harpa_num, (SELECT valor FROM config WHERE id = 'cor-harpa-red') as cor_harpa_red, (SELECT valor FROM config WHERE id = 'cor-musica-fundo') as cor_musica_fundo, (SELECT valor FROM config WHERE id = 'cor-musica-letra') as cor_musica_letra, (SELECT valor FROM config WHERE id = 'cor-musica-mark') as cor_musica_mark")[0]

        print(roteiro_musical[0]['lista_final'][0]['tipo'])

        return render_template('PowerPoint_Musical.jinja', lista_final=roteiro_musical, cores=cores, index=index, ponteiro_musical=ponteiro_musical)

    elif estado == 10: # Poesia
        # estabelecer configuração da música
        fundo = 'images/Poesia_Background.jpg'
        config = {'letra':banco.executarConsulta("select valor from config where id = 'cor-musica-letra'")[0]['valor'], 'fundo':banco.executarConsulta("select valor from config where id = 'cor-musica-fundo'")[0]['valor'], 'mark':banco.executarConsulta("select valor from config where id = 'cor-musica-mark'")[0]['valor']}

        lista_slides = banco.executarConsulta('select `text-slide` from slide_poesia where id_poesia = %s order by pos' % current_presentation['id'])
        titulo = banco.executarConsultaVetor('select titulo from poesia where id = %s' % current_presentation['id'])[0]

        return render_template('PowerPoint_Poesia.jinja', lista_slides=lista_slides, index=index, config=config, fundo=fundo, titulo=titulo)    



@app.route('/slide', methods=['GET', 'POST'])
def slide():

    global estado
    global current_presentation
    global index

    if estado == 0:
        consulta = banco.executarConsulta("SELECT segundos, arquivos FROM slide_show_wallpaper WHERE id = (SELECT valor FROM config WHERE id = 'wallpaper_show_id')")[0]
        imagens = eval(consulta['arquivos'])
        segundos = consulta['segundos']

        ls_final = []
        id = 0

        if len(imagens) > 1: # se for mais de uma imagem, definir a imagem inicial aleatoriamente
            for item in imagens:
                ls_final.append({'class':'hide', 'image':item})

            random_id = random.randint(0, len(imagens) - 1)
            ls_final[random_id]['class'] = 'in'
            id = random_id

        else:
            ls_final.append({'class':'in', 'image':imagens[0]})
        
        return render_template('PowerPoint_StandBy.jinja', fundo=ls_final, id=id, segundos=segundos, limite=len(imagens) - 1)
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
    
    elif estado == 6: # Calendário

        slides = []
        semana = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
        semana_sqlite = ['Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado']

        # começar a criar o vetor com as informações
        segunda = datetime.datetime.strptime(current_presentation['semana'], r"%Y-%m-%d").date()
        domingo = segunda + datetime.timedelta(days=6)
        
        cont = 0

        for i in range(7):
            info = {}

            dia = segunda + datetime.timedelta(days=i)
            posicao_mensal = (dia.day - 1) // 7 + 1
            
            sql = 'SELECT id, texto, plain_text FROM calendario_semanal WHERE dia_semana = %s and (dia_mensal = 0 or dia_mensal = %s) and ativo = 1 UNION ALL ' % (i, posicao_mensal)
            sql += "select id, texto, plain_text from calendario_mensal where '%s' between inicio and fim UNION ALL " % dia.strftime(r"%Y-%m-%d")
            sql += "SELECT 0 as id, desc_longa as texto, plain_text FROM calendario_festa_dep_sede WHERE '%s' BETWEEN data_de AND date_ate UNION ALL " % dia.strftime(r"%Y-%m-%d")
            sql += "SELECT id_congregacao as id, 'Às <b class=\"text-danger\">' || replace(replace(horario, ':', 'h'), 'h00','h') || ',</b> Festa de Dep. <b class=\"text-decoration-underline\">' || congregacoes.descricao || CASE WHEN eventos_festa_dep.id_evento NOT IN (7, 8) THEN '</b>, Culto com participação do <b class=""text-decoration-underline"">' ELSE '</b> - <b>' END || eventos.descricao_curta || '</b>' as text, " \
                  "'Às ' || replace(replace(horario, ':', 'h'), 'h00','h') || ', Festa de Dep. ' || congregacoes.descricao || CASE WHEN eventos_festa_dep.id_evento NOT IN (7, 8) THEN ', Culto com participação do ' ELSE ' - ' END || eventos.descricao_curta as plain_text " \
                  r"FROM eventos_festa_dep INNER JOIN congregacoes ON congregacoes.id = eventos_festa_dep.id_congregacao INNER JOIN eventos on eventos.id = eventos_festa_dep.id_evento WHERE dia_semana_sqlite = strftime('%w', '" + dia.strftime(r"%Y-%m-%d") + "') "
            sql += "AND id_congregacao = (select id_congregacao from calendario_festa_dep where '%s' between inicio and fim) ORDER BY plain_text" % dia.strftime(r"%Y-%m-%d")

            info['dia'] = dia.strftime('%d')
            info['semana'] = semana[i]
            info['eventos'] = executarConsultaCalendario(sql)
            info['tipo'] = 'semanal'
            info['pos'] = cont + 2

            if len(info['eventos']) > 0:
                slides.append(info)
                cont += 1


        # pegar agora os eventos mensais
        mes = current_presentation['mes']
        ano = current_presentation['id']

        mes_desc = calendar.month_name[int(mes)]

        sql = "SELECT id, inicio, fim, 'isolado' as tipo, strftime('%w', inicio) as semana, strftime('%w', fim) as semana_fim FROM calendario_mensal WHERE strftime('%m', inicio) = '" + str(mes).zfill(2) + "' AND strftime('%Y', inicio) = '" + str(ano) + "' AND fim > date('now') group by(inicio) "
        sql += "UNION ALL SELECT 0 as id, min(data_de) as inicio, max(date_ate) as fim, 'dep_jan' as tipo, strftime('%w', data_de) as semana, strftime('%w', date_ate) as semana_fim FROM calendario_festa_dep_sede WHERE strftime('%m', data_de) = '" + str(mes).zfill(2) + "' "
        sql += "UNION ALL SELECT id_congregacao as id, inicio, fim, 'dep' as tipo, strftime('%w', inicio) as semana, strftime('%w', fim) as semana_fim FROM calendario_festa_dep WHERE strftime('%m', inicio) = '" + str(mes).zfill(2) + "' AND strftime('%Y', inicio) = '" + str(ano) + "' AND fim > date('now')  ORDER BY inicio"

        eventos_mensais = executarConsultaCalendario(sql)

        for evento in eventos_mensais:
            info = {}

            if evento['tipo'] == 'isolado':
                if evento['inicio'] == evento['fim']:
                    desc_dia = '<span class="text-dark fw-bold">%s (</span><span class="fw-bold text-primary">%s</span><span class="fw-bold text-dark">)</span>' % (evento['inicio'][8:], semana_sqlite[int(evento['semana'])])
                else:
                    desc_dia = '<span class="text-dark fw-bold">%s a %s (</span><span class="fw-bold text-primary">%s a %s</span><span class="fw-bold text-dark">)</span>' % (evento['inicio'][8:], evento['fim'][8:], semana_sqlite[int(evento['semana'])].replace('-feira', ''), semana_sqlite[int(evento['semana_fim'])].replace('-feira', ''))

                ls_aux = []
                for item in executarConsultaCalendario("SELECT texto FROM calendario_mensal where inicio = '%s' ORDER BY plain_text" % evento['inicio']):
                    ls_aux.append(item['texto'])

                info['tipo'] = evento['tipo']
                info['desc_dia'] = desc_dia
                info['eventos'] = ls_aux
                info['pos'] = cont + 2
                slides.append(info)
                cont += 1

            elif evento['tipo'] == 'dep':
                descricao = '<span class="text-dark">RESUMO FESTA DE DEP. </span> - <span class="text-danger">%s</span>' % executarConsultaCalendario('select descricao from congregacoes where id = %s' % evento['id'])[0]['descricao'].upper()

                ls_aux = []
                temp_segunda = datetime.datetime.strptime(evento['inicio'], r"%Y-%m-%d").date()
                temp_segunda = temp_segunda - datetime.timedelta(days=temp_segunda.weekday(), weeks=0)
                for item in executarConsultaCalendario(r"select dia_semana, strftime('%Hh%M', horario) as horario, " + "id_evento, eventos.descricao_curta as evento from eventos_festa_dep inner join eventos on eventos.id = eventos_festa_dep.id_evento where id_congregacao = %s order by dia_semana, horario" % evento['id']):
                    ls_aux.append("<b>%s (<span class='text-primary'>%s</span>)</b> - Às <b class='text-danger'>%s, </b> <b class='text-decoration-underline'>%s</b>" % (int(temp_segunda.strftime("%d")) + item['dia_semana'], semana[int(item['dia_semana'])].replace('-feira', ''), item['horario'], item['evento']))
                
                info['tipo'] = evento['tipo']
                info['desc_dia'] = descricao
                info['eventos'] = ls_aux
                info['pos'] = cont + 2
                slides.append(info)
                cont += 1

            elif evento['tipo'] == 'dep_jan' and not evento['inicio'] is None:
                descricao = '<span class="fw-bold">CONGRESSO UNIFICADO - </span><span class="text-danger fw-bold">IGREJA SEDE</span>'

                ls_aux = []
                eventos = executarConsultaCalendario(r'SELECT CASE WHEN data_de = date_ate THEN strftime("%d", data_de) ELSE strftime("%d", data_de) || " a " || strftime("%d", date_ate) END as dia, strftime("%w", data_de) as semana_inicio, strftime("%w", date_ate) as semana_fim, desc_curta as texto FROM calendario_festa_dep_sede ORDER BY data_de')

                for item in eventos:
                    dia_semana = semana_sqlite[int(item['semana_inicio'])][0:3]
                    if item['semana_inicio'] != item['semana_fim']:
                        dia_semana = semana_sqlite[int(item['semana_inicio'])][0:3] + ' a ' + semana_sqlite[int(item['semana_fim'])][0:3]

                    ls_aux.append("<b>%s (<span class='text-primary'>%s</span>)</b> - %s" % (item['dia'], dia_semana, item['texto']))

                info['tipo'] = 'dep'
                info['desc_dia'] = descricao
                info['eventos'] = ls_aux
                info['pos'] = cont + 2
                slides.append(info)

                cont += 1  

        # após tudo isso criar uma lista tbm com as imagens presentes na tela de wallpaper para serem visualizadas
        path = os.path.dirname(os.path.realpath(__file__)) + '\\static\\images\\Wallpaper'

        onlyfiles = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

        for file in onlyfiles:
            slides.append({'url':file, 'tipo':'wallpaper', 'pos':cont + 2})
            cont += 1

        
        return render_template('PowerPoint_Calendar.jinja', slides=slides, index=index, inicio='%s/%s' % (slides[0]['dia'], current_presentation['semana'][5:7]), fim='%s' % domingo.strftime(r"%d/%m/%Y"), ano=ano, mes_desc=mes_desc)


    elif estado == 7:

        return render_template('video_player.jinja')
    
    elif estado == 8:

        dados = []
        leitura = []
        licoes = pegarLicoes(datetime.datetime.now())

        data = licoes[int(current_presentation['id']) - 1]['dia'].strftime('%d/%m/%Y')

        dados = banco.executarConsulta('select * from licao_ebd where id = %s' % current_presentation['id'])[0]
        capa = banco.executarConsulta("select valor from config where id = 'capa_ebd'")[0]['valor']
        leitura = json.loads(dados['leitura_biblica'])

        total = 1

        trimestre = pegarTrimestre(datetime.datetime.now())

        for biblia in leitura:
            biblia['desc_livro'] = banco.executarConsulta('select descricao from livro_biblia where id = %s' % biblia['livro'])[0]['descricao']
            biblia['texto'] = banco.executarConsulta('select ver, texto from biblia_arc where livro = %s and cap = %s and ver BETWEEN %s and %s' % (biblia['livro'], biblia['cap'], biblia['ver1'], biblia['ver2']))

            total += len(biblia['texto'])

        return render_template('PowerPoint_EBD.jinja', dados=dados, leitura=leitura, data=data, licao='%02d' % int(current_presentation['id']), index=index, total=total, trimestre=trimestre, capa=capa)

    elif estado == 9: # musical 
        global ponteiro_musical

        roteiro_musical = banco.executarConsulta(r"SELECT id_origem, `tabela-origem`, CASE WHEN capa_url IS NULL THEN CASE WHEN `tabela-origem` = 'poesia' THEN '[SEM_CAPA_POESIA]' WHEN `tabela-origem` = 'musicas' THEN 'images/capas/' || capas.filename ELSE '[SEM_CAPA_HARPA]' END ELSE capa_url END as capa_url FROM roteiro_musical LEFT JOIN musicas ON musicas.id = id_origem LEFT JOIN harpa ON harpa.id = id_origem LEFT JOIN capas ON capas.id_musica = musicas.id")

        # adicionado capa principal
        capa_padrao = banco.executarConsulta("select valor from config where id = 'capa_musical'")[0]['valor']

        # rodando o loop de cada música
        for item in roteiro_musical:
            item['lista_final'] = []
            item['lista_final'].append({'tipo':'capa_img', 'url':capa_padrao})
            # adicionando capa
            if item['capa_url'] == '[SEM_CAPA_HARPA]':

                id_harpa = item['id_origem']

                if item['tabela-origem'] == 'harpa_versionada':
                    id_harpa = banco.executarConsultaVetor('select id_harpa from harpa_versionada where id = %s' % id_harpa)[0]

                hostname = request.headers.get('Host')
                info = {'url':'http://%s/render_capa_harpa?id=%s' % (hostname, id_harpa), 'tipo':'capa'}

                try:
                    with sync_playwright() as playwright:
                        capa = run_pdf_generation(playwright, info)
                        capa = base64.b64encode(capa).decode('utf-8')

                except Exception as e:
                    print({"message": "Erro ao gerar Imagem", "error": str(e)}), 500

                item['lista_final'].append({'tipo':'capa_base64', 'url':capa})

            elif item['capa_url'] == '[SEM_CAPA_POESIA]':

                hostname = request.headers.get('Host')
                info = {'url':'http://%s/render_capa_poesia?id=%s' % (hostname, item['id_origem']), 'tipo':'capa'}


                try:
                    with sync_playwright() as playwright:
                        capa = run_pdf_generation(playwright, info)
                        capa = base64.b64encode(capa).decode('utf-8')

                except Exception as e:
                    print({"message": "Erro ao gerar Imagem", "error": str(e)}), 500

                item['lista_final'].append({'tipo':'capa_base64', 'url':capa})

            else:
                item['lista_final'].append({'tipo':'capa_img', 'url':item['capa_url']})

            # adicionando slides
            if item['tabela-origem'] == 'musicas':
                letras = banco.executarConsulta('select `text-slide`, categoria, ifnull(anotacao, "") as anotacao from slides where id_musica = %s' % item['id_origem'])
                for sld in letras:
                    item['lista_final'].append({'tipo':'letra', 'cat':sld['categoria'], 'categoria':'cat-' + str(sld['categoria']) + '-musica', 'anotacao':sld['anotacao'], 'texto':sld['text-slide']})
            elif item['tabela-origem'] == 'harpa_versionada':
                letras = banco.executarConsulta('select `text-slide`, categoria, ifnull(anotacao, "") as anotacao from slides_harpa_versionada where id_harpa_versionada = %s' % item['id_origem'])
                for sld in letras:
                    item['lista_final'].append({'tipo':'letra', 'cat':sld['categoria'], 'categoria':'cat-' + str(sld['categoria']) + '-harpa', 'anotacao':sld['anotacao'], 'texto':sld['text-slide']})            
            elif item['tabela-origem'] == 'poesia':
                letras = banco.executarConsulta('select `text-slide`, ifnull(anotacao, "") as anotacao from slide_poesia where id_poesia = %s' % item['id_origem'])
                for sld in letras:
                    item['lista_final'].append({'tipo':'letra', 'cat':'poesia', 'categoria':'cat-poesia', 'anotacao':sld['anotacao'], 'texto':sld['text-slide']})            
            else:
                letras = banco.executarConsulta('select `text-slide`, categoria, ifnull(anotacao, "") as anotacao from slides_harpa where id_harpa = %s' % item['id_origem'])
                for sld in letras:
                    item['lista_final'].append({'tipo':'letra', 'cat':sld['categoria'], 'categoria':'cat-' + str(sld['categoria']) + '-harpa', 'anotacao':sld['anotacao'], 'texto':sld['text-slide']})

            # adicionando capa inicial no final da música
            item['lista_final'].append({'tipo':'capa_img', 'url':capa_padrao})

        
        # adicionando cores
        cores = banco.executarConsulta("SELECT (SELECT valor FROM config WHERE id = 'cor-harpa-fundo') as cor_harpa_fundo, (SELECT valor FROM config WHERE id = 'cor-harpa-letra') as cor_harpa_letra, (SELECT valor FROM config WHERE id = 'cor-harpa-num') as cor_harpa_num, (SELECT valor FROM config WHERE id = 'cor-harpa-red') as cor_harpa_red, (SELECT valor FROM config WHERE id = 'cor-musica-fundo') as cor_musica_fundo, (SELECT valor FROM config WHERE id = 'cor-musica-letra') as cor_musica_letra, (SELECT valor FROM config WHERE id = 'cor-musica-mark') as cor_musica_mark")[0]

        print(roteiro_musical[0]['lista_final'][0]['tipo'])

        return render_template('PowerPoint_Musical.jinja', lista_final=roteiro_musical, cores=cores, index=index, ponteiro_musical=ponteiro_musical)

    elif estado == 10: # Poesia
        # estabelecer configuração da música
        fundo = 'images/Poesia_Background.jpg'
        config = {'letra':banco.executarConsulta("select valor from config where id = 'cor-musica-letra'")[0]['valor'], 'fundo':banco.executarConsulta("select valor from config where id = 'cor-musica-fundo'")[0]['valor'], 'mark':banco.executarConsulta("select valor from config where id = 'cor-musica-mark'")[0]['valor']}

        lista_slides = banco.executarConsulta('select `text-slide` from slide_poesia where id_poesia = %s order by pos' % current_presentation['id'])
        titulo = banco.executarConsultaVetor('select titulo from poesia where id = %s' % current_presentation['id'])[0]

        return render_template('PowerPoint_Poesia.jinja', lista_slides=lista_slides, index=index, config=config, fundo=fundo, titulo=titulo)

@app.route('/updateSlide', methods=['GET', 'POST'])
def updateSlide():
    if request.method == 'POST':

        if request.is_json: # application/json
            # handle your ajax request here!

    
            global index
            global ponteiro_musical

            index = int(request.json)

            if estado == 9:
                socketio.emit('update', {'index':index, 'ponteiro':ponteiro_musical})
            else:
                socketio.emit('update', index)
          
            return jsonify(True)


@app.route('/videoplayer_command', methods=['GET', 'POST'])
def videoplayer_command():
    if request.method == 'POST':

        if request.is_json: # application/json
            # handle your ajax request here!

            info = request.json
            socketio.emit('video_command', info['command'])

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

@app.route('/addPoesia', methods=['GET', 'POST'])
def addPoesia():
    if request.method == 'POST':   
        info = json.loads(request.form.getlist('json_send')[0])

        if info['destino'] == '0':
            # inserir poesia
            if banco.inserirNovaPoesia(info):
                status= '<div class="alert alert-success alert-dismissible fade show" role="alert"><strong>Operação concluída com sucesso!</strong> Poesia <strong>' + info['titulo'] + '</strong> cadastrada com sucesso!.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
            else:
                status= '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Erro falta!</strong> Falha ao tentar inserir slides e letra no Banco, favor verificar o problema.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
        else: # alterar a poesia e não inserir
            if banco.alterarPoesia(info):
                status= '<div class="alert alert-success alert-dismissible fade show" role="alert"><strong>Operação concluída com sucesso!</strong> Poesia <strong>' + info['titulo'] + '</strong> alterada com sucesso!.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
            else:
                status= '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Erro falta!</strong> Falha ao tentar inserir slides e letra no Banco, favor verificar o problema.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'                
        
        poesias = banco.executarConsulta('select * from poesia order by titulo')

        return render_template('poesias.jinja', poesias=poesias, status=status)
    

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
            capa = result['capa']
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

        if len(lista[index]) < 199:
            tamanho = 20
        elif len(lista[index]) < 499:
            tamanho = 30
        else:
            tamanho = 60

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

    elif (estado == 9): # Musical
        global ponteiro_musical

        lista = banco.executarConsulta(r"SELECT id_origem, `tabela-origem`, CASE WHEN capa_url IS NULL THEN CASE WHEN `tabela-origem` = 'musicas' THEN 'images/capas/' || capas.filename ELSE '[SEM_CAPA_HARPA]' END ELSE capa_url END as capa_url FROM roteiro_musical LEFT JOIN musicas ON musicas.id = id_origem LEFT JOIN harpa ON harpa.id = id_origem LEFT JOIN capas ON capas.id_musica = musicas.id")
        titulo = banco.executarConsulta('select valor from config where id = "titulo_musical"')[0]['valor']
        tamanho = 20

        for slide in lista:
            slide['lista'] = [titulo]
            if slide['tabela-origem'] == 'harpa':
                slide['lista'].append(banco.executarConsulta('select descricao from harpa where id = %s' % slide['id_origem'])[0]['descricao'])

                for item in banco.executarConsulta('select `text-legenda` from slides_harpa where id_harpa = %s' % slide['id_origem']):
                    slide['lista'].append(item['text-legenda'])
                
                slide['lista'].append('')

            elif slide['tabela-origem'] == 'musicas':
                slide['lista'].append(banco.executarConsulta('select titulo from musicas where id = %s' % slide['id_origem'])[0]['titulo'])

                for item in banco.executarConsulta('select `text-legenda` from slides where id_musica = %s' % slide['id_origem']):
                    slide['lista'].append(item['text-legenda'])
                
                slide['lista'].append('')

            elif slide['tabela-origem'] == 'harpa_versionada':
                slide['lista'].append(banco.executarConsulta('select id_harpa, harpa.descricao as titulo from harpa_versionada inner join harpa on harpa.id = harpa_versionada.id_harpa where harpa_versionada.id = %s' % slide['id_origem'])[0]['titulo'])
                
                for item in banco.executarConsulta('select `text-legenda` from slides_harpa_versionada where id_harpa_versionada = %s' % slide['id_origem']):
                    slide['lista'].append(item['text-legenda'])
                
                slide['lista'].append('')

            elif slide['tabela-origem'] == 'poesia':
                slide['lista'].append(banco.executarConsulta('select titulo from poesia where id = %s' % slide['id_origem'])[0]['titulo'])
                
                for item in banco.executarConsulta('select `text-legenda` from slide_poesia where id_poesia = %s' % slide['id_origem']):
                    slide['lista'].append(item['text-legenda'])
                
                slide['lista'].append('')

        return render_template('subtitle_musical.jinja', legenda=lista, index=index, tamanho=tamanho, head=head, estado=estado, align=align, ponteiro_musical=ponteiro_musical)

    elif (estado == 10): # poesia
        legenda = banco.executarConsulta('select `text-legenda` from slide_poesia where id_poesia = %s order by pos' % current_presentation['id'])
        lista = [banco.executarConsulta('select titulo from poesia where id = %s' % current_presentation['id'])[0]['titulo']]
        for item in legenda:
            lista.append(item['text-legenda'])

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

@app.route('/edit_poesia', methods=['GET', 'POST'])
def edit_poesia():

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
            

        # recriar lista pro editor
        for item in lista_texto:
            blocks.append({'type':'paragraph', 'data':{'text':item['text-slide']}})
            blocks_s.append({'type':'paragraph', 'data':{'text':item['subtitle']}})

    
    return render_template('editor_poesia.jinja', lista_texto=lista_texto, blocks=blocks, blocks_s=blocks_s, titulo=titulo, destino=destino)

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

@app.route('/enviarDadosNovaPoesia', methods=['GET', 'POST'])
def enviarDadosNovaPoesia():
    if request.method == "POST":
        info = json.loads(request.form.getlist('json_data_send')[0])

        blocks = []
        blocks_2 = []
        texto = ''

        for item in info['slides']:
            texto = item['text-slide'].replace("<i>", '').replace("</i>", '').replace('<br>', ' ') # retirando o negrito e os espaços
            blocks.append({'type':'paragraph', 'data':{'text':texto}})


        destino = request.form.getlist('destino')[0]
        if destino != '0': # significa que é edição e não acréscimo
            letras = banco.executarConsulta('select * from letras_poesia where id_poesia = %s and pagina = 1 order by paragrafo' % destino)
            blocks = []

            for item in letras:
                blocks.append({'type':'paragraph', 'data':{'text':item['texto']}})

            letras = banco.executarConsulta('select * from letras_poesia where id_poesia = %s and pagina = 2 order by paragrafo' % destino)
            blocks_2 = []

            for item in letras:
                blocks_2.append({'type':'paragraph', 'data':{'text':item['texto']}})

        return render_template('save_poesia.jinja', info=info, blocks=blocks, blocks_2=blocks_2, destino=destino)

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
        aux = ''

        for item in info['slides']:
            texto = item['text-slide'].replace('<b>', '').replace('</b>', '').replace('<br>', ' ').replace('style="font-weight: bold;"', '') # retirando o negrito e os espaços
            

            # inserindo negrito na numeração
            if texto[0:22] == '<span class="cdx-num">':
                if aux != '':
                    blocks.append({'type':'paragraph', 'data':{'text':aux}})
                texto = '<b>' + texto
                pos = texto.find('</span>')

                texto = texto[:pos] + '</b>' + texto[pos:]
                aux = texto + '<br>'
            elif texto[0:18] == '<span class="red">':
                blocks.append({'type':'paragraph', 'data':{'text':aux}})
                if texto[18:19].isdigit():
                    aux = '<b>' + texto.replace('<span class="red">', '<span class="cdx-num">')
                    pos = aux.find('</span>')

                    aux = aux[:pos] + '</b>' + aux[pos:]
                    aux += '<br>'                    
                else:
                    aux = '<i>' + texto + '</i><br>'

            else:
                aux += texto + '<br>'

        blocks.append({'type':'paragraph', 'data':{'text':aux}})

        print(blocks)


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
        final_text = ''
        for item in info['slides']:
            final_text += item['text-slide'].replace('<br>', ' ') + '<br>'
        
        blocks.append({'type':'paragraph', 'data':{'text':final_text}})

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
        else:
            # tentar buscar vínculos do banco antigo
            old_vinc = executarConsultaOldMusic(r"select nome_arquivo, vinculo_1, status_1, desc_1, vinculo_2, status_2, desc_2, vinculo_3, status_3, desc_3 from listaMusicas where nome_arquivo like '%" + info['titulo'] + r"%'")
            
            if len(old_vinc) > 0: # peguei algum vínculo antigo
                for i in range(1, 4):
                    if old_vinc[0]['vinculo_%s' % i] != None:
                        vinculos.append({'id_vinculo':old_vinc[0]['vinculo_%s' % i], 'id_status':old_vinc[0]['status_%s' % i], 'descricao':old_vinc[0]['desc_%s' % i]})



        return render_template('save_musica.jinja', info=info, cat_slides=cat_slides, blocks=blocks, blocks_2=blocks_2, categoria=categoria, status=status, vinculos=vinculos, cat_slides_list=cat_slides_list, destino=destino)

@app.route('/upload_capa',  methods=['GET', 'POST'])
def upload_capa():
    isthisFile = request.files.get('file')
    id = request.form.getlist('id')[0]
    filename = str(id) + os.path.splitext(isthisFile.filename)[1]

    isthisFile.save('./static/images/capas/' + filename)

    banco.insertOrUpdate({'id_musica':id, 'filename':"'" + filename + "'"}, 'id_musica', 'capas')

    return jsonify('./static/images/capas/' + filename)


@app.route('/upload_capa_musical',  methods=['GET', 'POST'])
def upload_capa_musical():
    isthisFile = request.files.get('file')
    filename = 'capa' + os.path.splitext(isthisFile.filename)[1]

    isthisFile.save('./static/images/musical/' + filename)

    banco.insertOrUpdate({'id':"'capa_musical'", 'valor':"'images/musical/" + filename + "'"}, 'id', 'config')

    c = datetime.datetime.now()
    current_time = c.strftime('%d%m%Y%H%M%S')

    return jsonify('./static/images/musical/' + filename + "?" + current_time)


@app.route('/upload_capa_musical_individual',  methods=['GET', 'POST'])
def upload_capa_musical_individual():
    isthisFile = request.files.get('file')
    id = request.form['id']
    tipo = request.form['tipo']

    if tipo == 'item-musica':
        origem = 'musicas'
    elif tipo == 'item-harpa-versionada':
        origem = 'harpa_versionada'
    elif tipo == 'item-poesia':
        origem = 'poesia'
    else:
        origem = 'harpa'

    filename = str(id) + "_" + origem + os.path.splitext(isthisFile.filename)[1]

    print(filename)


    banco.executeCustomQuery("UPDATE roteiro_musical SET capa_url = 'images/musical/%s' WHERE id_origem = %s and `tabela-origem` = '%s'" % (filename, id, origem))

    isthisFile.save('./static/images/musical/' + filename)

    c = datetime.datetime.now()
    current_time = c.strftime('%d%m%Y%H%M%S')

    return jsonify('./static/images/musical/' + filename + "?" + current_time)

@app.route('/converto_to_pdf_list', methods=['GET', 'POST'])
def converto_to_pdf_list():
    global temp_pdf
    temp_pdf = request.json

    hostname = request.headers.get('Host')
    info = {'url':'http://%s/render_pdf?ls=render_preview' % (hostname), 'tipo':'hinario'}

    try:
        with sync_playwright() as playwright:
            pdf_path = run_pdf_generation(playwright, info)

        return send_file(pdf_path, as_attachment=True, mimetype="application/pdf")

    except Exception as e:
        return jsonify({"message": "Erro ao gerar PDF", "error": str(e)}), 500


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
            lista_slides = banco.executarConsulta("select `text-slide`, categoria, ifnull(anotacao, '') as anotacao, pos from slides_harpa where id_harpa = %s order by pos" % id['id'])

            return jsonify({'letras':letras, 'numero':numero, 'titulo':titulo, 'autor':autor, 'versoes':versoes, 'lista_slides':lista_slides})
        
@app.route('/get_info_harpa_versionada', methods=['GET', 'POST'])
def get_info_harpa_versionada():
    if request.method == "POST":
        if request.is_json:

            info = request.json

            letras = banco.executarConsulta('select * from letras_harpa_versionada where id_harpa_versionada = %s' % info['id'])
            desc_versao = banco.executarConsultaVetor('select desc_versao from harpa_versionada where id = %s' % info['id'])[0]


            return {'letras':letras, 'desc_versao':desc_versao}

@app.route('/get_info_poesia', methods=['GET', 'POST'])
def get_info_poesia():
    id = request.json
    letras = banco.executarConsulta('select texto from letras_poesia where id_poesia = %s order by paragrafo' % id['id'])

    return jsonify({'letras':letras})


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

            lista_slides = banco.executarConsulta("select `text-slide`, categoria, ifnull(anotacao, '') as anotacao, pos from slides where id_musica = %s order by pos" % id['id'])

            return jsonify({'vinculos':vinculos, 'letras':letras, 'capa':capa, 'lista_slides':lista_slides})

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


@app.route('/verificarSenhaPoesia', methods=['GET', 'POST'])
def verificarSenhaPoesia():
    if request.method == "POST":
        print('afs')
        senha = encriptar(request.form.getlist('senha')[0])
        destino = request.form.getlist('destino')[0]

        if senha == banco.executarConsultaVetor("select valor from config where id = 'senha_adm'")[0]:
            if destino == '0':
                return render_template('editor_poesia.jinja', blocks=[], blocks_s=[], lista_texto=[], destino=0)
            else:
                blocks = []
                blocks_s = []
                titulo = banco.executarConsulta('select titulo from poesia where id = %s' % destino)[0]['titulo']
                lista_texto = banco.executarConsulta("select pos, `text-slide`, `text-legenda` as subtitle, ifnull(anotacao, '') as anotacao from slide_poesia where id_poesia = %s order by pos" % destino)

                # recriar lista pro editor
                for item in lista_texto:
                    blocks.append({'type':'paragraph', 'data':{'text':item['text-slide']}})
                    blocks_s.append({'type':'paragraph', 'data':{'text':item['subtitle']}})

                return render_template('editor_poesia.jinja', lista_texto=lista_texto, blocks=blocks, blocks_s=blocks_s, titulo=titulo, destino=destino)
        else:
            poesias = banco.executarConsulta('select * from poesia order by titulo')
            status= '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Senha incorreta!</strong> Por favor digite a senha correta para abrir a área de Cadastro e Alteração.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'

            return render_template('poesias.jinja', poesias=poesias, status=status)
    else:
        return redirect('/')


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

@app.route('/verificarSenhaHistorico', methods=['GET', 'POST'])
def verificarSenhaHistorico():
    if request.method == 'POST':
        senha = encriptar(request.form.getlist('senha')[0])

        if senha == banco.executarConsultaVetor("select valor from config where id = 'senha_adm'")[0]:
            return redirect(url_for('add_historico'))
        else:
            return redirect(url_for('historico', status='<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Senha incorreta!</strong> Por favor digite a senha correta para abrir a área de Cadastro e Alteração.<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'))

    return render_template('erro.jinja', log='Erro fatal ao tentar redirecionar para área de Administrador.')


@app.route('/gerar_imagem_calendario_mensal', methods=['GET', 'POST'])
def gerar_imagem_calendario_mensal():
    info = request.json
    hostname = request.headers.get('Host')

    info = {'url':'http://%s/render_calendario_mensal?ano=%s&mes=%s' % (hostname, info['ano'], info['mes']), 'tipo':'calendario'}

    try:
        with sync_playwright() as playwright:
            result = run_pdf_generation(playwright, info)
            result = base64.b64encode(result).decode('utf-8')
        
            return jsonify({"message": "Script executed successfully!", "output": result}), 200
        
    except Exception as e:
        return jsonify({"message": "An error occurred.", "error": str(e)}), 500


@app.route('/gerar_imagem_calendario', methods=['GET', 'POST'])
def gerar_imagem_calendario():
    info = request.json
    hostname = request.headers.get('Host')

    print(info['data'])

    info = {'url':'http://%s/render_calendario?semana=%s' % (hostname, info['data']), 'tipo':'calendario'}

    try:
        with sync_playwright() as playwright:
            result = run_pdf_generation(playwright, info)
            result = base64.b64encode(result).decode('utf-8')
        
            return jsonify({"message": "Script executed successfully!", "output": result}), 200
        
    except Exception as e:
        return jsonify({"message": "An error occurred.", "error": str(e)}), 500

@app.route('/gerar_pdf_slide', methods=['GET', 'POST'])
def gerar_pdf_slide():
    info = request.json
    hostname = request.headers.get('Host')

    web_info = {'url':'http://%s/render_slide_pdf?id=%s&destino=%s&id_name=%s&classe=%s' % (hostname, info['id'], info['destino'], info['id_name'], info['classe']), 'tipo':'slide'}

    try:
        with sync_playwright() as playwright:
            pdf_path = run_pdf_generation(playwright, web_info)

        return send_file(pdf_path, as_attachment=True, mimetype="application/pdf")

    except Exception as e:
        return jsonify({"message": "Erro ao gerar PDF", "error": str(e)}), 500

@app.route('/gerar_pdf', methods=['GET', 'POST'])
def gerar_pdf():
    ls = request.json
    hostname = request.headers.get('Host')

    print('http://%s/render_pdf?ls=%s' % (hostname, ls))

    info = {'url':'http://%s/render_pdf?ls=%s' % (hostname, ls), 'tipo':'hinario', 'ls':ls}

    try:
        with sync_playwright() as playwright:
            pdf_path = run_pdf_generation(playwright, info)

        return send_file(pdf_path, as_attachment=True, mimetype="application/pdf")

    except Exception as e:
        return jsonify({"message": "Erro ao gerar PDF", "error": str(e)}), 500

@app.route('/gerar_pdf_harpa', methods=['GET', 'POST'])
def gerar_pdf_harpa():
    info = request.json
    hostname = request.headers.get('Host')

    info = {'url':'http://%s/render_pdf_harpa?tipo=%s' % (hostname, info['tipo']), 'tipo':'hinario'}

    try:
        with sync_playwright() as playwright:
            pdf_path = run_pdf_generation(playwright, info)

        return send_file(pdf_path, as_attachment=True, mimetype="application/pdf")

    except Exception as e:
        return jsonify({"message": "Erro ao gerar PDF", "error": str(e)}), 500


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

            resultados = banco.executarConsulta("select livro, cap, ver from biblia_ara where texto like '%s' union select livro, cap, ver from biblia_arc where texto like '%s' union select livro, cap, ver from biblia_naa where texto like '%s' union select livro, cap, ver from biblia_nvi where texto like '%s' union select livro, cap, ver from biblia_nvt where texto like '%s' order by livro, cap, ver" % (pesquisa, pesquisa, pesquisa, pesquisa, pesquisa))
            

            for item in resultados:

                item['desc_livro'] = banco.executarConsultaVetor('select descricao from livro_biblia where id = %s'  % item['livro'])[0]

                sql = 'select '
                for tb in tabelas:
                    sql += '%s.texto as %s, ' % (tb, tb)

                sql = sql[:-2] + ' from %s ' % tabelas[0]

                for i in range(1, len(tabelas)):
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
                        config = {'letra':banco.executarConsulta("select valor from config where id = 'cor-harpa-letra'")[0]['valor'], 'fundo':banco.executarConsulta("select valor from config where id = 'cor-harpa-fundo'")[0]['valor'], 'num':banco.executarConsulta("select valor from config where id = 'cor-harpa-num'")[0]['valor'], 'red':banco.executarConsulta("select valor from config where id = 'cor-harpa-red'")[0]['valor']}
                        return render_template('resultado_pesquisa_harpa.jinja', resultado_pesquisa=resultado_pesquisa, lista_palavras=lista_palavras, pesquisa=pesquisa_original, config=config)
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
                        config = {'letra':banco.executarConsulta("select valor from config where id = 'cor-musica-letra'")[0]['valor'], 'fundo':banco.executarConsulta("select valor from config where id = 'cor-musica-fundo'")[0]['valor'], 'mark':banco.executarConsulta("select valor from config where id = 'cor-musica-mark'")[0]['valor']}
                        return render_template('resultado_pesquisa.jinja', resultado_pesquisa=resultado_pesquisa, lista_palavras=lista_palavras, pesquisa=pesquisa_original, config=config)
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
        rows = banco.executarConsulta("SELECT id, valor FROM config")
        rows_dict = {row['id']: row['valor'] for row in rows}
        config = {'letra':rows_dict['cor-musica-letra'], 'fundo':rows_dict['cor-musica-fundo'], 'mark':rows_dict['cor-musica-mark'],  'num':rows_dict['cor-harpa-num'], 'red':rows_dict['cor-harpa-red'], 'alternante':rows_dict['cor-musica-alternante']}

        #pegar um texto aleatório pra testar o preview
        texto = banco.executarConsulta('''SELECT `text-slide` FROM slides WHERE `text-slide` LIKE '%<mark class="cdx-marker">%' ORDER BY RANDOM() LIMIT 1''')[0]['text-slide']

        return render_template('alterar_fundo.jinja', titulo='Música', preview=texto, config=config)

    elif (destino == 'h'):
        rows = banco.executarConsulta("SELECT id, valor FROM config")
        rows_dict = {row['id']: row['valor'] for row in rows}
        config = {'letra':rows_dict['cor-harpa-letra'], 'fundo':rows_dict['cor-harpa-fundo'], 'num':rows_dict['cor-harpa-num'], 'red':rows_dict['cor-harpa-red']}
    
        # texto aleatório início de estrofe
        texto_1 = banco.executarConsulta('''SELECT `text-slide` FROM slides_harpa WHERE `text-slide` LIKE '%<span class="cdx-num">%' ORDER BY RANDOM() LIMIT 1''')[0]['text-slide']
        # texto aleatório com coro ou estrofe final
        texto_2 = banco.executarConsulta('''SELECT `text-slide` FROM slides_harpa WHERE `text-slide` LIKE '%<span class="red">%' ORDER BY RANDOM() LIMIT 1''')[0]['text-slide']

        return render_template('alterar_fundo_h.jinja', titulo='Harpa', preview={'texto1':texto_1, 'texto2':texto_2}, config=config)


@app.route('/open_window_slide', methods=['GET', 'POST'])
def open_window_slide():

    if request.method == 'POST': # significa que precisa mandar abrir a janela

        path = os.path.dirname(os.path.realpath(__file__)) + "\\Desktop_Version.py"
        global window_browser

        if window_browser is not None:
            window_browser.kill()

        try:
            # Call the form_interaction.py script with parameters
            window_browser = subprocess.Popen(
                ['pythonw', path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            return jsonify({"message": "Janela aberta com sucesso!", "result":True})

        except Exception as e:
            print("An exception occurred:", e) # An exception occurred: division by zero
            return jsonify({"message": "An error occurred.", "error": str(e), "result":False}), 500




@app.route('/slide_pix', methods=['GET', 'POST'])
def slide_pix():

    if request.method == 'POST': # significa que o comando de solicitação de troca foi feito
        socketio.emit('pix', 1)
        return jsonify(True)

    pix = banco.executarConsultaVetor("select valor from config where id = 'chave-pix-igreja'")[0]

    return render_template('slide_pix.jinja', pix=pix)

@app.route('/wallpaper_new', methods=['GET', 'POST'])
def wallpaper_new():

    status = ''
    id = 1

    if request.method == 'POST':

        if request.is_json:

            info = request.json

            if info['destino'] == 0:

                id = info['id']
                
                # pegar dados novamente
                selecionado = banco.executarConsultaVetor("select valor from config where id = 'wallpaper_show_id'")[0]
                lista_wallpapers = banco.executarConsulta("select id, descricao, arquivos, segundos, CASE WHEN id == %s THEN 'selected' ELSE '' END AS selected from slide_show_wallpaper order by id" % id)

                arquivos_selecionados = banco.executarConsulta('select arquivos, segundos from slide_show_wallpaper where id = %s' % id)[0]

                path = os.path.dirname(os.path.realpath(__file__)) + '\\static\\images\\Wallpaper'
                files_folder = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
                file_list = eval(arquivos_selecionados['arquivos'])

                lista_final = []
                for item in file_list:
                    lista_final.append({'nome':item, 'class':'box-index', 'check':'checked'})

                for item in files_folder:
                    if item not in file_list:
                        lista_final.append({'nome':item, 'class':'shadow-sm', 'check':''})            


                return jsonify({'seg':arquivos_selecionados['segundos'], 'lista':lista_final})
            
            if info['destino'] == 1:
                id = info['id']
                
                if banco.change_config([{'id':"'wallpaper_show_id'", 'valor':id}]):
                    socketio.emit('change_wallpaper', 1)
                    return jsonify(True)
                else:
                    return jsonify(False)
        
        if 'upload' in request.files:

            try:
                isthisFile = request.files.get('upload')
                filename = isthisFile.filename
                isthisFile.save('./static/images/Wallpaper/' + filename)

                status = '<div class="alert alert-success alert-dismissible fade show" role="alert"><strong>Operação realizada com sucesso!</strong> Arquivo <strong>"' + filename + '"</strong> foi devidamente inserido na pasta de Wallpapers!<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
            except:
                status = '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Atenção! Erro fatal!</strong> Falha grave ao tentar inserir arquivo na pasta!<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
        
        if 'nome_arquivo_del' in request.form:
            try:
                os.remove(os.path.join('./static/images/Wallpaper/', request.form['nome_arquivo_del']))
                status = '<div class="alert alert-success alert-dismissible fade show" role="alert"><strong>Operação realizada com sucesso!</strong> Arquivo <strong>"' + request.form['nome_arquivo_del'] + '"</strong> excluído com sucesso!<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
            except:
                status = '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Atenção! Erro fatal!</strong> Falha grave ao tentar esxcluir arquivo da pasta!<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'

        if 'txt_new_slide_show' in request.form:

            try:
                banco.executeCustomQuery("INSERT INTO slide_show_wallpaper(descricao, arquivos, segundos) VALUES('%s', '[]', 0)" % request.form['txt_new_slide_show'])
                status = '<div class="alert alert-success alert-dismissible fade show" role="alert"><strong>Operação realizada com sucesso!</strong> Esquema de Slide <strong>"' + request.form['txt_new_slide_show'] + '"</strong> inserido com sucesso!<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
            except:
                status = '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Atenção! Erro fatal!</strong> Falha grave ao tentar incluir esquema de SlideShow!<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'

        if 'val_delete_id' in request.form:
            sql = 'DELETE FROM slide_show_wallpaper WHERE id = %s' % request.form['val_delete_id']
            print(sql)
            if banco.executeCustomQuery(sql):
                status = '<div class="alert alert-success alert-dismissible fade show" role="alert"><strong>Operação realizada com sucesso!</strong> Esquema de Slide excluído com sucesso!<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
            else:
                status = '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Atenção! Erro fatal!</strong> Falha grave ao tentar excluir esquema de SlideShow!<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'

        if 'val_id_update' in request.form:

            try:
                id_slideshow = request.form['val_id_update']
                seg = request.form['txt_segundos']
                files = request.form['arquivos']

                banco.executeCustomQuery('UPDATE slide_show_wallpaper SET arquivos="%s", segundos=%s WHERE id=%s' % (files, seg, id_slideshow))
                status = '<div class="alert alert-success alert-dismissible fade show" role="alert"><strong>Operação realizada com sucesso!</strong> Alteração do SlideShow efetuado com sucesso!<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
                socketio.emit('change_wallpaper', 1)
            except:
                status = '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Atenção! Erro fatal!</strong> Falha grave ao tentar alterar banco!<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
                print('UPDATE slide_show_wallpaper SET arquivos="%s", segundos=%s WHERE id=%s' % (files, seg, id_slideshow))

    
    selecionado = banco.executarConsultaVetor("select valor from config where id = 'wallpaper_show_id'")[0]
    lista_wallpapers = banco.executarConsulta("select id, descricao, arquivos, segundos, CASE WHEN id == %s THEN 'selected' ELSE '' END AS selected from slide_show_wallpaper order by descricao" % selecionado)

    arquivos_selecionados = banco.executarConsulta('select arquivos, segundos from slide_show_wallpaper where id = %s' % selecionado)[0]

    path = os.path.dirname(os.path.realpath(__file__)) + '\\static\\images\\Wallpaper'
    files_folder = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    file_list = eval(arquivos_selecionados['arquivos'])

    lista_final = []
    for item in file_list:
        lista_final.append({'nome':item, 'class':'box-index', 'check':'checked'})

    for item in files_folder:
        if item not in file_list:
            lista_final.append({'nome':item, 'class':'shadow-sm', 'check':''})


    return render_template('wallpaper_new.jinja', selecionado=selecionado, lista=lista_final, status=status, lista_wallpapers=lista_wallpapers, segundos=arquivos_selecionados['segundos'])

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


@app.route('/abrir_video', methods=['GET', 'POST'])
def abrir_video():

    global current_presentation
    global estado
    global index

    if request.method == 'POST':

        file = request.files.get('file')

        path = os.path.dirname(os.path.realpath(__file__)) + '\\static\\uploads\\video.mp4'
        file.save(path) # processo de salvamento do arquivo

        estado = 7
        current_presentation['file'] = '\\static\\uploads\\video.mp4'

        socketio.emit('refresh', 1)

        return redirect('/controlador')

    return render_template('abrir_video.jinja')

@app.route('/abrir_pptx', methods=['GET', 'POST'])
def abrir_pptx():

    global current_presentation
    global estado
    global index

    status = ''

    if request.method == 'POST':

        socketio.emit('wait_pptx', 1)

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
          r'CASE WHEN tipo = 1 THEN livro_biblia.descricao || " - Cap. " || capitulo WHEN tipo = 2 THEN musicas.titulo WHEN tipo = 3 THEN PRINTF("%03d", harpa.id) || " - " || harpa.descricao ELSE poesia.titulo END as alvo, ' + \
          "log.atividade as num_atividdade " + \
          "FROM log " + \
          "INNER JOIN cat_log ON cat_log.id = log.atividade " + \
          "LEFT JOIN musicas ON musicas.id = log.id_musica LEFT JOIN harpa ON harpa.id = log.id_harpa LEFT JOIN livro_biblia ON livro_biblia.id = log.livro_biblia LEFT JOIN poesia ON poesia.id = log.id_poesia order by data_hora desc"
    
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

@app.route('/wait_pptx', methods=['GET', 'POST'])
def wait_pptx():

    return render_template('wait_pptx_animation.jinja')


@app.route('/iniciar_apresentacao', methods=['GET', 'POST'])
def iniciar_apresentacao():

    global current_presentation
    global estado
    global index
    global roteiro
    global pause_index
    global ponteiro_musical

    if request.method == 'POST':
        if request.is_json:
            info = request.json
            current_presentation = {'id':info['id'], 'tipo':info['tipo']}
            index = 0

            if info['tipo'] == 'musicas':
                estado = 1
                index = int(info['index'])
                insert_log(5, 2, info['id'], 0)
            elif info['tipo'] == 'harpa':
                estado = 3
                index = int(info['index'])
                insert_log(5, 3, info['id'], 0)
            elif info['tipo'] == 'harpa_versionada':
                estado = 4
                insert_log(5, 3, banco.executarConsultaVetor('select id_harpa from harpa_versionada where id = %s' % info['id'])[0], 0)
            elif info['tipo'] == 'calendario':
                estado = 6
                current_presentation['mes'] = info['mes']
                current_presentation['semana'] = info['semana']
            elif info['tipo'] == 'ebd':
                estado = 8
            elif info['tipo'] == 'musical':
                total = banco.executarConsulta('select count(*) as total from roteiro_musical')[0]['total']

                if total > 0:
                    estado = 9
                    index = pause_index
                else:
                    current_presentation = {'id':0, 'tipo':''}
                    return jsonify(False)
            elif info['tipo'] == 'poesia':
                estado = 10


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
                        insert_log(5, 3, banco.executarConsultaVetor('select id_harpa from harpa_versionada where id = %s' % current_presentation['id'])[0], 0)

                    index = 0

                    socketio.emit('refresh', 1)
                    break

            return redirect('/')

@app.route('/alterar_roteiro_musical', methods=['GET', 'POST'])
def alterar_roteiro_musical():      

    global index
    global ponteiro_musical

    if request.method == 'POST':
        if request.is_json:
            ponteiro_musical = request.json
            index = 0
            #socketio.emit('update', {'index':index, 'ponteiro':ponteiro_musical})

            query = '''SELECT
                        id_origem,
                        `tabela-origem`,
                        CASE WHEN capa_url IS NULL THEN 
                            CASE WHEN `tabela-origem` = 'musicas' THEN 'images/capas/' || capas.filename
                            WHEN `tabela-origem` = 'poesia' THEN '[SEM_CAPA_POESIA]'
                            ELSE '[SEM_CAPA_HARPA]' END
                        ELSE capa_url END as capa_url,
                        CASE WHEN `tabela-origem` = 'musicas' THEN musicas.titulo
                            WHEN `tabela-origem` = 'harpa' THEN harpa.descricao
                            WHEN `tabela-origem` = 'harpa_versionada' THEN (SELECT descricao FROM harpa WHERE id = (SELECT id_harpa FROM harpa_versionada WHERE id = id_origem)) 
                        END AS titulo
                    FROM roteiro_musical
                    LEFT JOIN musicas ON musicas.id = id_origem
                    LEFT JOIN harpa ON harpa.id = id_origem
                    LEFT JOIN capas ON capas.id_musica = musicas.id'''

            roteiro_musical = banco.executarConsulta(query)
            item_atual = roteiro_musical[ponteiro_musical]

            lista_final = []

            # adicionado capa principal
            capa_padrao = banco.executarConsulta("select valor from config where id = 'capa_musical'")[0]['valor']
            lista_final.append({'tipo':'capa_img', 'url':capa_padrao})            

            # adicionando capa
            if item_atual['capa_url'] == '[SEM_CAPA_HARPA]':

                id_harpa = item_atual['id_origem']

                if item_atual['tabela-origem'] == 'harpa_versionada':
                    id_harpa = banco.executarConsultaVetor('select id_harpa from harpa_versionada where id = %s' % id_harpa)[0]

                hostname = request.headers.get('Host')
                info = {'url':'http://%s/render_capa_harpa?id=%s' % (hostname, id_harpa), 'tipo':'capa'}

                try:
                    with sync_playwright() as playwright:
                        capa = run_pdf_generation(playwright, info)
                        capa = base64.b64encode(capa).decode('utf-8')

                except Exception as e:
                    print({"message": "Erro ao gerar Imagem", "error": str(e)}), 500             

                lista_final.append({'tipo':'capa_base64', 'url':capa})
                
            elif item_atual['capa_url'] == '[SEM_CAPA_POESIA]':

                hostname = request.headers.get('Host')
                info = {'url':'http://%s/render_capa_poesia?id=%s' % (hostname, item_atual['id_origem']), 'tipo':'capa'}


                try:
                    with sync_playwright() as playwright:
                        capa = run_pdf_generation(playwright, info)
                        capa = base64.b64encode(capa).decode('utf-8')

                except Exception as e:
                    print({"message": "Erro ao gerar Imagem", "error": str(e)}), 500             

                lista_final.append({'tipo':'capa_base64', 'url':capa})                

            else:
                lista_final.append({'tipo':'capa_img', 'url':item_atual['capa_url']})

            # adicionando slides
            if item_atual['tabela-origem'] == 'musicas':
                letras = banco.executarConsulta('select `text-slide`, categoria, ifnull(anotacao, "") as anotacao from slides where id_musica = %s' % item_atual['id_origem'])
                for sld in letras:
                    lista_final.append({'tipo':'letra', 'cat':sld['categoria'], 'categoria':'cat-' + str(sld['categoria']) + '-musica', 'anotacao':sld['anotacao'], 'texto':sld['text-slide']})
            elif item_atual['tabela-origem'] == 'harpa_versionada':
                letras = banco.executarConsulta('select `text-slide`, categoria, ifnull(anotacao, "") as anotacao from slides_harpa_versionada where id_harpa_versionada = %s' % item_atual['id_origem'])
                for sld in letras:
                    lista_final.append({'tipo':'letra', 'cat':sld['categoria'], 'categoria':'cat-' + str(sld['categoria']) + '-harpa', 'anotacao':sld['anotacao'], 'texto':sld['text-slide']})
            elif item_atual['tabela-origem'] == 'poesia':
                letras = banco.executarConsulta('select `text-slide`, ifnull(anotacao, "") as anotacao from slide_poesia where id_poesia = %s' % item_atual['id_origem'])
                for sld in letras:
                    lista_final.append({'tipo':'letra', 'cat':'poesia', 'categoria':'cat-poesia', 'anotacao':sld['anotacao'], 'texto':sld['text-slide']})
            else:
                letras = banco.executarConsulta('select `text-slide`, categoria, ifnull(anotacao, "") as anotacao from slides_harpa where id_harpa = %s' % item_atual['id_origem'])
                for sld in letras:
                    lista_final.append({'tipo':'letra', 'cat':sld['categoria'], 'categoria':'cat-' + str(sld['categoria']) + '-harpa', 'anotacao':sld['anotacao'], 'texto':sld['text-slide']})

            # adicionando capa inicial no final da música
            lista_final.append({'tipo':'capa_img', 'url':capa_padrao})

            # adicionando cores
            cores = banco.executarConsulta("SELECT (SELECT valor FROM config WHERE id = 'cor-harpa-fundo') as cor_harpa_fundo, (SELECT valor FROM config WHERE id = 'cor-harpa-letra') as cor_harpa_letra, (SELECT valor FROM config WHERE id = 'cor-harpa-num') as cor_harpa_num, (SELECT valor FROM config WHERE id = 'cor-harpa-red') as cor_harpa_red, (SELECT valor FROM config WHERE id = 'cor-musica-fundo') as cor_musica_fundo, (SELECT valor FROM config WHERE id = 'cor-musica-letra') as cor_musica_letra, (SELECT valor FROM config WHERE id = 'cor-musica-mark') as cor_musica_mark")[0]            

            return jsonify({'lista':lista_final, 'cores':cores})

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
    global pause_index
    global ponteiro_musical


    if request.method == 'POST':
        if request.is_json:
            if int(request.json) == 1:
                estado = 0
                current_presentation = {'id':0, 'tipo':''}
                index = 0
                pause_index = index
                ponteiro_musical = 0

                socketio.emit('refresh', 1)
                socketio.emit('update_roteiro', 1)

            elif int(request.json) == 2: # pausar
                estado = 0
                current_presentation = {'id':0, 'tipo':''}
                pause_index = index
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


# testar integração com react
@app.route('/api/musicas')
def listar_musicas():
    return jsonify(["Vem, esta é a hora", "Santo Espírito", "Agnus Dei"])


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True, port=5000)
    #serve(app, host='0.0.0.0', port=80, threads=8)
    #eventlet.wsgi.server(eventlet.listen(('', 80)), app)
    #socketio.run(app, port=80,host='0.0.0.0', debug=True) 
    #monkey.patch_all()
    #http_server = WSGIServer(('0.0.0.0', 80), app)
    #http_server.serve_forever()