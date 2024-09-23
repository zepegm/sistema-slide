import asyncio 
from pyppeteer import launch 
from bs4 import BeautifulSoup
from SQLite_DB import db

banco = db()

async def main(head):
    browser = await launch()
    page = await browser.newPage()
    await page.goto('https://www.bible.com/bible/1608/%s' % head)
    html = await page.content()
    await browser.close()
 
    soup = BeautifulSoup(html, 'html.parser')
    mydivs = soup.find_all("span", {"class": "ChapterContent_verse__57FIw"})

    return mydivs


lista_final = []

for i in range(21, 51):

    livro = 1
    capitulo = i
    head = 'GEN.%s.ARA' % capitulo
    versiculos = asyncio.get_event_loop().run_until_complete(main(head))
    key_span = False

    print('pegando caítulo %s' % i)

    for item in versiculos:
        try:
            ver = int(item.find('span', {"class":"ChapterContent_label__R2PLt"}).text)

            text_list = item.find_all('span')
            texto_final = ''

            for txt in text_list:
                if txt.get_attribute_list('class')[0] not in ['ChapterContent_label__R2PLt', 'ChapterContent_note__YlDW0', 'ChapterContent_body__O3qjr']:

                    if txt.get_attribute_list('class')[0] == 'ChapterContent_nd__ECPAf':
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

        

print('inserindo dados no banco')
banco.insertListBiblia(lista_final, 'biblia_ara')



