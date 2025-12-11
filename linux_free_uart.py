#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
linux_free_uart - Linux 串口调试工具（支持命令分组 & 拖拽排序 & DSL脚本引擎 + SEND可选等待返回）
- 非独占串口，退出后可被其他程序正常写
- 自定义波特率 / 刷新串口
- 命令分组：支持颜色标识、折叠、跨组拖拽
- 右侧命令按钮（轻微增大行间距，更美观），持久化到 JSON v2
- 支持：右侧命令用鼠标拖动上下移动，并自动保存到 commands.json
- 脚本 DSL：SEND / DELAY / WAIT / LOOP / SET / 变量展开
- 新增：SEND 可选 EXPECT/TIMEOUT，串口返回匹配后再继续，否则超时报错
- 授权：MIT License（开源）；作者 moonlitcodex
"""

import json, sys, time, re, uuid
from pathlib import Path
import serial, serial.tools.list_ports

from PyQt5.QtCore import QTimer, Qt, QMimeData, QEvent, QThread, pyqtSignal
from PyQt5.QtGui import (
    QDrag, QColor, QIcon, QPixmap, QPainter, QLinearGradient, QFont, QPen
)
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QTextEdit, QLineEdit,
    QVBoxLayout, QHBoxLayout, QComboBox, QScrollArea, QMessageBox,
    QInputDialog, QFileDialog, QSizePolicy, QColorDialog, QDialog,
    QFormLayout, QDialogButtonBox, QFrame
)

# ---------- 基础信息 ----------
APP_NAME = "linux_free_uart"
APP_VERSION = "1.0.0"
APP_AUTHOR = "moonlitcodex"
APP_LICENSE = "MIT License"
APP_EMAIL = "moonlitcodex@qq.com"

# ---------- 语言与翻译 ----------
LANGUAGES = {
    "en": "English",
    "zh": "简体中文",
}

TRANSLATIONS = {
    "title_main": {
        "en": f"{APP_NAME} - Serial Assistant",
        "zh": f"{APP_NAME} - 串口调试助手",
    },
    "label_port": {"en": "Port:", "zh": "串口:"},
    "btn_refresh": {"en": "Refresh", "zh": "刷新"},
    "label_baud": {"en": "Baud:", "zh": "波特率:"},
    "btn_open": {"en": "Open", "zh": "打开串口"},
    "btn_close": {"en": "Close", "zh": "关闭串口"},
    "btn_send": {"en": "Send", "zh": "发送"},
    "btn_save_button": {"en": "Save as Button", "zh": "保存为按钮"},
    "label_command_buttons": {"en": "Command Buttons", "zh": "命令按钮"},
    "btn_clear_log": {"en": "Clear Log", "zh": "清空日志"},
    "btn_export_log": {"en": "Export Log", "zh": "导出日志"},
    "btn_run_script": {"en": "Run Script", "zh": "运行脚本"},
    "btn_stop_script": {"en": "Stop Script", "zh": "停止脚本"},
    "btn_about": {"en": "About", "zh": "关于"},
    "btn_new_group": {"en": "+ New Group", "zh": "+ 新建分组"},
    "placeholder_empty_group": {"en": "Drag commands here", "zh": "拖拽命令到此处"},
    "placeholder_no_device": {"en": "<No Device>", "zh": "<无设备>"},
    "msg_no_port_title": {"en": "Notice", "zh": "提示"},
    "msg_no_port": {"en": "No serial device detected.", "zh": "未检测到串口设备！"},
    "msg_opened": {"en": "[Opened: {port} @ {baud}]", "zh": "[串口已打开: {port} @ {baud}]"},
    "msg_closed": {"en": "[Serial closed]", "zh": "[串口已关闭]"},
    "msg_open_first": {"en": "[Please open serial port first]", "zh": "[请先打开串口]"},
    "msg_send_error": {"en": "[Send error] {err}", "zh": "[发送错误] {err}"},
    "msg_recv_error": {"en": "[Receive error] {err}", "zh": "[接收错误] {err}"},
    "msg_run_script_title": {"en": "Notice", "zh": "提示"},
    "msg_run_script_need_open": {"en": "Please open the serial port before running script.", "zh": "请先打开串口，再运行脚本。"},
    "msg_script_running": {"en": "Script is running. Stop it or wait to finish.", "zh": "脚本正在运行中。请先停止或等待完成。"},
    "msg_script_load_error_title": {"en": "Script Error", "zh": "脚本错误"},
    "msg_script_loaded": {"en": "[Script] Loaded {steps} steps; start executing.", "zh": "[脚本] 加载成功，共 {steps} 步；开始执行。"},
    "msg_script_stopping": {"en": "[Script] Stopping…", "zh": "[脚本] 停止中…"},
    "msg_script_result": {"en": "[Script] {msg}", "zh": "[脚本] {msg}"},
    "msg_export_no_log": {"en": "No log to export.", "zh": "没有日志可导出！"},
    "msg_export_title": {"en": "Export Log", "zh": "导出日志"},
    "msg_export_success": {"en": "Log saved to: {path}", "zh": "日志已保存到: {path}"},
    "msg_export_fail": {"en": "Save failed: {err}", "zh": "保存失败: {err}"},
    "msg_save_success_title": {"en": "Success", "zh": "成功"},
    "msg_question_title": {"en": "Question", "zh": "提示"},
    "msg_replace_or_copy": {
        "en": "Replace this button?\nOld: {old}\nNew: {new}\nYes = replace; No = duplicate.",
        "zh": "要把\n『{old}』\n替换为\n『{new}』吗？\n选\"否\"将保留旧命令并新增新按钮。"
    },
    "msg_cmd_exists": {"en": "Command already exists!", "zh": "命令已存在！"},
    "msg_cmd_exists_warn_title": {"en": "Warning", "zh": "提示"},
    "msg_group_delete_warn": {"en": "At least one group must remain.", "zh": "至少需要保留一个分组！"},
    "msg_group_delete_confirm": {
        "en": "Delete group \"{name}\"? Commands will move to the first group.",
        "zh": "确定要删除分组\"{name}\"吗？\n分组内的命令将移至第一个分组。"
    },
    "about_title": {"en": "About", "zh": "关于"},
    "about_body": {
        "en": (
            "{name}\n"
            "Linux serial assistant\n"
            "Version: {version}\n"
            "Author: {author}\n"
            "Email: {email}\n"
            "Copyright: (c) 2024 {author}\n"
            "License: {license} (open source)\n"
            "MIT License: free to use, modify, and distribute with attribution."
        ),
        "zh": (
            "{name}\n"
            "Linux 串口调试助手\n"
            "版本: {version}\n"
            "作者: {author}\n"
            "邮箱: {email}\n"
            "版权: (c) 2024 {author}\n"
            "许可证: {license}（开源）\n"
            "遵循 MIT License 发布，可自由使用、修改和分发，保留作者署名。"
        ),
    },
    "label_lang": {"en": "Language", "zh": "语言"},
    "dlg_edit_group_title": {"en": "Edit Group", "zh": "编辑分组"},
    "dlg_group_name": {"en": "Group Name:", "zh": "分组名称:"},
    "dlg_choose_color": {"en": "Select color:", "zh": "选择颜色:"},
    "dlg_custom_color": {"en": "Custom Color...", "zh": "自定义颜色..."},
    "dlg_delete_group": {"en": "Delete Group", "zh": "删除分组"},
    "dlg_current_color": {"en": "Current color: {color}", "zh": "当前颜色: {color}"},
    "dlg_new_group_title": {"en": "New Group", "zh": "新建分组"},
    "dlg_new_group_prompt": {"en": "Please enter group name:", "zh": "请输入分组名称:"},
    "dlg_edit_cmd_title": {"en": "Edit/Copy/Delete Command", "zh": "编辑/复制/删除命令"},
    "dlg_edit_cmd_text": {
        "en": "Edit then press OK.\nEmpty -> delete;\nYes -> replace; No -> duplicate.",
        "zh": "修改内容后点\"确定\"\n留空 → 删除；\n修改后选择\"是\" → 替换；\n修改后选择\"否\" → 复制为新："
    },
    "dlg_open_script_title": {"en": "Select Script File", "zh": "选择脚本文件"},
    "dlg_choose_group_title": {"en": "Choose Group", "zh": "选择分组"},
    "dlg_choose_group_prompt": {"en": "Add command to which group?", "zh": "请选择要添加到的分组:"},
    "msg_open_fail_title": {"en": "Open Failed", "zh": "打开失败"},
    "msg_export_no_path": {"en": "No path selected.", "zh": "未选择路径。"},
    "msg_script_need_open_title": {"en": "Info", "zh": "提示"},
    "msg_script_prefix": {"en": "[Script]", "zh": "[脚本]"},
    "msg_script_wait_timeout": {
        "en": "EXPECT timed out: EXPECT={expect}, TIMEOUT={timeout}ms",
        "zh": "等待期望返回超时：EXPECT={expect}，TIMEOUT={timeout}ms"
    },
    "msg_script_stop": {"en": "Script stopped", "zh": "脚本已停止"},
    "msg_script_done": {"en": "Script completed", "zh": "脚本执行完成"},
    "msg_script_exception": {"en": "Script exception: {err}", "zh": "脚本执行异常：{err}"},
    "msg_bad_regex": {"en": "EXPECT regex invalid: {err}, fallback to substring match", "zh": "EXPECT 正则无效：{err}，按普通文本处理"},
    "msg_script_read_fail": {"en": "Serial read failed: {err}", "zh": "读取串口失败：{err}"},
    "msg_script_unknown_step": {"en": "Unknown step: {op}", "zh": "未知步骤：{op}"},
    "msg_no_log_title": {"en": "Notice", "zh": "提示"},
}


def translate(key, lang, **kwargs):
    """Return translated text; fallback to English and key itself."""
    text = TRANSLATIONS.get(key, {}).get(lang) or TRANSLATIONS.get(key, {}).get("en") or key
    return text.format(**kwargs)


def build_app_icon(save_path: Path = None) -> QIcon:
    """Create an in-memory app icon; optionally save to PNG."""
    size = 256
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)

    # Base: simple light-to-dark grayscale gradient
    bg = QLinearGradient(0, 0, size, size)
    bg.setColorAt(0.0, QColor("#FFFFFF"))
    bg.setColorAt(1.0, QColor("#DADADA"))
    painter.setBrush(bg)
    painter.setPen(QPen(QColor("#000000"), 6))
    painter.drawRoundedRect(10, 10, size - 20, size - 20, 36, 36)

    # Signal lines in black
    pen = QPen(QColor("#000000"))
    pen.setWidth(12)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    path_points = [
        (40, 160), (90, 120), (140, 190), (190, 110), (230, 150)
    ]
    for i in range(len(path_points) - 1):
        a, b = path_points[i], path_points[i+1]
        painter.drawLine(a[0], a[1], b[0], b[1])

    # Accent circles (monochrome)
    painter.setBrush(QColor("#000000"))
    painter.setPen(Qt.NoPen)
    for x, y in path_points[1:-1]:
        painter.drawEllipse(x - 8, y - 8, 16, 16)

    # Text
    painter.setPen(QColor("#000000"))
    font = QFont("Sans Serif", 56, QFont.Black)
    painter.setFont(font)
    painter.drawText(pix.rect(), Qt.AlignCenter, "UART")
    painter.end()

    if save_path:
        try:
            pix.save(str(save_path), "PNG")
        except Exception:
            pass

    return QIcon(pix)

# ---------- 配置 ----------
CONFIG_FILE = Path(__file__).with_name("commands.json")
DEFAULT_CMDS = ["AT", "AT+GMR", "AT+RST", "AT+HELP"]

# 预设颜色（Material Design 柔和色系）
PRESET_COLORS = [
    ("#E3F2FD", "浅蓝"),
    ("#FFF9C4", "浅黄"),
    ("#C8E6C9", "浅绿"),
    ("#F8BBD0", "浅粉"),
    ("#D1C4E9", "浅紫"),
    ("#FFCCBC", "浅橙"),
    ("#B2DFDB", "浅青"),
    ("#F5F5F5", "浅灰"),
]


def migrate_v1_to_v2(data):
    """将 v1 格式（数组或 {commands: []}）迁移到 v2 格式"""
    if isinstance(data, list):
        return {
            "version": 2,
            "groups": [{
                "id": "default",
                "name": "默认分组",
                "color": "#F5F5F5",
                "collapsed": False,
                "commands": data
            }]
        }
    elif isinstance(data, dict) and "commands" in data and "groups" not in data:
        return {
            "version": 2,
            "groups": [{
                "id": "default",
                "name": "默认分组",
                "color": "#F5F5F5",
                "collapsed": False,
                "commands": data["commands"]
            }]
        }
    return data


def load_groups():
    """加载分组配置，自动处理格式迁移"""
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            
            if not isinstance(data, dict) or "version" not in data or data.get("version") != 2:
                print("[INFO] 检测到旧格式，自动迁移到 v2...")
                data = migrate_v1_to_v2(data)
                
                backup = CONFIG_FILE.with_suffix(".json.v1.backup")
                if not backup.exists():
                    import shutil
                    shutil.copy2(CONFIG_FILE, backup)
                    print(f"[INFO] 旧配置已备份到: {backup}")
                
                save_groups(data["groups"])
            
            return data.get("groups", [])
        except Exception as e:
            print(f"[WARN] load_groups 失败: {e}")
    
    return [{
        "id": "default",
        "name": "默认分组",
        "color": "#F5F5F5",
        "collapsed": False,
        "commands": DEFAULT_CMDS.copy()
    }]


def save_groups(groups):
    """保存分组配置（v2 格式）"""
    try:
        data = {
            "version": 2,
            "groups": groups
        }
        CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        print("[WARN] save_groups:", exc)


# ---------- 可拖拽命令行 ----------
class CmdRow(QWidget):
    """
    一行命令（发送按钮 + ✎编辑按钮），支持拖动启动 QDrag。
    保持原外观，只做“轻微”间距优化。
    """
    MIME = "application/x-serialtool-cmd-v2"

    def __init__(self, parent, cmd, group_id, on_send, on_edit):
        super().__init__(parent)
        self.cmd = cmd
        self.group_id = group_id
        self._press_pos = None

        line = QHBoxLayout(self)
        line.setContentsMargins(4, 3, 4, 3)
        line.setSpacing(6)

        self.send_btn = QPushButton(cmd, self)
        self.send_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.send_btn.setMinimumHeight(30)
        self.send_btn.clicked.connect(lambda: on_send(cmd))

        self.edit_btn = QPushButton("✎", self)
        self.edit_btn.setFixedWidth(30)
        self.edit_btn.clicked.connect(lambda: on_edit(cmd, group_id))

        line.addWidget(self.send_btn)
        line.addWidget(self.edit_btn)

        self.installEventFilter(self)
        self.send_btn.installEventFilter(self)
        self.edit_btn.installEventFilter(self)

    def eventFilter(self, obj, e):
        if e.type() == QEvent.MouseButtonPress and e.button() == Qt.LeftButton:
            self._press_pos = e.globalPos()
            return False

        if e.type() == QEvent.MouseMove and (e.buttons() & Qt.LeftButton):
            if self._press_pos is None:
                return False
            if (e.globalPos() - self._press_pos).manhattanLength() >= QApplication.startDragDistance():
                self._start_drag()
                return True
        return False

    def _start_drag(self):
        drag = QDrag(self)
        mime = QMimeData()
        # v2: 携带命令和源分组 ID
        payload = json.dumps({"command": self.cmd, "source_group": self.group_id})
        mime.setData(self.MIME, payload.encode("utf-8"))
        drag.setMimeData(mime)
        drag.exec_(Qt.MoveAction)


# ---------- 分组容器 ----------
class GroupBox(QFrame):
    """
    单个分组容器，包含：
    - 头部（标题、折叠按钮、设置按钮）
    - 命令列表区域
    """
    sig_group_changed = pyqtSignal()  # 分组属性变更

    def __init__(self, group_id, name, color, collapsed, tool):
        super().__init__()
        self.group_id = group_id
        self.name = name
        self.color = color
        self.collapsed = collapsed
        self.tool = tool
        
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.StyledPanel)
        
        self._apply_style()
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 头部
        header = QWidget()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(4)
        
        self.collapse_btn = QPushButton("▼" if not collapsed else "▶")
        self.collapse_btn.setFixedSize(20, 20)
        self.collapse_btn.clicked.connect(self._toggle_collapse)
        
        self.title_label = QLabel(name)
        self.title_label.setStyleSheet("font-weight: bold;")
        
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(20, 20)
        self.settings_btn.clicked.connect(self._edit_group)
        
        header_layout.addWidget(self.collapse_btn)
        header_layout.addWidget(self.title_label, 1)
        header_layout.addWidget(self.settings_btn)
        
        main_layout.addWidget(header)
        
        # 命令列表容器
        self.cmd_area = QWidget()
        self.cmd_layout = QVBoxLayout(self.cmd_area)
        self.cmd_layout.setContentsMargins(4, 4, 4, 4)
        self.cmd_layout.setSpacing(4)
        
        main_layout.addWidget(self.cmd_area)
        
        self.cmd_area.setVisible(not collapsed)
    
    def _apply_style(self):
        """应用分组颜色样式"""
        qcolor = QColor(self.color)
        lighter = qcolor.lighter(180).name()
        
        self.setStyleSheet(f"""
            GroupBox {{
                border: 2px solid {self.color};
                border-radius: 6px;
                background-color: {lighter};
                margin: 2px;
            }}
            QWidget#header {{
                background-color: {self.color};
                border-radius: 4px 4px 0 0;
            }}
        """)
    
    def _toggle_collapse(self):
        """折叠/展开分组"""
        self.collapsed = not self.collapsed
        self.cmd_area.setVisible(not self.collapsed)
        self.collapse_btn.setText("▼" if not self.collapsed else "▶")
        self.sig_group_changed.emit()
    
    def _edit_group(self):
        """编辑分组设置"""
        dialog = GroupEditDialog(self.name, self.color, self.tool._tr, self)
        if dialog.exec_() == QDialog.Accepted:
            new_name, new_color = dialog.get_values()
            if new_color == "__DELETE__":
                # 删除分组
                self.tool.delete_group(self.group_id)
            elif new_name != self.name or new_color != self.color:
                self.name = new_name
                self.color = new_color
                self.title_label.setText(new_name)
                self._apply_style()
                self.sig_group_changed.emit()
    
    def rebuild_commands(self, commands):
        """重建命令列表"""
        while self.cmd_layout.count():
            item = self.cmd_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        
        if commands:
            for cmd in commands:
                row = CmdRow(self, cmd, self.group_id, self.tool._send_cmd, self.tool._edit_dialog)
                self.cmd_layout.addWidget(row)
        else:
            empty_label = QLabel(self.tool._tr("placeholder_empty_group"))
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("color: #999; font-style: italic; padding: 20px;")
            self.cmd_layout.addWidget(empty_label)
        
        self.cmd_layout.addStretch(1)
    
    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(CmdRow.MIME):
            e.acceptProposedAction()
        else:
            e.ignore()
    
    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(CmdRow.MIME):
            e.acceptProposedAction()
        else:
            e.ignore()
    
    def dropEvent(self, e):
        if not e.mimeData().hasFormat(CmdRow.MIME):
            e.ignore()
            return
        
        try:
            payload = json.loads(bytes(e.mimeData().data(CmdRow.MIME)).decode("utf-8"))
            cmd = payload["command"]
            source_group = payload["source_group"]
        except Exception:
            e.ignore()
            return
        
        pos_y = e.pos().y()
        rows = self._get_cmd_rows()
        
        insert_idx = len(rows)
        for i, r in enumerate(rows):
            g = r.geometry()
            center_y = g.top() + g.height() // 2
            if pos_y < center_y:
                insert_idx = i
                break
        
        self.tool.move_command(cmd, source_group, self.group_id, insert_idx)
        e.acceptProposedAction()
    
    def _get_cmd_rows(self):
        rows = []
        for i in range(self.cmd_layout.count()):
            w = self.cmd_layout.itemAt(i).widget()
            if isinstance(w, CmdRow):
                rows.append(w)
        return rows


# ---------- 分组编辑对话框 ----------
class GroupEditDialog(QDialog):
    """编辑分组名称和颜色"""
    def __init__(self, name, color, tr_fn, parent=None):
        super().__init__(parent)
        self.tr = tr_fn
        self.setWindowTitle(self.tr("dlg_edit_group_title"))
        self.selected_color = color
        
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        self.name_input = QLineEdit(name)
        form.addRow(self.tr("dlg_group_name"), self.name_input)
        layout.addLayout(form)
        
        color_label = QLabel(self.tr("dlg_choose_color"))
        layout.addWidget(color_label)
        
        color_grid = QHBoxLayout()
        for hex_color, label in PRESET_COLORS:
            btn = QPushButton()
            btn.setFixedSize(40, 40)
            btn.setStyleSheet(f"background-color: {hex_color}; border: 2px solid #999;")
            btn.setToolTip(label)
            btn.clicked.connect(lambda checked, c=hex_color: self._select_color(c))
            color_grid.addWidget(btn)
        
        layout.addLayout(color_grid)
        
        custom_btn = QPushButton(self.tr("dlg_custom_color"))
        custom_btn.clicked.connect(self._custom_color)
        layout.addWidget(custom_btn)
        
        self.color_preview = QLabel()
        self.color_preview.setFixedHeight(30)
        self._update_preview()
        layout.addWidget(self.color_preview)
        
        delete_btn = QPushButton(self.tr("dlg_delete_group"))
        delete_btn.setStyleSheet("background-color: #ffcccc;")
        delete_btn.clicked.connect(self._delete_group)
        layout.addWidget(delete_btn)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _select_color(self, color):
        self.selected_color = color
        self._update_preview()
    
    def _custom_color(self):
        color = QColorDialog.getColor(QColor(self.selected_color), self)
        if color.isValid():
            self.selected_color = color.name()
            self._update_preview()
    
    def _update_preview(self):
        self.color_preview.setStyleSheet(f"background-color: {self.selected_color}; border: 1px solid #999;")
        self.color_preview.setText(f"  {self.tr('dlg_current_color', color=self.selected_color)}")
    
    def _delete_group(self):
        self.selected_color = "__DELETE__"
        self.accept()
    
    def get_values(self):
        return self.name_input.text().strip(), self.selected_color



# ---------- 命令容器：支持分组显示 ----------
class CmdContainer(QWidget):
    """
    右侧滚动区域里的实际容器，显示多个 GroupBox
    """
    def __init__(self, tool):
        super().__init__()
        self.tool = tool

        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(6, 6, 6, 6)
        self.vbox.setSpacing(8)
    
    def rebuild(self):
        """根据 self.tool.groups 重建所有分组"""
        while self.vbox.count():
            item = self.vbox.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        
        for group in self.tool.groups:
            group_box = GroupBox(
                group["id"],
                group["name"],
                group["color"],
                group.get("collapsed", False),
                self.tool
            )
            group_box.rebuild_commands(group.get("commands", []))
            group_box.sig_group_changed.connect(self.tool._on_group_changed)
            self.vbox.addWidget(group_box)
        
        # 添加"新建分组"按钮
        add_group_btn = QPushButton(self.tool._tr("btn_new_group"))
        add_group_btn.setStyleSheet("background-color: #e8f5e9; padding: 8px;")
        add_group_btn.clicked.connect(self.tool._create_new_group)
        self.vbox.addWidget(add_group_btn)
        
        self.vbox.addStretch(1)

# ---------- 脚本解析 & 执行 ----------
class ScriptError(Exception):
    pass


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


def parse_script(text: str):
    """
    极简 DSL（大小写不敏感）：
      - SEND <text> [EXPECT <substr|"/regex/"> [TIMEOUT <ms>]]
      - DELAY <ms>
      - WAIT <ms>        # 等价 DELAY
      - LOOP <N> { ... }
      - SET NAME = VALUE   或   NAME=VALUE
      - 变量引用：$NAME / ${NAME}（仅在 SEND 中展开）
      - # 注释；空行忽略
    返回树：list[
      ('SET', name, value) |
      ('SEND', text, expect:str|None, timeout_ms:int|None) |
      ('DELAY', ms) |
      ('LOOP', n, block)
    ]
    """
    lines = text.splitlines()

    def _is_assign_line(raw: str):
        l = raw.lstrip()
        if l.upper().startswith("SET "):
            body = l[4:]
            if "=" in body:
                name, value = body.split("=", 1)
                return True, name.strip(), value.lstrip()
            return False, None, None
        up = l.upper()
        if up.startswith(("SEND ", "DELAY ", "WAIT ", "LOOP ")):
            return False, None, None
        if "=" in l:
            name, value = l.split("=", 1)
            if name and name.strip() == name and " " not in name:
                return True, name, value.lstrip()
        return False, None, None

    def _parse_send_remainder(rem: str):
        """
        解析 SEND 余下部分，抽取 EXPECT/TIMEOUT。
        规则：寻找关键字 EXPECT/TIMEOUT（大小写不敏感）；EXPECT 的模式可用引号或 /regex/。
        """
        # 为了简单稳健，按空格拆分扫描关键字，但允许 EXPECT 值包含空格（使用引号或 /.../）
        up = rem.upper()
        expect = None
        timeout = None

        # 找 EXPECT 位置
        pos_exp = up.find(" EXPECT ")
        pos_to = up.find(" TIMEOUT ")

        # 计算各段
        end_cmd = len(rem)
        if pos_exp != -1:
            end_cmd = pos_exp
        if pos_to != -1:
            end_cmd = min(end_cmd, pos_to)
        cmd_text = rem[:end_cmd].strip()

        tail = rem[end_cmd:]
        # 解析 tail 中的 EXPECT/TIMEOUT（顺序任意）
        i = 0
        while i < len(tail):
            if tail[i:].upper().startswith(" EXPECT "):
                i += len(" EXPECT ")
                # 读取一个 token（引号字符串、/regex/、或到下一个关键字前的裸字符串）
                j = i
                if j < len(tail) and tail[j] in ("'", '"'):
                    q = tail[j]; j += 1
                    while j < len(tail) and tail[j] != q:
                        j += 1
                    token = tail[i:j+1] if j < len(tail) else tail[i:]
                    i = j + 1
                    expect = _strip_quotes(token)
                elif j < len(tail) and tail[j] == "/":
                    j += 1
                    while j < len(tail) and tail[j] != "/":
                        j += 1
                    token = tail[i:j+1] if j < len(tail) else tail[i:]
                    i = j + 1
                    expect = token.strip()  # 保留 /.../ 以示正则
                else:
                    # 读到下一个关键字或末尾
                    k = tail[i:].upper().find(" TIMEOUT ")
                    token = tail[i:] if k == -1 else tail[i:i+k]
                    expect = token.strip()
                    i = len(tail) if k == -1 else i + k
            elif tail[i:].upper().startswith(" TIMEOUT "):
                i += len(" TIMEOUT ")
                # 读到下一个空白或结尾
                j = i
                while j < len(tail) and tail[j].isdigit():
                    j += 1
                token = tail[i:j].strip()
                if not token.isdigit():
                    raise ScriptError("TIMEOUT 需要毫秒整数")
                timeout = int(token)
                i = j
            else:
                i += 1

        return cmd_text, expect, timeout

    def parse_block(idx):
        cmds = []
        while idx < len(lines):
            raw = lines[idx]
            s = raw.strip()
            idx += 1

            if not s or s.startswith("#"):
                continue
            if s == "}":
                return cmds, idx

            is_assign, var_name, var_value = _is_assign_line(raw)
            if is_assign:
                if " #" in var_value:
                    var_value = var_value.split(" #", 1)[0]
                cmds.append(("SET", var_name, var_value.rstrip("\n")))
                continue

            up = s.upper()

            if up.startswith("SEND "):
                rem = s[5:].strip()
                cmd_text, expect, timeout = _parse_send_remainder(rem)
                cmds.append(("SEND", cmd_text, expect, timeout))
                continue

            if up.startswith("DELAY "):
                val = s[6:].strip()
                if not val.isdigit():
                    raise ScriptError(f"DELAY 需要毫秒整数（第 {idx} 行）")
                cmds.append(("DELAY", int(val)))
                continue

            if up.startswith("WAIT "):
                val = s[5:].strip()
                if not val.isdigit():
                    raise ScriptError(f"WAIT 需要毫秒整数（第 {idx} 行）")
                cmds.append(("DELAY", int(val)))
                continue

            if up.startswith("LOOP "):
                rest = s[5:].strip()
                parts = rest.split(None, 1)
                if not parts or not parts[0].isdigit():
                    raise ScriptError(f"LOOP 后需要次数整数（第 {idx} 行）")
                count = int(parts[0])
                after = parts[1].strip() if len(parts) > 1 else ""
                if after == "{":
                    block, idx = parse_block(idx)
                else:
                    while idx < len(lines) and (lines[idx].strip() == "" or lines[idx].strip().startswith("#")):
                        idx += 1
                    if idx >= len(lines) or lines[idx].strip() != "{":
                        raise ScriptError(f"LOOP 缺少 '{{'（第 {idx} 行附近）")
                    idx += 1
                    block, idx = parse_block(idx)
                cmds.append(("LOOP", count, block))
                continue

            raise ScriptError(f"无法识别的指令：{s}（第 {idx} 行）")
        return cmds, idx

    cmds, _ = parse_block(0)
    return cmds


def flatten_cmds(cmds, limit=200000):
    """
    展开树为线性序列：
      - ('SET', name, value)
      - ('SEND', text, expect, timeout_ms)
      - ('DELAY', ms)
    """
    out = []

    def rec(lst):
        nonlocal out
        for c in lst:
            op = c[0]
            if op == "SEND":
                out.append(("SEND", c[1], c[2], c[3]))
            elif op == "DELAY":
                out.append(("DELAY", c[1]))
            elif op == "SET":
                out.append(("SET", c[1], c[2]))
            elif op == "LOOP":
                times, block = c[1], c[2]
                if times < 0:
                    raise ScriptError("LOOP 次数不能为负数")
                for _ in range(times):
                    rec(block)
            else:
                raise ScriptError(f"未知指令类型：{op}")
            if len(out) > limit:
                raise ScriptError(f"展开后的指令超过限制（>{limit}），请减少循环次数。")

    rec(cmds)
    return out


class ScriptRunner(QThread):
    sig_log = pyqtSignal(str)
    sig_send = pyqtSignal(str)   # 主线程串口发送
    sig_done = pyqtSignal(bool, str)

    def __init__(self, steps, serial_obj: serial.Serial, tr_fn):
        super().__init__()
        self._steps = steps
        self._stop = False
        self._vars = {}
        self._ser = serial_obj  # 直接读取串口，用于 EXPECT 等待
        self._tr = tr_fn

    def stop(self):
        self._stop = True

    def _expand_vars(self, text: str) -> str:
        """展开 $NAME / ${NAME}，支持 \$ 转义"""
        out = []
        i = 0
        n = len(text)
        while i < n:
            ch = text[i]
            if ch == "\\" and i + 1 < n and text[i+1] == "$":
                out.append("$"); i += 2; continue
            if ch == "$":
                # ${NAME}
                if i + 1 < n and text[i+1] == "{":
                    j = i + 2
                    while j < n and text[j] != "}":
                        j += 1
                    if j < n:
                        name = text[i+2:j]
                        out.append(self._vars.get(name, ""))
                        i = j + 1
                        continue
                # $NAME
                j = i + 1
                while j < n and (text[j].isalnum() or text[j] == "_"):
                    j += 1
                name = text[i+1:j]
                if name:
                    out.append(self._vars.get(name, ""))
                    i = j
                    continue
            out.append(ch); i += 1
        return "".join(out)

    def _wait_for_expect(self, expect: str, timeout_ms: int) -> bool:
        """
        在当前线程直接从串口读取，直到匹配 expect 或超时。
        - 如果 expect 形如 /.../ 则按正则匹配；否则做子串查找
        - 不改变 DTR/RTS，不写，只读 in_waiting
        """
        buf = ""
        deadline = time.time() + timeout_ms / 1000.0
        is_regex = False
        pattern = None

        if expect and len(expect) >= 2 and expect[0] == "/" and expect[-1] == "/":
            try:
                pattern = re.compile(expect[1:-1])
                is_regex = True
            except re.error as e:
                self.sig_log.emit(f"{self._tr('msg_script_prefix')} {self._tr('msg_bad_regex', err=e)}")
                is_regex = False

        while not self._stop:
            # 超时？
            now = time.time()
            if now >= deadline:
                return False

            try:
                waiting = getattr(self._ser, "in_waiting", 0)
                if waiting and waiting > 0:
                    data = self._ser.read(waiting)
                    try:
                        text = data.decode("utf-8", errors="ignore")
                    except Exception:
                        text = data.decode(errors="ignore")
                    if text:
                        buf += text
                        # 同时把新读到的内容抛到日志，方便观察（不影响 GUI 定时器被暂停的情况）
                        self.sig_log.emit(text)
                        if is_regex:
                            if pattern.search(buf):
                                return True
                        else:
                            if expect in buf:
                                return True
            except Exception as e:
                self.sig_log.emit(f"{self._tr('msg_script_prefix')} {self._tr('msg_script_read_fail', err=e)}")
                # 继续循环，直到超时
            time.sleep(0.01)
        return False

    def run(self):
        try:
            for step in self._steps:
                if self._stop:
                    self.sig_done.emit(False, self._tr("msg_script_stop"))
                    return

                op = step[0]
                if op == "SET":
                    name, value = step[1], step[2]
                    self._vars[name] = value
                    self.sig_log.emit(f"{self._tr('msg_script_prefix')} SET {name} = ({len(value)} bytes)")
                    continue

                if op == "SEND":
                    raw = step[1]
                    expect = step[2]  # 可能为 None
                    timeout_ms = step[3] if step[3] is not None else 3000  # 默认 3s

                    expanded = self._expand_vars(raw)
                    log_line = f"{self._tr('msg_script_prefix')} SEND {raw}"
                    if expanded != raw:
                        log_line += f"  ->  {expanded}"
                    if expect:
                        log_line += f"  ; EXPECT={expect}  ; TIMEOUT={timeout_ms}ms"
                    self.sig_log.emit(log_line)

                    # 由主线程写串口（追加 CRLF）
                    self.sig_send.emit(expanded)

                    # 需要等待返回？
                    if expect:
                        ok = self._wait_for_expect(expect, timeout_ms)
                        if not ok:
                            self.sig_done.emit(False, self._tr("msg_script_wait_timeout", expect=expect, timeout=timeout_ms))
                            return
                    continue

                if op == "DELAY":
                    ms = max(0, int(step[1]))
                    self.sig_log.emit(f"{self._tr('msg_script_prefix')} DELAY {ms} ms")
                    end_t = time.time() + ms / 1000.0
                    while not self._stop and time.time() < end_t:
                        time.sleep(0.02)
                    continue

                self.sig_log.emit(f"{self._tr('msg_script_prefix')} {self._tr('msg_script_unknown_step', op=op)}")

            self.sig_done.emit(True, self._tr("msg_script_done"))
        except Exception as e:
            self.sig_done.emit(False, self._tr("msg_script_exception", err=e))


# ---------- 主窗口 ----------
class SerialTool(QWidget):
    def __init__(self):
        super().__init__()
        self.lang = "en"  # 默认英文
        self.setWindowTitle(self._tr("title_main"))
        self.resize(900, 580)

        # 尽量使用非独占
        self.serial = serial.Serial(exclusive=False)
        self.timer = QTimer(self); self.timer.timeout.connect(self._read_data)

        self.groups = load_groups()
        self.script_runner = None  # ScriptRunner 线程
        self._build_ui()

    def _tr(self, key, **kwargs):
        return translate(key, self.lang, **kwargs)

    # ===== UI =====
    def _build_ui(self):
        root = QHBoxLayout(self)

        # -------- 左侧 --------
        left = QVBoxLayout(); root.addLayout(left, 4)

        # 串口行
        port_line = QHBoxLayout()
        self.port_label = QLabel()
        self.port_cb = QComboBox(); self._refresh_ports()
        self.refresh_btn = QPushButton(); self.refresh_btn.clicked.connect(self._refresh_ports)
        self.baud_label = QLabel()
        self.baud_cb = QComboBox(); self.baud_cb.setEditable(True)
        self.baud_cb.addItems(["9600", "19200", "38400", "57600", "115200", "921600", "1000000"])
        self.baud_cb.setCurrentText("115200")
        self.open_btn = QPushButton(); self.open_btn.clicked.connect(self._toggle_serial)
        for w in (self.port_label, self.port_cb, self.refresh_btn,
                  self.baud_label, self.baud_cb, self.open_btn):
            port_line.addWidget(w)
        left.addLayout(port_line)

        # 发送行
        send_line = QHBoxLayout()
        self.send_le = QLineEdit()
        self.send_btn = QPushButton(); self.send_btn.clicked.connect(lambda: self._send_cmd(self.send_le.text().strip()))
        self.add_btn = QPushButton(); self.add_btn.clicked.connect(self._add_from_input)
        for w in (self.send_le, self.send_btn, self.add_btn): send_line.addWidget(w)
        left.addLayout(send_line)

        # 日志
        self.log = QTextEdit(readOnly=True); left.addWidget(self.log, 1)

        # 工具行
        tools = QHBoxLayout()
        self.clear_btn = QPushButton(); self.clear_btn.clicked.connect(self.log.clear)
        self.export_btn = QPushButton(); self.export_btn.clicked.connect(self._export_log)
        self.btn_run_script = QPushButton(); self.btn_run_script.clicked.connect(self._run_script_dialog)
        self.btn_stop_script = QPushButton(); self.btn_stop_script.clicked.connect(self._stop_script)
        self.btn_stop_script.setEnabled(False)
        self.about_btn = QPushButton(); self.about_btn.clicked.connect(self._show_about)
        self.lang_label = QLabel()
        self.lang_cb = QComboBox()
        for code, name in LANGUAGES.items():
            self.lang_cb.addItem(name, code)
        self.lang_cb.setCurrentIndex(0)  # 默认英文
        self.lang_cb.currentIndexChanged.connect(self._on_lang_changed)
        tools.addWidget(self.clear_btn)
        tools.addWidget(self.export_btn)
        tools.addWidget(self.btn_run_script)
        tools.addWidget(self.btn_stop_script)
        tools.addWidget(self.about_btn)
        tools.addWidget(self.lang_label)
        tools.addWidget(self.lang_cb)
        tools.addStretch(1)
        left.addLayout(tools)

        # -------- 右侧：命令按钮（保持原布局：标签 + ScrollArea）--------
        right = QVBoxLayout(); root.addLayout(right, 2)
        self.right_title_label = QLabel()
        right.addWidget(self.right_title_label)

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setMinimumWidth(220)
        self.cmd_container = CmdContainer(self)
        scroll.setWidget(self.cmd_container)
        right.addWidget(scroll)

        self._rebuild_cmd_buttons()
        self._apply_language()

    def _apply_language(self):
        """应用当前语言到界面"""
        self.setWindowTitle(self._tr("title_main"))
        self.port_label.setText(self._tr("label_port"))
        self.refresh_btn.setText(self._tr("btn_refresh"))
        self.baud_label.setText(self._tr("label_baud"))
        self._update_open_btn_text()
        self.send_btn.setText(self._tr("btn_send"))
        self.add_btn.setText(self._tr("btn_save_button"))
        self.clear_btn.setText(self._tr("btn_clear_log"))
        self.export_btn.setText(self._tr("btn_export_log"))
        self.btn_run_script.setText(self._tr("btn_run_script"))
        self.btn_stop_script.setText(self._tr("btn_stop_script"))
        self.about_btn.setText(self._tr("btn_about"))
        self.right_title_label.setText(self._tr("label_command_buttons"))
        self.lang_label.setText(self._tr("label_lang"))
        self._rebuild_cmd_buttons()

    def _update_open_btn_text(self):
        self.open_btn.setText(self._tr("btn_close") if self.serial.is_open else self._tr("btn_open"))

    def _on_lang_changed(self, _index):
        code = self.lang_cb.currentData()
        if code and code != self.lang:
            self.lang = code
            self._apply_language()

    # ===== 关于 =====
    def _show_about(self):
        info = self._tr(
            "about_body",
            name=APP_NAME,
            version=APP_VERSION,
            author=APP_AUTHOR,
            license=APP_LICENSE,
            email=APP_EMAIL,
        )
        QMessageBox.information(self, self._tr("about_title"), info)

    # ===== 串口辅助 =====
    def _refresh_ports(self):
        self.port_cb.clear()
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if not ports:
            ports = [self._tr("placeholder_no_device")]
        self.port_cb.addItems(ports)

    def _release_serial(self):
        if self.serial.is_open:
            self.timer.stop()
            try:
                self.serial.flush(); self.serial.reset_input_buffer(); self.serial.reset_output_buffer()
                self.serial.dtr = False; self.serial.rts = False; self.serial.close()
            except Exception:
                pass
        self.serial = serial.Serial(exclusive=False)
        self._update_open_btn_text()

    def _toggle_serial(self):
        if self.serial.is_open:
            self._release_serial(); self.log.append(self._tr("msg_closed")); return
        port = self.port_cb.currentText()
        if self._tr("placeholder_no_device") == port:
            QMessageBox.warning(self, self._tr("msg_no_port_title"), self._tr("msg_no_port")); return
        try:
            self.serial.port = port; self.serial.baudrate = int(self.baud_cb.currentText()); self.serial.timeout = 0.5
            self.serial.open()
            self._update_open_btn_text()
            self.log.append(self._tr("msg_opened", port=port, baud=self.serial.baudrate))
            self.timer.start(100)
        except Exception as e:
            QMessageBox.critical(self, self._tr("msg_open_fail_title"), str(e)); self._release_serial()

    # ===== 脚本相关 =====
    def _run_script_dialog(self):
        if not self.serial.is_open:
            QMessageBox.information(self, self._tr("msg_run_script_title"), self._tr("msg_run_script_need_open"))
            return
        if self.script_runner and self.script_runner.isRunning():
            QMessageBox.information(self, self._tr("msg_run_script_title"), self._tr("msg_script_running"))
            return

        path, _ = QFileDialog.getOpenFileName(
            self, self._tr("dlg_open_script_title"), str(Path.home()),
            "Script (*.txt *.uartscript);;All Files (*)"
        )
        if not path:
            return

        try:
            text = Path(path).read_text(encoding="utf-8")
            tree = parse_script(text)
            steps = flatten_cmds(tree)
        except Exception as e:
            QMessageBox.critical(self, self._tr("msg_script_load_error_title"), str(e))
            return

        self.log.append(self._tr("msg_script_loaded", steps=len(steps)))
        # 暂停 GUI 定时读取，避免消耗串口数据，交由脚本线程等待
        self.timer.stop()

        self.script_runner = ScriptRunner(steps, self.serial, self._tr)
        self.script_runner.sig_log.connect(self.log.append)
        self.script_runner.sig_send.connect(self._script_send)   # 在主线程发送
        self.script_runner.sig_done.connect(self._script_done)
        self.btn_run_script.setEnabled(False)
        self.btn_stop_script.setEnabled(True)
        self.script_runner.start()

    def _stop_script(self):
        if self.script_runner and self.script_runner.isRunning():
            self.script_runner.stop()
            self.log.append(self._tr("msg_script_stopping"))

    def _script_done(self, ok, msg):
        self.log.append(self._tr("msg_script_result", msg=msg))
        self.btn_run_script.setEnabled(True)
        self.btn_stop_script.setEnabled(False)
        self.script_runner = None
        # 恢复 GUI 定时器读取
        if self.serial.is_open:
            self.timer.start(100)

    def _script_send(self, cmd):
        # 脚本线程发来的发送请求 -> 主线程复用现有发送逻辑（自动 CRLF）
        self._send_cmd(cmd)

    # ===== 命令按钮 =====
    def _rebuild_cmd_buttons(self):
        self.cmd_container.rebuild()

    def _choose_group_id(self):
        """选择要添加到的分组，返回分组 ID 或 None"""
        if not self.groups:
            return None
        if len(self.groups) == 1:
            return self.groups[0]["id"]

        dialog = QDialog(self)
        dialog.setWindowTitle(self._tr("dlg_choose_group_title"))
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(self._tr("dlg_choose_group_prompt")))

        cb = QComboBox(dialog)
        for g in self.groups:
            cb.addItem(g["name"], g["id"])
        layout.addWidget(cb)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() == QDialog.Accepted:
            return cb.currentData()
        return None

    def _add_from_input(self):
        cmd = self.send_le.text().strip()
        if not cmd:
            return
        # 检查命令是否已存在于任何分组
        for group in self.groups:
            if cmd in group.get("commands", []):
                QMessageBox.information(self, self._tr("msg_cmd_exists_warn_title"), self._tr("msg_cmd_exists"))
                return
        target_group_id = self._choose_group_id()
        if not target_group_id:
            return
        # 添加到指定分组
        target_group = None
        for group in self.groups:
            if group["id"] == target_group_id:
                target_group = group
                break
        if target_group:
            target_group["commands"].append(cmd)
        else:
            self.groups.append({
                "id": str(uuid.uuid4())[:8],
                "name": "默认分组",
                "color": "#F5F5F5",
                "collapsed": False,
                "commands": [cmd]
            })
            target_group = self.groups[-1]
        save_groups(self.groups)
        self._rebuild_cmd_buttons()
        self.send_le.clear()

    def _edit_dialog(self, cmd, group_id):
        """编辑/复制/删除命令"""
        new_text, ok = QInputDialog.getText(
            self, self._tr("dlg_edit_cmd_title"),
            self._tr("dlg_edit_cmd_text"),
            text=cmd
        )
        if not ok:
            return
        new_cmd = new_text.strip()

        # 找到命令所在的分组
        group = None
        for g in self.groups:
            if g["id"] == group_id:
                group = g
                break
        
        if not group:
            return

        if new_cmd == "":
            # 删除命令
            if cmd in group["commands"]:
                group["commands"].remove(cmd)
                save_groups(self.groups)
                self._rebuild_cmd_buttons()
            return

        if new_cmd == cmd:
            return

        # 检查新命令是否已存在
        for g in self.groups:
            if new_cmd in g.get("commands", []):
                QMessageBox.warning(self, self._tr("msg_cmd_exists_warn_title"), self._tr("msg_cmd_exists"))
                return

        resp = QMessageBox.question(
            self, self._tr("msg_question_title"), self._tr("msg_replace_or_copy", old=cmd, new=new_cmd),
            QMessageBox.Yes | QMessageBox.No
        )
        if resp == QMessageBox.Yes:
            idx = group["commands"].index(cmd)
            group["commands"][idx] = new_cmd
        else:
            group["commands"].append(new_cmd)
        save_groups(self.groups)
        self._rebuild_cmd_buttons()

    def _send_cmd(self, cmd):
        if not cmd:
            return
        if not self.serial.is_open:
            self.log.append(self._tr("msg_open_first")); return
        try:
            self.serial.write((cmd + "\r\n").encode())
            self.log.append(f">>> {cmd}")
        except Exception as e:
            self.log.append(self._tr("msg_send_error", err=e))

    def _read_data(self):
        try:
            if self.serial.is_open and self.serial.in_waiting:
                data = self.serial.read(self.serial.in_waiting).decode(errors="ignore")
                if data:
                    self.log.append(data)
        except Exception as e:
            self.log.append(self._tr("msg_recv_error", err=e))

    # ===== 日志 =====
    def _export_log(self):
        txt = self.log.toPlainText().strip()
        if not txt:
            QMessageBox.information(self, self._tr("msg_no_log_title"), self._tr("msg_export_no_log")); return
        path, _ = QFileDialog.getSaveFileName(self, self._tr("msg_export_title"), "serial_log.txt", "Text Files (*.txt)")
        if path:
            try:
                Path(path).write_text(txt, encoding="utf-8")
                QMessageBox.information(self, self._tr("msg_save_success_title"), self._tr("msg_export_success", path=path))
            except Exception as e:
                QMessageBox.critical(self, self._tr("msg_export_title"), self._tr("msg_export_fail", err=e))

    # ===== 分组管理 =====
    def move_command(self, cmd, from_group_id, to_group_id, insert_idx):
        """跨分组移动命令"""
        # 从源分组移除
        for group in self.groups:
            if group["id"] == from_group_id:
                if cmd in group["commands"]:
                    group["commands"].remove(cmd)
                break
        
        # 添加到目标分组
        for group in self.groups:
            if group["id"] == to_group_id:
                group["commands"].insert(insert_idx, cmd)
                break
        
        save_groups(self.groups)
        self._rebuild_cmd_buttons()
    
    def _on_group_changed(self):
        """分组属性变更（折叠状态、颜色等）"""
        # 更新groups数据
        for i in range(self.cmd_container.vbox.count()):
            w = self.cmd_container.vbox.itemAt(i).widget()
            if isinstance(w, GroupBox):
                for group in self.groups:
                    if group["id"] == w.group_id:
                        group["name"] = w.name
                        group["color"] = w.color
                        group["collapsed"] = w.collapsed
                        break
        save_groups(self.groups)
    
    def _create_new_group(self):
        """创建新分组"""
        name, ok = QInputDialog.getText(self, self._tr("dlg_new_group_title"), self._tr("dlg_new_group_prompt"))
        if ok and name.strip():
            new_group = {
                "id": str(uuid.uuid4())[:8],
                "name": name.strip(),
                "color": PRESET_COLORS[len(self.groups) % len(PRESET_COLORS)][0],
                "collapsed": False,
                "commands": []
            }
            self.groups.append(new_group)
            save_groups(self.groups)
            self._rebuild_cmd_buttons()
    
    def delete_group(self, group_id):
        """删除分组"""
        if len(self.groups) <= 1:
            QMessageBox.warning(self, self._tr("msg_no_port_title"), self._tr("msg_group_delete_warn"))
            return
        
        # 找到要删除的分组
        group_to_delete = None
        for group in self.groups:
            if group["id"] == group_id:
                group_to_delete = group
                break
        
        if not group_to_delete:
            return
        
        # 确认删除
        resp = QMessageBox.question(
            self, self._tr("msg_question_title"),
            self._tr("msg_group_delete_confirm", name=group_to_delete['name']),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if resp == QMessageBox.Yes:
            # 将命令移至第一个其他分组
            commands = group_to_delete.get("commands", [])
            self.groups.remove(group_to_delete)
            if commands and self.groups:
                self.groups[0]["commands"].extend(commands)
            save_groups(self.groups)
            self._rebuild_cmd_buttons()

    # ===== 关闭 =====
    def closeEvent(self, ev):
        # 停止脚本线程
        if self.script_runner and self.script_runner.isRunning():
            self.script_runner.stop()
            self.script_runner.wait(200)
        save_groups(self.groups)
        self._release_serial()
        super().closeEvent(ev)


# ---------- main ----------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    try:
        app.setDesktopFileName(APP_NAME)
    except Exception:
        pass

    icon_path = Path(__file__).with_name("linux_free_uart.png")
    app_icon = build_app_icon(icon_path)
    app.setWindowIcon(app_icon)

    w = SerialTool()
    w.setWindowIcon(app_icon)
    w.show()
    sys.exit(app.exec_())
