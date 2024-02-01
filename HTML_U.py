from bs4 import BeautifulSoup

def converHTML_to_List(string):
    soup = BeautifulSoup(string, 'lxml')
    tag = soup.body.p

    if (tag is None):
        tag = soup.body

    paragrafo = []
    # Print each string recursively
    for element in tag:

        linhas = []
        for txt in element.stripped_strings:
            linhas.append(txt)

        if str(element.name) == 'None':
            elemento = "'None'"
        else:
            elemento = element.name

        if (elemento == 'span'):
            if element.get('class')[0] == 'ignore':
                elemento = 'ignore'

        for child in element:
            try:
                if elemento == 'mark' and child.name == 'u':
                    elemento = 'mark-u'
                elif elemento == 'u' and child.name =='b':
                    elemento = 'u-b'
                elif elemento == 'b' and child.name == 'u':
                    elemento = 'u-b'
            except:
                pass

        paragrafo.append({'css':elemento, 'text':linhas})
    
    return paragrafo


string = '<mark class="cdx-marker"><u class="cdx-underline">Volta no começo e repete novamente.</u></mark>'

#print(converHTML_to_List(string))