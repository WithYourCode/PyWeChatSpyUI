from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QDesktopWidget,
    QPushButton,
    QLabel,
    QTextBrowser, QMenu, QAction, QTextEdit, QFileDialog, QListWidget, QListWidgetItem, QCheckBox)
from PyQt5.QtGui import QPixmap, QCursor
from PyQt5.QtCore import QSize, QThread, pyqtSignal
from PyWeChatSpy import WeChatSpy
import requests
import sys
from queue import Queue
from time import sleep


contact_list = []
msg_queue = Queue()


def parser(data):
    msg_queue.put(data)


class MsgThread(QThread):
    signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

    def run(self):
        while True:
            if not msg_queue.empty():
                msg = msg_queue.get()
                self.signal.emit(msg)
            else:
                sleep(0.1)


def download_image(url, output):
    resp = requests.get(url)
    if resp.status_code == 200:
        with open(output, "wb") as wf:
            wf.write(resp.content)
        return True
    return False


class ContactWidget(QWidget):
    def __init__(self, nickname):
        super().__init__()
        layout = QHBoxLayout(self)
        checkbox_contact = QCheckBox()
        checkbox_contact.setFixedSize(20, 20)
        layout.addWidget(checkbox_contact)
        label_profilephoto = QLabel(self)
        label_profilephoto.setFixedSize(32, 32)
        default_profilephoto = QPixmap("default.jpg").scaled(32, 32)
        label_profilephoto.setPixmap(default_profilephoto)
        layout.addWidget(label_profilephoto)
        label_nickname = QLabel(self)
        label_nickname.setText(nickname)
        layout.addWidget(label_nickname)


class SpyUI(QWidget):
    def __init__(self):
        super().__init__()
        self.spy = WeChatSpy(parser=parser)
        self.layout_main = QHBoxLayout(self)
        self.layout_left = QVBoxLayout(self)
        self.layout_middle = QVBoxLayout(self)
        self.layout_right = QVBoxLayout(self)
        self.layout_main.addLayout(self.layout_left)
        self.layout_main.addLayout(self.layout_middle)
        self.layout_main.addLayout(self.layout_right)
        self.label_profilephoto = QLabel(self)
        self.TE_contact_search = QTextEdit(self)
        self.LW_contact_list = QListWidget(self)
        self.TB_chat = QTextBrowser(self)
        self.TE_send = QTextEdit(self)
        self.init_ui()

    def init_ui(self):
        # 设置主窗体
        self.resize(858, 608)
        fg = self.frameGeometry()
        center = QDesktopWidget().availableGeometry().center()
        fg.moveCenter(center)
        self.move(fg.topLeft())
        self.setWindowTitle("PyWeChatSpy")
        # 设置登录信息头像
        self.label_profilephoto.setFixedSize(32, 32)
        default_profilephoto = QPixmap("default.jpg").scaled(32, 32)
        self.label_profilephoto.setPixmap(default_profilephoto)
        self.layout_left.addWidget(self.label_profilephoto)
        button_open_wechat = QPushButton(self)
        button_open_wechat.setText("打开\n微信")
        button_open_wechat.clicked.connect(self.open_wechat)
        button_open_wechat.setFixedSize(32, 32)
        self.layout_left.addWidget(button_open_wechat)
        # 联系人列表
        self.TE_contact_search.setFixedSize(250, 24)
        self.layout_middle.addWidget(self.TE_contact_search)
        checkbox_select_all = QCheckBox("全选")
        checkbox_select_all.stateChanged[int].connect(self.select_all_contact)
        self.layout_middle.addWidget(checkbox_select_all)
        self.LW_contact_list.setFixedSize(250, 500)
        self.layout_middle.addWidget(self.LW_contact_list)
        # 聊天区域
        self.TB_chat.setFixedSize(468, 300)
        self.layout_right.addWidget(self.TB_chat)
        # self.TB_chat.move(0, 0)
        layout = QHBoxLayout(self)
        button_file = QPushButton(self)
        button_file.setText("添加文件")
        button_file.clicked.connect(self.insert_file)
        layout.addWidget(button_file)
        self.layout_right.addLayout(layout)
        self.TE_send.setFixedSize(468, 200)
        self.layout_right.addWidget(self.TE_send)
        button_send = QPushButton(self)
        button_send.setText("发送")
        self.layout_right.addWidget(button_send)
        self.setLayout(self.layout_main)
        msg_thread = MsgThread()
        msg_thread.signal.connect(self.parser)
        msg_thread.start()
        self.show()

    def add_contact(self, nickname):
        widget = ContactWidget(nickname)
        item = QListWidgetItem()
        item.setSizeHint(QSize(200, 50))
        self.LW_contact_list.addItem(item)
        self.LW_contact_list.setItemWidget(item, widget)

    def parser(self, data):
        print(data)
        _type = data.pop("type")
        if _type == 1:
            # 登录成功
            # self.label_nickname.setText(data["nickname"])
            # self.label_wechatid.setText(data["wechatid"])
            # self.label_wxid.setText(data["wxid"])
            if download_image(data["profilephoto_url"], "image.jpg"):
                profilephoto = QPixmap("image.jpg").scaled(32, 32)
                self.label_profilephoto.setPixmap(profilephoto)
            self.spy.query_contact_list()
        elif _type == 3:
            for contact in data["data"]:
                contact_list.append(contact)
            if data["total_page"] == data["current_page"]:
                for contact in contact_list:
                    widget = ContactWidget(contact["nickname"])
                    item = QListWidgetItem()
                    item.setSizeHint(QSize(200, 50))
                    self.LW_contact_list.addItem(item)
                    self.LW_contact_list.setItemWidget(item, widget)
        elif _type == 5:
            # 聊天消息
            for msg in data["data"]:
                if msg["msg_type"] == 1:
                    self.TB_chat.append(msg['content'])
                    self.TB_chat.moveCursor(self.TB_chat.textCursor().End)

    def open_wechat(self):
        self.spy.run(background=True)

    def rightMenuShow(self):
        menu = QMenu(self)
        menu.addAction(QAction('回复ta', menu))
        menu.triggered.connect(self.reply)
        menu.exec_(QCursor.pos())

    def reply(self, act):
        print(self.tb_chat.toHtml())
        print(act.text())

    def insert_file(self):
        file_name, file_type = QFileDialog.getOpenFileName(self, "打开文件", "", "*.jpg;;*.png;;All Files(*)")
        self.td_msg_send.append(f"<img src={file_name}>")

    def send_msg(self):
        print(self.td_msg_send.to)

    def select_all_contact(self, state):
        print(state)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    spy = SpyUI()
    sys.exit(app.exec_())
