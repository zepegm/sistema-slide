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

    lista_ul = soup.find('ul', {'class':'pbe-px'})

    livros = lista_ul.find_all("li")

    for index, item in enumerate(livros):
        await page.click(".pbe-px > li:nth-child(%sn)" % (index + 1))
        painel_aux = soup.find('div', {"id":"headlessui-popover-panel-:r4:"})
        link = painel_aux.find_all('a')
        print(link)
        await page.screenshot({'path': 'static/images/etapas_navegacao/ETAPA 2.png'})

    #link = soup.find('div', {'class':'headlessui-popover-panel-:r3c:'})

    #print(link.text)

    await browser.close()

asyncio.get_event_loop().run_until_complete(main())