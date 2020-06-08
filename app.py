from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QDesktopWidget,
    QPushButton,
    QLabel,
    QTabWidget,
    QMenu, QAction, QTextEdit, QFileDialog, QListWidget, QListWidgetItem, QCheckBox)
from PyQt5.QtGui import QPixmap, QCursor
from PyQt5.QtCore import QSize, QThread, pyqtSignal, Qt, QPoint
from PyWeChatSpy import WeChatSpy
from lxml import etree
import requests
import sys
from queue import Queue
from time import sleep
from threading import Thread
import os
import re


FRIEND_LIST = []
GROUP_LIST = []
OFFICE_LIST = []
cb_contact_list = []
contact_need_details = []
current_row = 0
msg_queue = Queue()
wxid_contact = {}
contact_filter = ("qmessage", "qqmail", "tmessage", "medianote", "floatbottle", "fmessage")


def parser(data: dict):
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


def download_image(url: str, output: str):
    resp = requests.get(url)
    if resp.status_code == 200:
        with open(output, "wb") as wf:
            wf.write(resp.content)
        return True
    return False


class ContactWidget(QWidget):
    def __init__(self, contact: dict, select_changed: classmethod):
        super().__init__()
        layout = QHBoxLayout(self)
        checkbox_contact = QCheckBox()
        checkbox_contact.__setattr__("wxid", contact["wxid"])
        checkbox_contact.setFixedSize(20, 20)
        checkbox_contact.stateChanged[int].connect(select_changed)
        cb_contact_list.append(checkbox_contact)
        layout.addWidget(checkbox_contact)
        label_profilephoto = QLabel(self)
        label_profilephoto.setFixedSize(32, 32)
        profilephoto_path = "profilephotos/default.jpg"
        if os.path.exists(f"profilephotos/{contact['wxid']}.jpg"):
            profilephoto_path = f"profilephotos/{contact['wxid']}.jpg"
        default_profilephoto = QPixmap(profilephoto_path).scaled(32, 32)
        label_profilephoto.setPixmap(default_profilephoto)
        layout.addWidget(label_profilephoto)
        label_nickname = QLabel(self)
        nickname = contact["nickname"]
        if remark := contact.get("remark"):
            nickname = f"{nickname}({remark})"
        if count := contact.get("member_count"):
            nickname = f"{nickname}[{count}]"
        label_nickname.setText(nickname)
        layout.addWidget(label_nickname)


class ContactSearchWidget(QWidget):
    def __init__(self, contact: dict):
        super().__init__()
        layout = QHBoxLayout(self)
        label_profilephoto = QLabel(self)
        label_profilephoto.setFixedSize(32, 32)
        profilephoto_path = "profilephotos/default.jpg"
        if os.path.exists(f"profilephotos/{contact['wxid']}.jpg"):
            profilephoto_path = f"profilephotos/{contact['wxid']}.jpg"
        default_profilephoto = QPixmap(profilephoto_path).scaled(32, 32)
        label_profilephoto.setPixmap(default_profilephoto)
        layout.addWidget(label_profilephoto)
        label_nickname = QLabel(self)
        nickname = contact["nickname"]
        if remark := contact.get("remark"):
            nickname = f"{nickname}({remark})"
        if count := contact.get("member_count"):
            nickname = f"{nickname}[{count}]"
        label_nickname.setText(nickname)
        layout.addWidget(label_nickname)


