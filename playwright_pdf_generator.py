import os
import uuid
import base64
from playwright.sync_api import Playwright

def run_pdf_generation(playwright: Playwright, info: dict) -> str:
    """
    Gera um PDF ou imagem baseado nas instruções passadas em 'info'.
    Retorna o caminho do arquivo salvo.
    """

    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    # Garante que a URL seja montada corretamente se apenas 'ls' for passado
    if 'url' not in info:
        info['url'] = f"http://localhost:5000/render_pdf?ls={info.get('ls', '')}"

    page.goto(info['url'], wait_until="load", timeout=15000)

    output_dir = "static\\docs"
    os.makedirs(output_dir, exist_ok=True)

    tipo = info.get("tipo")
    filename = ""

    if tipo == 'hinario':
        #filename = f"output_hinario_{uuid.uuid4().hex}.pdf"
        filename = f"output_hinario.pdf"
        path = os.path.join(output_dir, filename)
        page.pdf(path=path, format="A5", print_background=True, scale=1.95, margin={'top': '18px'})
    elif tipo == 'slide':
        #filename = f"output_slide_{uuid.uuid4().hex}.pdf"
        filename = f"output_slide.pdf"
        path = os.path.join(output_dir, filename)
        page.set_viewport_size({"width": 1280, "height": 720})
        page.pdf(path=path, print_background=True, width="1280px", height="720px")
    elif tipo == 'capa' or tipo == 'calendario':
        # Em ambos, estamos usando screenshot
        page.wait_for_timeout(500)  # tempo mínimo para evitar render incompleto
        path = page.screenshot(full_page=True)
        #filename = f"{tipo}_{uuid.uuid4().hex}.png"
        #filename = f"{tipo}.png"
        #path = os.path.join(output_dir, filename)
        #with open(path, "wb") as f:
            #f.write(screenshot_bytes)
    else:
        browser.close()
        raise ValueError(f"Tipo desconhecido: {tipo}")

    browser.close()
    return path
