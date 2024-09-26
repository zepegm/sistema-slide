import asyncio 
from pyppeteer import launch 
from bs4 import BeautifulSoup

async def main():
    browser = await launch()
    page = await browser.newPage()    
    await page.goto('https://www.bible.com/bible/1608/GEN.1.ARA')
    await page.waitForSelector("main > div > div > div > div > div > button")

    await page.click("main > div > div > div > div > div > button")

    await page.screenshot({'path': 'static/images/etapas_navegacao/ETAPA 1.png'})

    #await page.waitForSelector('.pbe-px', {'visible': True}) 

    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')
    ls_final = []
    lista_ul = soup.find('ul', {'class':'pbe-px'})

    livros = lista_ul.find_all("li")

    for index, item in enumerate(livros):
        await page.waitForSelector(".pbe-px")
        await page.click(".pbe-px > li:nth-child(%sn)" % (index + 1))
        await page.waitForSelector("p.truncate")
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        painel_aux = soup.find('div', {"id":"headlessui-popover-panel-:r4:"})
        link = painel_aux.find_all('a')
        ls_final.append(link[0].get_attribute_list('href')[0][12:15])
        await page.screenshot({'path': 'static/images/etapas_navegacao/ETAPA 2.png'})
        await page.click("button.mie-auto")
        print(link[0].get_attribute_list('href')[0][12:15])


    #link = soup.find('div', {'class':'headlessui-popover-panel-:r3c:'})

    #print(link.text)

    await browser.close()
    return ls_final

print(asyncio.get_event_loop().run_until_complete(main()))