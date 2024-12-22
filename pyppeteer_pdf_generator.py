import sys
import json
import base64
import asyncio
from pyppeteer import launch

async def run(source):
    # Lê as informações da entrada
    info = json.loads(source)

    # Inicia o navegador em modo headless
    browser = await launch(headless=True)
    page = await browser.newPage()

    # Navega até a URL fornecida
    await page.goto(info['url'])

    pdf_bytes = None

    # Gerar PDF ou capturas de tela com base no tipo
    if info['tipo'] == 'hinario':
        pdf_bytes = await page.pdf(format='A5', printBackground=True, scale=1.95, margin={'top': '18px'})
    elif info['tipo'] == 'slide':
        await page.setViewport({"width": 1280, "height": 720})
        pdf_bytes = await page.pdf(printBackground=True, width=1280, height=720)
    elif info['tipo'] == 'capa':
        await page.setViewport({"width": 1366, "height": 768})
        pdf_bytes = await page.screenshot(fullPage=True)
    elif info['tipo'] == 'calendario':
        await page.waitForSelector('.text')
        await page.setViewport({"width": 1512, "height": 1200})
        pdf_bytes = await page.screenshot(fullPage=True)

    # Fecha o navegador
    await browser.close()

    return pdf_bytes


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python script.py <json_input>")
        sys.exit(1)

    # Captura os argumentos e executa a função principal
    source = sys.argv[1]
    pdf_base64 = asyncio.run(run(source))
    print(pdf_base64)