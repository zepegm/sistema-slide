import sys
import json
import base64
from playwright.sync_api import sync_playwright

def run(playwright, source):
    # Launch the browser (you can use 'firefox' or 'webkit' as well)
    browser = playwright.chromium.launch(headless=True)  # Set headless=True to run without UI
    page = browser.new_page()

    info = json.loads(source)
    
    # Navigate to a website
    page.goto(info['url'])

    page.wait_for_load_state('domcontentloaded')
    
    # gerar PDF
    if info['tipo'] == 'hinario':
        pdf_bytes = page.pdf(format='A5', print_background=True, scale=1.95, margin={'top':'18px'})
    elif info['tipo'] == 'slide':
        page.set_viewport_size({"width": 1280, "height": 720})
        pdf_bytes = page.pdf(print_background=True, width="1280px", height="720px")
    elif info['tipo'] == 'capa':
        page.set_viewport_size({"width": 1366, "height": 768})
        pdf_bytes = page.screenshot(full_page=True)
    elif info['tipo'] == 'calendario':
        page.set_viewport_size({"width": 1512, "height": 1200})
        pdf_bytes = page.screenshot(full_page=True)

    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

    
    # Close the browser
    browser.close()

    return pdf_base64

if __name__ == '__main__':
    with sync_playwright() as playwright:
        if len(sys.argv) < 2:
            print("Usage: python form_interaction.py <username> <password>")
            sys.exit(1)
        pdf = run(playwright, sys.argv[1])
        print(pdf)    