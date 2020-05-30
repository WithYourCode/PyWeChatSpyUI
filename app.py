from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QDesktopWidget,
    QPushButton,
    QLabel,
    QTextBrowser, QMenu, QAction, QTextEdit, QFileDialog, QListWidget, QListWidgetItem, QCheckBox)
from PyQt5.QtGui import QPixmap, QCursor
from PyQt5.QtCore import Qt
from PyWeChatSpy import WeChatSpy
import requests
import sys


def download_image(url, output):
    resp = requests.get(url)
    if resp.status_code == 200:
        with open(output, "wb") as wf:
            wf.write(resp.content)
        return True
    return False


class ContactUI(QWidget):
    def __init__(self):
        super().__init__()


class SpyUI(QWidget):
    def __init__(self):
        super().__init__()
        self.spy = WeChatSpy(parser=self.parser)
        self.label_profile_photo = QLabel(self)
        self.label_nickname = QLabel(self)
        self.label_wechatid = QLabel(self)
        self.label_wxid = QLabel(self)
        self.tb_chat = QTextBrowser(self)
        self.td_msg_send = QTextEdit(self)
        self.lw_contact = QListWidget(self)
        self.init_ui()

    def init_ui(self):
        # 设置主窗体
        self.resize(800, 600)
        fg = self.frameGeometry()
        center = QDesktopWidget().availableGeometry().center()
        fg.moveCenter(center)
        self.move(fg.topLeft())
        self.setWindowTitle("PyWeChatSpy")
        # 设置头像
        self.label_profile_photo.setFixedSize(132, 132)
        self.label_profile_photo.move(0, 0)
        default_profilephoto = QPixmap("default.png").scaled(132, 132)
        self.label_profile_photo.setPixmap(default_profilephoto)
        # 昵称
        self.label_nickname.setText("昵称")
        self.label_nickname.setFixedWidth(200)
        self.label_nickname.move(132, 0)
        # 微信号
        self.label_wechatid.setText("微信号")
        self.label_wechatid.setFixedWidth(200)
        self.label_wechatid.move(132, 44)
        # wxid
        self.label_wxid.setText("WXID")
        self.label_wxid.setFixedWidth(200)
        self.label_wxid.move(132, 88)
        # 联系人列表
        cb_select_all = QCheckBox("全选(selectAll)")
        cb_select_all.stateChanged[int].connect(self.select_all_contact)  #
        item = QListWidgetItem(self.lw_contact)
        self.lw_contact.setItemWidget(item, cb_select_all)
        self.lw_contact.setFixedSize(332, 400)
        self.lw_contact.move(0, 200)
        # 聊天框
        self.tb_chat.setFixedSize(468, 300)
        self.tb_chat.move(332, 0)
        self.tb_chat.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tb_chat.customContextMenuRequested.connect(self.rightMenuShow)  # 开放右键策略
        # 消息发送框
        btn_add_file = QPushButton(self)
        btn_add_file.setText("插入文件")
        btn_add_file.clicked.connect(self.add_file)
        btn_add_file.move(331, 300)
        self.td_msg_send.setFixedSize(468, 200)
        self.td_msg_send.move(332, 334)
        btn_send = QPushButton(self)
        btn_send.setText("发送")
        btn_send.clicked.connect(self.send_msg)
        btn_send.move(331, 534)
        # 打开微信按钮
        btn = QPushButton("打开微信", self)
        btn.clicked.connect(self.open_wechat)
        btn.move(0, 132)
        self.show()

    def parser(self, data):
        print(data)
        _type = data.pop("type")
        if _type == 1:
            # 登录成功
            self.label_nickname.setText(data["nickname"])
            self.label_wechatid.setText(data["wechatid"])
            self.label_wxid.setText(data["wxid"])
            if download_image(data["profilephoto_url"], "image.jpg"):
                profilephoto = QPixmap("image.jpg")
                self.label_profile_photo.setPixmap(profilephoto)
        elif _type == 5:
            # 聊天消息
            for msg in data["data"]:
                if msg["msg_type"] == 1:
                    self.tb_chat.append(msg['content'])
                    self.tb_chat.moveCursor(self.tb_chat.textCursor().End)

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

    def add_file(self):
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
