from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hello, World!")

        button = QPushButton("Exit")
        button.pressed.connect(self.close)

        self.setCentralWidget(button)
        self.show()

def main():    
    app = QApplication([])
    window = MainWindow()
    app.exec()
