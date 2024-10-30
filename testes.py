from pyppeteer import launch
import asyncio



async def musical():

    pdf_path = 'static/docs/musica.pdf'

    browser = await launch(      
        handleSIGINT=False,
        handleSIGTERM=False,
        handleSIGHUP=False
    )

    #hostname = request.headers.get('Host')
    hostname = 'localhost'

    page = await browser.newPage()
    await page.setViewport({"width": 1280, "height": 720})
    await page.goto('http://%s/render_slide_pdf?id=%s&destino=slides&id_name=id_musica&classe=musica' % (hostname, 1), {'waitUntil':'networkidle2'})
    await page.pdf({'path': pdf_path, 'printBackground':True, 'fullPage': True, 'width':1280, 'height':720})
    await browser.close()


asyncio.run(musical()) # Here
