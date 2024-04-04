from pptx import Presentation

def getListText(dir):
    file = open(f'{dir}', 'rb')

    prs = Presentation(file)

    text_runs = []

    slide_pos = 0

    for slide in prs.slides:

        anotacao = ''
        if slide.has_notes_slide:
            anotacao = slide.notes_slide.notes_text_frame.text

        slide_pos += 1

        if slide_pos == 1:
            continue

        if slide_pos == len(prs.slides):
            continue

        text_slide = ""
        plain_text = ""

        key_b = False
        key_u = False


        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            cont = 0
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:

                    if (not key_b and run.font.bold):
                        text_slide +="<b>"
                        key_b = True
                    elif (key_b and not run.font.bold):
                        text_slide += "</b>"
                        key_b = False

                    if (not key_u and run.font.underline):
                        text_slide +='<u class="cdx-underline">'
                        key_u = True
                    elif (key_u and not run.font.underline):
                        text_slide += "</u>"
                        key_u = False

                    if cont > 0:
                        text_slide += " " + run.text.strip()
                        plain_text += " " + run.text.strip()
                    else:
                        text_slide += run.text.strip()
                        plain_text += run.text.strip()
                        cont += 1

        if key_b:
            text_slide += "</b>"
        if key_u:
            text_slide += "</u>"

        text_slide = text_slide.replace('  ', ' ')
        plain_text = plain_text.replace('  ', ' ')

        text_runs.append({'pos':slide_pos - 1, 'text-slide':text_slide, 'subtitle':plain_text, 'anotacao':anotacao})


    return text_runs


def getListTextHarpa(dir):

    file = open(f'{dir}', 'rb')

    prs = Presentation(file)

    text_runs = []

    slide_pos = 0

    for slide in prs.slides:

        anotacao = ''
        if slide.has_notes_slide:
            anotacao = slide.notes_slide.notes_text_frame.text

        slide_pos += 1

        if slide_pos == 1:
            continue

        key_c = False

        text_slide = "<b>"
        plain_text = ""
        
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
  
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    if str(run.font.color.rgb) == '0070C0':
                        text_slide += '<span class="cdx-num">' + run.text.lstrip() + ' </span>'
                    elif str(run.font.color.rgb) == 'FF0000':
                        if run.text[0:1].isdigit():
                            text_slide += '<span class="red">' + run.text.lstrip() + ' </span>'
                        else:
                            if not key_c:
                                text_slide += '<span class="red">' + run.text.lstrip()
                                key_c = True
                            else:
                                text_slide += run.text.lstrip()
                    else:
                        text_slide += run.text.lstrip()

                    plain_text += run.text

                if (text_slide != '<b>'):
                    text_slide += "<br>"
                    plain_text += "<br>"
        
        if key_c:
            text_slide += '</span>'    
            key_c = False

        text_slide += '</b>'
        text_runs.append({'pos':slide_pos - 1, 'text-slide':text_slide, 'subtitle':plain_text, 'anotacao':anotacao})
    
    return text_runs