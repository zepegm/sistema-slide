# pip install PyQt5 PyQtWebEngine


from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, QUrl
import sys
import os


class BrowserWindow(QMainWindow):
    def __init__(self, url):
        super().__init__()
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl(url))  # Converte a string em um QUrl

        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.browser)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)


# Variável global para rastrear a janela principal
window_instance = None

def configure_environment():
    # Opcional: Configurações para evitar problemas com cache e GPU
    os.environ["QTWEBENGINE_DISABLE_GPU_THREAD"] = "1"
    os.environ["QTWEBENGINE_DISABLE_SHADER_CACHE"] = "1"
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disk-cache-size=0"

def get_second_screen_geometry(app):
    screens = app.screens()
    #if len(screens) > 1:
        #return screens[1].geometry()  # Retorna a geometria do segundo monitor
    return app.primaryScreen().geometry()  # Retorna a geometria do monitor principal como fallback


def main():

    global window_instance

    # Configura o ambiente do Qt WebEngine
    configure_environment()

    # Verifica se já existe uma instância da aplicação
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Se a janela já existir, traga-a para o foco
    if window_instance is not None and window_instance.isVisible():
        print("Janela já está aberta. Trazendo para o foco.")
        window_instance.raise_()
        window_instance.activateWindow()
        return
    else:
        print (window_instance)

    # Configura a URL e abre a janela no segundo monitor
    url = "http://localhost/slide"  # URL que será aberta
    second_screen_geometry = get_second_screen_geometry(app)

    window = BrowserWindow(url)
    window.setGeometry(second_screen_geometry)  # Define a posição e tamanho baseados no segundo monitor
    window.showFullScreen()  # Abre em tela cheia
    window_instance = window

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
