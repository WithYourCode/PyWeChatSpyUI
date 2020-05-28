from PyQt5.QtWidgets import QApplication, QWidget, QDesktopWidget, QPushButton,QLabel, QHBoxLayout
from PyQt5.QtGui import QPixmap
from PyWeChatSpy import WeChatSpy
import requests
import sys


def download_image(url, optput):
    resp = requests.get(url)
    if resp.status_code == 200:
        with open(optput, "wb") as wf:
            wf.write(resp.content)
        return True
    return False


class SpyUI(QWidget):
    def __init__(self):
        super().__init__()
        self.spy = WeChatSpy(parser=self.parser)
        self.init_ui()

    def init_ui(self):
        self.resize(800, 600)
        fg = self.frameGeometry()
        center = QDesktopWidget().availableGeometry().center()
        fg.moveCenter(center)
        self.move(fg.topLeft())
        self.setWindowTitle("PyWeChatSpy")
        btn = QPushButton("打开微信", self)
        btn.clicked.connect(self.open_wechat)
        self.hbox = QHBoxLayout(self)
        self.setLayout(self.hbox)
        self.show()

    def parser(self, data):
        _type = data.pop("type")
        if _type == 1:
            # 登录成功
            profilephoto_url = data["profilephoto_url"]
            if download_image(profilephoto_url, "image.jpg"):
                pixmap = QPixmap("image.png")
                lbl = QLabel(self)
                lbl.setPixmap(pixmap)
                self.hbox.addWidget(lbl)


    def open_wechat(self):
        self.spy.run(background=True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    spy = SpyUI()
    sys.exit(app.exec_())
