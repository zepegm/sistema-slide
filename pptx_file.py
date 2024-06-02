import win32com.client
import pythoncom

class ppt:
    def __init__(self, caminho):
        self.app = win32com.client.Dispatch("PowerPoint.Application", pythoncom.CoInitialize())
        self.app.Presentations.Open(FileName=caminho, WithWindow=False)
        self.objCOM = self.app.Presentations(caminho)

        print(self.objCOM)


    def convertToListJPG(self):
        try:
            for sld in self.objCOM.Presentation.Slides:
                sld.Export(os.path.dirname(os.path.realpath(__file__)) + r'\static\images\SlidesPPTX' + r'\Slide' + str(sld.SlideIndex) + '.jpg', 'JPG')

            return True
        except Exception as error:
            print("An exception occurred:", error) # An exception occurred: division by zero
            return False