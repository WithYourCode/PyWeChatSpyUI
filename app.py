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
from PyQt5.QtCore import QSize, QThread, pyqtSignal, Qt
from PyWeChatSpy import WeChatSpy
from lxml import etree
import requests
import sys
from queue import Queue
from time import sleep
from threading import Thread
from copy import deepcopy


CONTACT_LIST = []
dw_contact_list = []
cb_contact_list = []
msg_queue = Queue()
wxid_contact = {}
contact_filter = ("qmessage", "qqmail", "tmessage", "medianote", "floatbottle", "fmessage")


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
    def __init__(self, nickname, select_changed):
        super().__init__()
        layout = QHBoxLayout(self)
        checkbox_contact = QCheckBox()
        checkbox_contact.setFixedSize(20, 20)
        checkbox_contact.stateChanged[int].connect(select_changed)
        cb_contact_list.append(checkbox_contact)
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
        self.CB_select_all_contact = QCheckBox("全选")
        self.CB_select_all_contact.setCheckState(Qt.Unchecked)
        self.init_ui()

    def init_ui(self):
        # 设置主窗体
        self.resize(858, 608)
        fg = self.frameGeometry()
        center = QDesktopWidget().availableGeometry().center()
        fg.moveCenter(center)
        self.move(fg.topLeft())
        self.setWindowTitle("PyWeChatSpyUI Beta 1.0.0")
        # 设置登录信息头像
        self.label_profilephoto.setFixedSize(32, 32)
        default_profilephoto = QPixmap("default.jpg").scaled(32, 32)
        self.label_profilephoto.setPixmap(default_profilephoto)
        self.layout_left.addWidget(self.label_profilephoto)
        button_open_wechat = QPushButton(self)
        button_open_wechat.setText("打开\n微信")
        button_open_wechat.clicked.connect(lambda: self.spy.run(background=True))
        button_open_wechat.setFixedSize(32, 32)
        self.layout_left.addWidget(button_open_wechat)
        # 联系人列表
        self.TE_contact_search.setFixedSize(250, 24)
        self.TE_contact_search.textChanged.connect(self.search_contact)
        self.TE_contact_search.setPlaceholderText("搜索")
        self.layout_middle.addWidget(self.TE_contact_search)
        self.CB_select_all_contact.stateChanged[int].connect(self.contact_select_all)
        self.layout_middle.addWidget(self.CB_select_all_contact)
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
        button_send.clicked.connect(self.send_msg)
        self.layout_right.addWidget(button_send)
        self.setLayout(self.layout_main)
        msg_thread = MsgThread()
        msg_thread.signal.connect(self.parser)
        msg_thread.start()
        self.show()

    def parser(self, data):
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
                wxid_contact[contact["wxid"]] = contact
                if (not contact["wxid"].startswith("gh_")) and (contact["wxid"] not in contact_filter):
                    CONTACT_LIST.append(contact)
                    dw_contact_list.append(contact)
            if data["total_page"] == data["current_page"]:
                self.refresh_contact_list()
        elif _type == 5:
            # 聊天消息
            for msg in data["data"]:
                speaker = ""
                wxid = msg.get("wxid1")
                if contact := wxid_contact.get(wxid):
                    speaker = contact["nickname"]
                    if remark := contact.get("remark"):
                        speaker = f"{speaker}({remark})"
                if msg["msg_type"] == 1:
                    self.TB_chat.append(f"{speaker}:{msg['content']}")
                    self.TB_chat.moveCursor(self.TB_chat.textCursor().End)

    def rightMenuShow(self):
        menu = QMenu(self)
        menu.addAction(QAction('回复ta', menu))
        menu.triggered.connect(self.reply)
        menu.exec_(QCursor.pos())

    def insert_file(self):
        file_name, file_type = QFileDialog.getOpenFileName(self, "打开文件", "", "All Files(*)")
        self.TE_send.append(f"<img src={file_name}>")

    def send_msg(self):
        content_html = self.TE_send.toHtml()
        content_etree = etree.HTML(content_html)
        lines = content_etree.xpath("//p")
        msg_list = []
        text_list = []
        for line in lines:
            if line.xpath("*"):
                file_path = line.xpath("img/@src")
                if file_path:
                    file_path = file_path[0]
                    if text_list:
                        msg_list.append((5, "\n".join(text_list)))
                        text_list.clear()
                    msg_list.append((6, file_path))
            text = line.xpath("text()")
            if text:
                text_list.append(text[0])
        else:
            if text_list:
                msg_list.append((5, "\n".join(text_list)))
                text_list.clear()

        def _send():
            for i, cb in enumerate(cb_contact_list):
                if cb.checkState():
                    contact = dw_contact_list[i]
                    for msg in msg_list:
                        if msg[0] == 5:
                            self.spy.send_text(contact["wxid"], msg[1])
                        elif msg[0] == 6:
                            self.spy.send_file(contact["wxid"], msg[1])
                        sleep(3)
                    sleep(5)

        t = Thread(target=_send)
        t.daemon = True
        t.start()
        self.TE_send.clear()

    def contact_select_all(self, state):
        if state == 2:
            for checkbox in cb_contact_list:
                checkbox.setCheckState(2)
        elif state == 0:
            for checkbox in cb_contact_list:
                checkbox.setCheckState(0)

    def contact_select_changed(self, state):
        checkbox = self.sender()
        if state:
            if len([cb for cb in cb_contact_list if cb.checkState()]) == self.LW_contact_list.count():
                # 0 不选中， 1 部分选中，2 全选中 #Qt.Unchecked #Qt.PartiallyChecked #Qt.Checked
                self.CB_select_all_contact.setCheckState(2)
            else:
                self.CB_select_all_contact.setCheckState(1)
        else:
            if len([cb for cb in cb_contact_list if cb.checkState()]):
                self.CB_select_all_contact.setCheckState(1)
            else:
                self.CB_select_all_contact.setCheckState(0)

    def refresh_contact_list(self):
        cb_contact_list.clear()
        self.LW_contact_list.clear()
        for contact in dw_contact_list:
            nickname = contact["nickname"]
            if remark := contact.get("remark"):
                nickname = f"{nickname}({remark})"
            if count := contact.get("member_count"):
                nickname = f"{nickname}[{count}]"
            widget = ContactWidget(nickname, self.contact_select_changed)
            item = QListWidgetItem()
            item.setSizeHint(QSize(200, 50))
            self.LW_contact_list.addItem(item)
            self.LW_contact_list.setItemWidget(item, widget)

    def search_contact(self):
        global dw_contact_list
        search_key = self.TE_contact_search.toPlainText()
        dw_contact_list.clear()
        if search_key:
            for contact in CONTACT_LIST:
                if search_key in contact["nickname"]:
                    dw_contact_list.append(contact)
                elif remark := contact.get("remark"):
                    if search_key in remark:
                        dw_contact_list.append(contact)
            self.refresh_contact_list()
        elif self.LW_contact_list.count() != len(CONTACT_LIST):
            dw_contact_list = deepcopy(CONTACT_LIST)
            self.refresh_contact_list()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    spy = SpyUI()
    sys.exit(app.exec_())