class MessageWidget(QWidget):
    def __init__(self, message: dict):
        super().__init__()
        layout_main = QHBoxLayout(self)
        layout_side = QVBoxLayout(self)
        label_content = QLabel(self)
        label_content.setWordWrap(True)
        label_content.adjustSize()
        label_content.setFixedWidth(300)
        label_speaker = QLabel(self)
        if message["self"]:
            layout_main.setAlignment(Qt.AlignRight)
            label_content.setAlignment(Qt.AlignRight)
            label_speaker.setAlignment(Qt.AlignRight)
        else:
            layout_main.setAlignment(Qt.AlignLeft)
            label_content.setAlignment(Qt.AlignLeft)
            label_speaker.setAlignment(Qt.AlignLeft)
        label_profilephoto = QLabel(self)
        label_profilephoto.setFixedSize(32, 32)
        profilephoto_path = "profilephotos/default.jpg"
        if os.path.exists(f"profilephotos/{message['wxid1']}.jpg"):
            profilephoto_path = f"profilephotos/{message['wxid1']}.jpg"
        default_profilephoto = QPixmap(profilephoto_path).scaled(32, 32)
        label_profilephoto.setPixmap(default_profilephoto)
        speaker = ""
        wxid1 = message["wxid1"]
        if contact := wxid_contact.get(wxid1):
            speaker = contact["nickname"]
            if remark := contact.get("remark"):
                speaker = f"{speaker}({remark})"
        label_speaker.setText(speaker)
        layout_side.addWidget(label_speaker)
        if message["msg_type"] == 1:
            label_content.setText(message["content"])
        else:
            label_content.setText("不支持的消息类型，请在手机上查看")
        layout_side.addWidget(label_content)
        if message["self"]:
            layout_main.addLayout(layout_side)
            layout_main.addWidget(label_profilephoto)
        else:
            layout_main.addWidget(label_profilephoto)
            layout_main.addLayout(layout_side)


