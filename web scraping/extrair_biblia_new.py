import asyncio 
from pyppeteer import launch 
from bs4 import BeautifulSoup
from SQLite_DB import db

banco = db()

head_list = ['GEN', 'EXO', 'LEV', 'NUM', 'DEU', 'JOS', 'JDG', 'RUT', '1SA', '2SA', '1KI', '2KI']

async def main(head):
    browser = await launch()
    page = await browser.newPage()
    await page.goto('https://www.bible.com/bible/1608/%s' % head)
    html = await page.content()
    await browser.close()
 
    soup = BeautifulSoup(html, 'html.parser')
    mydivs = soup.find_all("span", {"class": "ChapterContent_verse__57FIw"})
    
    painel_geral = soup.find('div', {'class':'ChapterContent_chapter__uvbXo'})

    elements = painel_geral.find_all("div")
    titulos_poema = {}

    for item in elements:
        try:
            if item.get_attribute_list('class')[0] == 'ChapterContent_sp__y6CR3':
                texto = item.text
                ver = int(item.find_next("span", {'class':'ChapterContent_label__R2PLt'}).text)
                titulos_poema[ver] = texto
        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero

    return {'versiculos':mydivs, 'titulos':titulos_poema}


lista_final = []

livro = banco.executarConsultaVetor('select max(livro) + 1 from biblia_ara')[0]

for i in range(1, 1):

    capitulo = i
    head = 'ISA.%s.ARA' % capitulo
    ls = asyncio.get_event_loop().run_until_complete(main(head))
    versiculos = ls['versiculos']
    titulos_poema = ls['titulos']
    key_span = False

    print('pegando capítulo %s' % i)

    for item in versiculos:
        try:
            ver = int(item.find('span', {"class":"ChapterContent_label__R2PLt"}).text)

            text_list = item.find_all('span')

            try:
                texto_final = '<span class="heading">%s: </span>' % titulos_poema[ver]
            except:
                texto_final = ''

            for txt in text_list:
                if txt.get_attribute_list('class')[0] not in ['ChapterContent_label__R2PLt', 'ChapterContent_note__YlDW0', 'ChapterContent_body__O3qjr']:

                    if txt.get_attribute_list('class')[0] in ['ChapterContent_nd__ECPAf', 'ChapterContent_sc__Hg9da']:
                        texto_final += '<span class="nd">'
                        key_span = True
                    elif txt.get_attribute_list('class')[0] == 'ChapterContent_wj___uP1U':
                        texto_final += '<span class="wj">'
                        key_span = True                    
                    else:
                        texto_final += txt.text

                        if (key_span):
                            texto_final = texto_final + "</span>"
                            key_span = False


            lista_final.append({'livro':livro, 'cap':capitulo, 'ver':ver, 'texto':texto_final.strip()})

        except:
            element = item.find('span', {'class':'ChapterContent_content__RrUqA'}).text

            if element != ' ':
                lista_final[-1]['texto'] += ' ' + element


        

#print('inserindo dados no banco')
#banco.insertListBiblia(lista_final, 'biblia_ara')



