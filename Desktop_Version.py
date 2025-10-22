# pip install PyQt5 PyQtWebEngine


from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEnginePage
from PyQt5.QtCore import Qt, QUrl
import sys

class BrowserWindow(QMainWindow):
    def __init__(self, url):
        super().__init__()
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl(url))  # Converte a string em um QUrl  

        # Abrir a ferramenta de desenvolvedor
        #self.dev_tools = QWebEngineView()
        #self.dev_tools_page = QWebEnginePage(self)
        #self.dev_tools.setPage(self.dev_tools_page)
        #self.browser.page().setDevToolsPage(self.dev_tools_page)
        #self.dev_tools.show()

        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.browser)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)


def get_second_screen_geometry(app):
    screens = app.screens()
    if len(screens) > 1:
        return screens[1].geometry()  # Retorna a geometria do segundo monitor
    return app.primaryScreen().geometry()  # Retorna a geometria do monitor principal como fallback


def main():

    # Verifica se já existe uma instância da aplicação
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    # Configura a URL e abre a janela no segundo monitor
    url = "http://localhost/slide_new"  # URL que será aberta
    second_screen_geometry = get_second_screen_geometry(app)

    window = BrowserWindow(url)
    window.setGeometry(second_screen_geometry)  # Define a posição e tamanho baseados no segundo monitor
    window.showFullScreen()  # Abre em tela cheia
    #window.show()  # Abre a janela

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