class SettingWidget(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.setWindowTitle("设置")
        self.parent = parent
        self.tab_widget = QTabWidget(self)
        self.tab_widget.setTabPosition(QTabWidget.West)
        self.tab_widget.setFixedSize(300, 200)
        self.tab_common = QListWidget(self)
        self.tab_widget.addTab(self.tab_common, "通用")
        item = QListWidgetItem()
        item.setSizeHint(QSize(200, 50))
        self.cb_auto_accept = QCheckBox("自动通过好友请求")
        self.tab_common.addItem(item)
        self.tab_common.setItemWidget(item, self.cb_auto_accept)


class SendTextEdit(QTextEdit):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def keyPressEvent(self, event):
        QTextEdit.keyPressEvent(self, event)
        if event.key() == Qt.Key_Return:
            if QApplication.keyboardModifiers() == Qt.ControlModifier:
                self.append("")
            else:
                self.parent.send_msg()


class SpyUI(QWidget):
    def __init__(self):
        super().__init__()
        self.spy = WeChatSpy(parser=parser, key="18d421169d93611a5584affac335e690")
        self.layout_main = QHBoxLayout(self)
        self.layout_left = QVBoxLayout(self)
        self.layout_middle = QVBoxLayout(self)
        self.layout_right = QVBoxLayout(self)
        self.layout_main.addLayout(self.layout_left)
        self.layout_main.addLayout(self.layout_middle)
        self.layout_main.addLayout(self.layout_right)
        self.label_profilephoto = QLabel(self)
        self.TE_contact_search = QTextEdit(self)
        self.LW_contact_search = QListWidget(self)
        self.TW_contact = QTabWidget(self)
        self.tab_friend = QListWidget()
        self.tab_group = QListWidget()
        self.tab_office = QListWidget()
        self.LW_chat_record = QListWidget(self)
        self.TE_send = SendTextEdit(self)
        self.CB_select_all_contact = QCheckBox("全选")
        self.CB_select_all_contact.setCheckState(Qt.Unchecked)
        self.setting_widget = SettingWidget(self)
        self.wxid = ""
        self.init_ui()

    def init_ui(self):
        fg = self.frameGeometry()
        center = QDesktopWidget().availableGeometry().center()
        fg.moveCenter(center)
        # 设置窗体
        self.setting_widget.resize(300, 200)
        self.setting_widget.move(fg.topLeft())
        self.setting_widget.hide()
        # 主窗体
        self.resize(858, 608)
        self.move(fg.topLeft())
        self.setWindowTitle("PyWeChatSpyUI Beta 1.3.2")
        # 设置登录信息头像
        self.label_profilephoto.setFixedSize(32, 32)
        default_profilephoto = QPixmap("profilephotos/default.jpg").scaled(32, 32)
        self.label_profilephoto.setPixmap(default_profilephoto)
        self.layout_left.addWidget(self.label_profilephoto)
        button_open_wechat = QPushButton(self)
        button_open_wechat.setText("打开\n微信")
        button_open_wechat.clicked.connect(lambda: self.spy.run(background=True))
        button_open_wechat.setFixedSize(32, 32)
        button_settings = QPushButton(self)
        button_settings.setText("设置")
        button_settings.setFixedSize(32, 32)
        button_settings.clicked.connect(self.setting_widget.show)
        self.layout_left.addWidget(button_open_wechat)
        self.layout_left.addWidget(button_settings)
        # 联系人列表
        self.TW_contact.currentChanged["int"].connect(self.tab_changed)
        self.TW_contact.addTab(self.tab_friend, "好友")
        self.TW_contact.addTab(self.tab_group, "群聊")
        self.TW_contact.addTab(self.tab_office, "公众号")
        self.tab_friend.itemClicked.connect(self.contact_clicked)
        self.tab_group.itemClicked.connect(self.contact_clicked)
        self.tab_office.itemClicked.connect(self.contact_clicked)
        self.TE_contact_search.setFixedSize(250, 24)
        self.TE_contact_search.textChanged.connect(self.search_contact)
        self.TE_contact_search.setPlaceholderText("搜索")
        self.LW_contact_search.setFixedSize(250, 200)
        self.LW_contact_search.itemClicked.connect(self.contact_search_clicked)
        self.layout_middle.addWidget(self.TE_contact_search)
        self.CB_select_all_contact.stateChanged[int].connect(self.contact_select_all)
        self.layout_middle.addWidget(self.CB_select_all_contact)
        self.layout_middle.addWidget(self.TW_contact)
        # 聊天区域
        self.LW_chat_record.setFixedSize(468, 400)
        self.LW_chat_record.setContextMenuPolicy(3)
        self.LW_chat_record.customContextMenuRequested[QPoint].connect(self.rightMenuShow)
        self.layout_right.addWidget(self.LW_chat_record)
        layout = QHBoxLayout(self)
        button_file = QPushButton(self)
        button_file.setText("添加文件")
        button_file.clicked.connect(self.insert_file)
        layout.addWidget(button_file)
        self.layout_right.addLayout(layout)
        self.TE_send.setFixedSize(468, 100)
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
        self.LW_contact_search.raise_()
        self.LW_contact_search.move(self.TE_contact_search.x(), self.TE_contact_search.y() + 24)
        self.LW_contact_search.hide()

    def parser(self, data: dict):
        _type = data.pop("type")
        if _type == 1:
            # 登录成功
            self.wxid = data["wxid"]
            profilephoto_path = f"profilephotos/{data['wxid']}.jpg"
            if not os.path.exists(profilephoto_path):
                if not download_image(data["profilephoto_url"], profilephoto_path):
                    profilephoto_path = "profilephotos/default.jpg"
            profilephoto = QPixmap(profilephoto_path).scaled(32, 32)
            self.label_profilephoto.setPixmap(profilephoto)
            self.spy.query_contact_list()
        elif _type == 2:
            if profilephoto_url := data.get("profilephoto_url"):
                download_image(profilephoto_url, f"profilephotos/{data['wxid']}.jpg")
            if contact_need_details:
                wxid = contact_need_details.pop()
                self.spy.query_contact_details(wxid)
            else:
                self.refresh_contact_list()
        elif _type == 3:
            for contact in data["data"]:
                wxid_contact[contact["wxid"]] = contact
                if contact["wxid"] not in contact_filter:
                    if not os.path.exists(f"profilephotos/{contact['wxid']}.jpg"):
                        contact_need_details.append(contact["wxid"])
                    if contact["wxid"].endswith("chatroom"):
                        GROUP_LIST.append(contact)
                    elif contact["wxid"].startswith("gh_"):
                        OFFICE_LIST.append(contact)
                    else:
                        FRIEND_LIST.append(contact)
            if data["total_page"] == data["current_page"]:
                self.refresh_contact_list()
                if contact_need_details:
                    wxid = contact_need_details.pop()
                    self.spy.query_contact_details(wxid)
        elif _type == 5:
            # 聊天消息
            for msg in data["data"]:
                if msg["msg_type"] == 37 and self.setting_widget.cb_auto_accept.checkState():
                    encryptusername = re.search("(?<=encryptusername=\").*?(?=\")", msg["content"]).group()
                    ticket = re.search("(?<=ticket=\").*?(?=\")", msg["content"]).group()
                    self.spy.accept_new_contact(encryptusername, ticket)
                else:
                    widget = MessageWidget(msg)
                    item = QListWidgetItem()
                    item.__setattr__("wxid1", msg["wxid1"])
                    item.__setattr__("wxid2", "")
                    item.__setattr__("content", "")
                    if wxid2 := msg.get("wxid2"):
                        item.__setattr__("wxid2", wxid2)
                    if msg["msg_type"] == 1 or msg["msg_type"] == 1000:
                        item.__setattr__("content", msg["content"])
                        item.setToolTip(msg["content"])
                    item.setSizeHint(QSize(234, 65))
                    self.LW_chat_record.addItem(item)
                    self.LW_chat_record.setItemWidget(item, widget)
                    self.LW_chat_record.setCurrentRow(self.LW_chat_record.count() - 1)

    def refresh_contact_list(self):
        cb_contact_list.clear()
        if self.TW_contact.currentIndex() == 0:
            self.tab_friend.clear()
            _contact_list = FRIEND_LIST
        elif self.TW_contact.currentIndex() == 1:
            self.tab_group.clear()
            _contact_list = GROUP_LIST
        else:
            self.tab_office.clear()
            _contact_list = OFFICE_LIST
        for i, contact in enumerate(_contact_list):
            widget = ContactWidget(contact, self.contact_select_changed)
            item = QListWidgetItem()
            item.setSizeHint(QSize(200, 50))
            item.__setattr__("wxid", contact["wxid"])
            item.__setattr__("row", i)
            if self.TW_contact.currentIndex() == 0:
                self.tab_friend.addItem(item)
                self.tab_friend.setItemWidget(item, widget)
            elif self.TW_contact.currentIndex() == 1:
                self.tab_group.addItem(item)
                self.tab_group.setItemWidget(item, widget)
            else:
                self.tab_office.addItem(item)
                self.tab_office.setItemWidget(item, widget)
        if current_row:
            if self.TW_contact.currentIndex() == 0:
                self.tab_friend.setCurrentRow(current_row)
            elif self.TW_contact.currentIndex() == 1:
                self.tab_group.setCurrentRow(current_row)
            else:
                self.tab_office.setCurrentRow(current_row)

    def tab_changed(self, index: int):
        self.TE_contact_search.clear()
        self.CB_select_all_contact.setCheckState(Qt.Unchecked)
        self.refresh_contact_list()

    def rightMenuShow(self, position: QPoint):
        item = self.LW_chat_record.itemAt(position)
        menu = QMenu(self)
        menu.addAction(QAction('回复ta', menu))
        menu.triggered.connect(lambda: self.reply(item))
        menu.exec_(QCursor.pos())

    def insert_file(self):
        file_name, file_type = QFileDialog.getOpenFileName(self, "打开文件", "", "All Files(*)")
        self.TE_send.append(f"<img src={file_name}>")

    def send_msg(self):
        content_html = self.TE_send.toHtml()
        content_html = re.sub("<span.*?>", "", content_html)
        content_html = re.sub("</span>", "", content_html)
        content_html = re.sub("<a.*?>", "", content_html)
        content_html = re.sub("</a>", "", content_html)
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
            wxid_list = [cb.wxid for cb in cb_contact_list if cb.checkState()]
            for wxid in wxid_list:
                for msg in msg_list:
                    if msg[0] == 5:
                        self.spy.send_text(wxid, msg[1])
                    elif msg[0] == 6:
                        self.spy.send_file(wxid, msg[1])
                    sleep(3)
                sleep(5)

        t = Thread(target=_send)
        t.daemon = True
        t.start()
        self.TE_send.clear()

    def contact_select_all(self, state: int):
        if state == 2:
            for cb in cb_contact_list:
                cb.setCheckState(2)
        elif state == 0:
            for cb in cb_contact_list:
                cb.setCheckState(0)

    def contact_select_changed(self, state):
        checkbox = self.sender()
        if state:
            if self.TW_contact.currentIndex() == 0:
                if len([cb for cb in cb_contact_list if cb.checkState()]) == self.tab_friend.count():
                    # 0 不选中， 1 部分选中，2 全选中 #Qt.Unchecked #Qt.PartiallyChecked #Qt.Checked
                    self.CB_select_all_contact.setCheckState(2)
                else:
                    self.CB_select_all_contact.setCheckState(1)
            elif self.TW_contact.currentIndex() == 1:
                if len([cb for cb in cb_contact_list if cb.checkState()]) == self.tab_group.count():
                    self.CB_select_all_contact.setCheckState(2)
                else:
                    self.CB_select_all_contact.setCheckState(1)
            else:
                if len([cb for cb in cb_contact_list if cb.checkState()]) == self.tab_office.count():
                    self.CB_select_all_contact.setCheckState(2)
                else:
                    self.CB_select_all_contact.setCheckState(1)
        else:
            if len([cb for cb in cb_contact_list if cb.checkState()]):
                self.CB_select_all_contact.setCheckState(1)
            else:
                self.CB_select_all_contact.setCheckState(0)

    def search_contact(self):
        search_key = self.TE_contact_search.toPlainText()
        if search_key:
            if self.TW_contact.currentIndex() == 0:
                _contact_list = FRIEND_LIST
            elif self.TW_contact.currentIndex() == 1:
                _contact_list = GROUP_LIST
            else:
                _contact_list = OFFICE_LIST
            _list = []
            for contact in _contact_list:
                if search_key in contact["nickname"]:
                    _list.append(contact)
                elif remark := contact.get("remark"):
                    if search_key in remark:
                        _list.append(contact)
            self.LW_contact_search.clear()
            if _list:
                for contact in _list:
                    widget = ContactSearchWidget(contact)
                    item = QListWidgetItem()
                    item.setSizeHint(QSize(200, 50))
                    item.__setattr__("wxid", contact["wxid"])
                    self.LW_contact_search.addItem(item)
                    self.LW_contact_search.setItemWidget(item, widget)
                self.LW_contact_search.show()
                _list.clear()
            else:
                self.LW_contact_search.hide()
        else:
            self.LW_contact_search.hide()

    def contact_clicked(self, item: QListWidgetItem):
        global current_row
        current_row = item.row
        self.spy.query_contact_details(item.wxid)

    def contact_search_clicked(self, item: QListWidgetItem):
        if self.TW_contact.currentIndex() == 0:
            for i in range(self.tab_friend.count()):
                _item = self.tab_friend.item(i)
                if item.wxid == _item.wxid:
                    self.tab_friend.setCurrentRow(i)
                    break
        elif self.TW_contact.currentIndex() == 1:
            for i in range(self.tab_group.count()):
                _item = self.tab_group.item(i)
                if item.wxid == _item.wxid:
                    self.tab_group.setCurrentRow(i)
                    break
        else:
            for i in range(self.tab_office.count()):
                _item = self.tab_office.item(i)
                if item.wxid == _item.wxid:
                    self.tab_office.setCurrentRow(i)
                    break
        self.LW_contact_search.hide()
        self.LW_contact_search.clear()

    def reply(self, item: QListWidgetItem):
        self.CB_select_all_contact.setCheckState(Qt.Unchecked)
        if item.wxid1.endswith("chatroom"):
            self.TW_contact.setCurrentIndex(1)
            for i in range(self.tab_group.count()):
                _item = self.tab_group.item(i)
                if item.wxid1 == _item.wxid:
                    self.tab_group.setCurrentRow(i)
                    break
        elif item.wxid1.startswith("gh_"):
            self.TW_contact.setCurrentIndex(2)
            for i in range(self.tab_office.count()):
                _item = self.tab_office.item(i)
                if item.wxid1 == _item.wxid:
                    self.tab_office.setCurrentRow(i)
                    break
        else:
            self.TW_contact.setCurrentIndex(0)
            for i in range(self.tab_friend.count()):
                _item = self.tab_friend.item(i)
                if item.wxid1 == _item.wxid:
                    self.tab_friend.setCurrentRow(i)
                    break
        for cb in cb_contact_list:
            if cb.wxid == item.wxid1:
                cb.setCheckState(Qt.Checked)
                break
        self.TE_send.setFocus()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    spy = SpyUI()
    sys.exit(app.exec_())
