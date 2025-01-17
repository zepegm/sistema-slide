# pip install PyQt5 PyQtWebEngine


from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, QUrl
import sys

def get_second_screen_geometry(app):
    screens = app.screens()
    if len(screens) > 1:
        return screens[1].geometry()  # Retorna a geometria do segundo monitor
    return app.primaryScreen().geometry()  # Retorna a geometria do monitor principal como fallback

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

def main():
    # Verifica se já existe uma instância da aplicação
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Fecha todas as janelas abertas, se existirem
    for widget in QApplication.topLevelWidgets():
        if isinstance(widget, BrowserWindow):
            widget.close()
    
    # Configura a URL e abre a janela no segundo monitor
    url = "https://www.google.com"  # URL que será aberta
    second_screen_geometry = get_second_screen_geometry(app)

    window = BrowserWindow(url)
    window.setGeometry(second_screen_geometry)  # Define a posição e tamanho baseados no segundo monitor
    window.showFullScreen()  # Abre em tela cheia

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()