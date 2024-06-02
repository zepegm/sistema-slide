import win32com.client
import pythoncom
import os


def ppt_to_png(presentation_path, slides_folder):
    Application = win32com.client.Dispatch("PowerPoint.Application", pythoncom.CoInitialize())
    lista = []

    try:
        # Open the presentation without making it visible
        Presentation = Application.Presentations.Open(FileName=presentation_path, WithWindow=False)

        # Rodando slide por slide
        for i, slide in enumerate(Presentation.Slides):
            # exportando imagem
            image_path = os.path.join(slides_folder, f"{i}.png")
            slide.Export(image_path, "PNG")

            # pegando texto pra transformar em legenda
            texto = ''

            if slide.Shapes(1).HasTextFrame:
                texto = slide.Shapes(1).TextFrame.TextRange.Text

                if texto == '':
                    if slide.Shapes(2).HasTextFrame:
                        texto = slide.Shapes(2).TextFrame.TextRange.Text

            elif slide.Shapes(2).HasTextFrame:
                texto = slide.Shapes(2).TextFrame.TextRange.Text

                
            texto = texto.replace(chr(11), ' ').replace(chr(13), '<br>').replace('  ', ' ')
            lista.append(texto)


        # Close the presentation
        Presentation.Close()

    except Exception as e:
        print(f"An error occurred: {e}")

    return lista