import csv

from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import XMLConverter, HTMLConverter, TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
import io
import re

fp = open('Letras do Musical de Páscoa.pdf', 'rb')
rsrcmgr = PDFResourceManager()
retstr = io.StringIO()
print(type(retstr))
codec = 'utf-8'
laparams = LAParams()
device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
interpreter = PDFPageInterpreter(rsrcmgr, device)

lista = []

page_no = 0
for pageNumber, page in enumerate(PDFPage.get_pages(fp)):
    if pageNumber == page_no:
        interpreter.process_page(page)

        data = retstr.getvalue()

        texto = str(data.encode('utf-8'))[2:-7].strip().replace(r'\n', ' ').replace(r'\xc3\xa9', 'é').replace(r'\xc3\x89', 'É').replace(r'\xc3\x93', 'Ó').replace(r'\xc3\xa1', 'á').replace(r'\xc3\xa3', 'ã').replace(r'\xc3\xa7', 'ç').replace(r'\xc3\xb3', 'ó').replace(r'\xc3\xaa', 'ê').replace(r'\xc3\xa2', 'â').replace(r'\xc3\x94', 'Ô').replace(r'\xc3\xad', 'í')
        texto = re.sub(' +', ' ', texto)
        #texto = data
        lista.append({'slide':page_no, 'texto':texto})

        data = ''
        retstr.truncate(0)
        retstr.seek(0)

    page_no += 1

keys = lista[0].keys()

with open('musicas.csv', 'w', newline='') as output_file:
    dict_writer = csv.DictWriter(output_file, keys, delimiter=';')
    dict_writer.writeheader()
    dict_writer.writerows(lista)