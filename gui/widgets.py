#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QLineEdit, QTextEdit, 
                             QFrame, QStackedWidget, QMessageBox, QScrollArea,
                             QSizePolicy, QStyledItemDelegate, QGraphicsDropShadowEffect)
from PySide6.QtWidgets import QStyle
from PySide6.QtCore import Qt, Signal, QThread, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QTextCursor, QColor
from PySide6.QtWidgets import QGraphicsOpacityEffect
from config.config import (load_api_key, save_api_key, load_model_config, 
                          save_model_config, load_answer_mode, save_answer_mode)
from tools.LLM.deepseek import CURRENT_MODELS, list_models
from tools.LLM.probe import probe_model


class ComboItemDelegate(QStyledItemDelegate):
    """去掉下拉项自带的焦点方框，只保留整行背景。"""

    def paint(self, painter, option, index):
        option.state &= ~QStyle.StateFlag.State_HasFocus
        super().paint(painter, option, index)


class Toast(QWidget):
    """窗口底部的短提示，自动消失。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("toastHost")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.card = QFrame()
        self.card.setObjectName("toast")
        card_layout = QHBoxLayout(self.card)
        card_layout.setContentsMargins(14, 10, 16, 10)
        card_layout.setSpacing(8)
        self.dot = QFrame()
        self.dot.setObjectName("toastDot")
        self.dot.setFixedSize(8, 8)
        self.text = QLabel("")
        self.text.setObjectName("toastText")
        card_layout.addWidget(self.dot, 0, Qt.AlignmentFlag.AlignVCenter)
        card_layout.addWidget(self.text)
        layout.addWidget(self.card)

        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(9, 9, 11, 36))
        self.card.setGraphicsEffect(shadow)

        self.opacity = QGraphicsOpacityEffect(self)
        self.opacity.setOpacity(0)
        self.setGraphicsEffect(self.opacity)
        self.fade = QPropertyAnimation(self.opacity, b"opacity", self)
        self.fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade.finished.connect(self._on_fade_finished)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._fade_out)

    def show_message(self, text):
        self.text.setText(text)
        self.show()
        self.ensurePolished()
        self.text.ensurePolished()
        self.text.setMinimumWidth(self.text.fontMetrics().horizontalAdvance(text) + 2)
        self.adjustSize()
        self.place()
        self.raise_()
        self.hide_timer.stop()
        self.fade.stop()
        self.fade.setDuration(160)
        self.fade.setStartValue(self.opacity.opacity())
        self.fade.setEndValue(1.0)
        self.fade.start()
        self.hide_timer.start(2200)

    def place(self):
        parent = self.parentWidget()
        if parent is None:
            return
        self.adjustSize()
        x = (parent.width() - self.width()) // 2
        y = parent.height() - self.height() - 24
        self.move(max(16, x), max(16, y))

    def _fade_out(self):
        self.fade.stop()
        self.fade.setDuration(180)
        self.fade.setStartValue(self.opacity.opacity())
        self.fade.setEndValue(0.0)
        self.fade.start()

    def _on_fade_finished(self):
        if self.opacity.opacity() <= 0.01:
            self.hide()


def apply_tag(label, object_name):
    """把状态文字收成贴合内容的小标签。"""
    label.setObjectName(object_name)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    label.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    label.style().unpolish(label)
    label.style().polish(label)
    label.adjustSize()
    label.updateGeometry()


class LogWidget(QWidget):
    """日志显示组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("card")
        log_layout = QVBoxLayout(card)
        log_layout.setContentsMargins(16, 16, 16, 16)
        log_layout.setSpacing(12)

        log_toolbar = QHBoxLayout()
        title = QLabel("日志")
        title.setObjectName("cardTitle")
        self.status_indicator = QLabel("就绪")
        apply_tag(self.status_indicator, "badgeMuted")
        clear_btn = QPushButton("清空")
        clear_btn.setObjectName("outlineButton")
        clear_btn.clicked.connect(self.clear_log)
        log_toolbar.addWidget(title)
        log_toolbar.addWidget(self.status_indicator, 0, Qt.AlignmentFlag.AlignVCenter)
        log_toolbar.addStretch()
        log_toolbar.addWidget(clear_btn)
        log_layout.addLayout(log_toolbar)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("log_text")
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(48)
        self.log_text.setPlaceholderText("答题过程会显示在这里")
        log_layout.addWidget(self.log_text)
        main_layout.addWidget(card)
    
    def append_log(self, text):
        """添加日志"""
        # 根据日志内容更新状态指示器
        if "开始" in text:
            self._set_badge("运行中", "badgeOk")
        elif "成功" in text or "完成" in text:
            self._set_badge("完成", "badgeOk")
        elif "失败" in text or "错误" in text:
            self._set_badge("错误", "badgeDanger")
        elif "停止" in text:
            self._set_badge("已停止", "badgeMuted")
        
        # 添加时间戳
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_text = f"[{timestamp}] {text}"
        
        self.log_text.append(formatted_text)
        # 自动滚动到底部
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)
    
    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
        self._set_badge("就绪", "badgeMuted")

    def _set_badge(self, text, object_name):
        self.status_indicator.setText(text)
        apply_tag(self.status_indicator, object_name)

    def set_status(self, status_text):
        """设置状态指示器"""
        self.status_indicator.setText(status_text)


class StatusWidget(QWidget):
    """状态显示组件"""
    
    login_clicked = Signal()
    logout_clicked = Signal()
    switch_account_clicked = Signal()
    start_quiz_clicked = Signal()
    stop_quiz_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_logged_in = False
        self.initUI()
    
    def initUI(self):
        """初始化UI"""
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)

        card = QFrame()
        card.setObjectName("card")
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        status_layout = QVBoxLayout(card)
        status_layout.setContentsMargins(16, 16, 16, 16)
        status_layout.setSpacing(14)
        status_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(12)
        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(6)
        title = QLabel("账号")
        title.setObjectName("cardTitle")
        self.login_status_label = QLabel("未登录")
        apply_tag(self.login_status_label, "badgeMuted")
        self.status_hint_label = QLabel("登录 B 站账号后才能开始答题")
        self.status_hint_label.setObjectName("muted")
        for label in (title, self.status_hint_label):
            label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)
        title_row.addWidget(title)
        title_row.addWidget(self.login_status_label, 0, Qt.AlignmentFlag.AlignVCenter)
        title_row.addStretch()
        title_col.addLayout(title_row)
        title_col.addWidget(self.status_hint_label)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(8)
        self.login_button = QPushButton("登录")
        self.login_button.setObjectName("primaryButton")
        self.login_button.clicked.connect(self._handle_login_button_click)
        self.switch_account_button = QPushButton("切换账号")
        self.switch_account_button.clicked.connect(self.switch_account_clicked.emit)
        for button in (self.login_button, self.switch_account_button):
            self._lock_button(button)
            actions.addWidget(button)

        header.addLayout(title_col, 1)
        header.addLayout(actions, 0)
        status_layout.addLayout(header)

        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFixedHeight(1)
        status_layout.addWidget(separator)

        hint = QLabel("先在「模型」页保存配置，再用下面的按钮开始或停止。")
        hint.setObjectName("muted")
        hint.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        status_layout.addWidget(hint)

        quiz_row = QHBoxLayout()
        quiz_row.setContentsMargins(0, 0, 0, 0)
        quiz_row.setSpacing(8)
        self.start_button = QPushButton("开始答题")
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self.start_quiz_clicked.emit)
        self.stop_button = QPushButton("停止")
        self.stop_button.setObjectName("dangerButton")
        self.stop_button.clicked.connect(self.stop_quiz_clicked.emit)
        for button in (self.start_button, self.stop_button):
            self._lock_button(button)
        self.stop_button.setEnabled(False)
        quiz_row.addWidget(self.start_button, 1)
        quiz_row.addWidget(self.stop_button)
        status_layout.addLayout(quiz_row)
        main_layout.addWidget(card)

    def _lock_button(self, button):
        """按钮保持固定高度，窗口变矮时不被压扁。"""
        button.setMinimumHeight(36)
        button.setMaximumHeight(36)
        button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    
    def _handle_login_button_click(self):
        """处理登录/退出按钮点击"""
        if self.is_logged_in:
            self.logout_clicked.emit()
        else:
            self.login_clicked.emit()
    
    def set_login_status(self, is_logged_in):
        """设置登录状态"""
        self.is_logged_in = is_logged_in
        if is_logged_in:
            self.login_status_label.setText("已登录")
            apply_tag(self.login_status_label, "badgeOk")
            self.status_hint_label.setText("可以开始答题")
            self.login_button.setText("退出")
            self.login_button.setObjectName("outlineButton")
            self.switch_account_button.setEnabled(True)
        else:
            self.login_status_label.setText("未登录")
            apply_tag(self.login_status_label, "badgeMuted")
            self.status_hint_label.setText("登录 B 站账号后才能开始答题")
            self.login_button.setText("登录")
            self.login_button.setObjectName("primaryButton")
            self.switch_account_button.setEnabled(False)
        self.login_button.style().unpolish(self.login_button)
        self.login_button.style().polish(self.login_button)
    
    def set_quiz_running(self, running):
        """答题进行中才能点停止，未开始时停止按钮不可用。"""
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)


class StatsWidget(QWidget):
    """本轮答题统计。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        self.reset()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("本轮统计")
        title.setObjectName("cardTitle")
        self.status_label = QLabel("未开始")
        apply_tag(self.status_label, "badgeMuted")
        header.addWidget(title)
        header.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignVCenter)
        header.addStretch()
        card_layout.addLayout(header)

        metrics = QHBoxLayout()
        metrics.setSpacing(12)
        self.correct_value = self._metric(metrics, "正确")
        self.failed_value = self._metric(metrics, "失败")
        self.accuracy_value = self._metric(metrics, "正确率")
        self.min_value = self._metric(metrics, "最低耗时")
        self.max_value = self._metric(metrics, "最高耗时")
        self.avg_value = self._metric(metrics, "平均耗时")
        card_layout.addLayout(metrics)

        self.last_text = QLabel("答对 60 题即通过，最多 100 题。")
        self.last_text.setObjectName("muted")
        self.last_text.setWordWrap(True)
        card_layout.addWidget(self.last_text)
        layout.addWidget(card)

    def _metric(self, layout, caption):
        box = QVBoxLayout()
        box.setSpacing(2)
        value = QLabel("—")
        value.setObjectName("metricValue")
        label = QLabel(caption)
        label.setObjectName("muted")
        box.addWidget(value)
        box.addWidget(label)
        layout.addLayout(box, 1)
        return value

    def reset(self):
        self.update_stats({
            "correct": 0,
            "failed": 0,
            "accuracy": None,
            "min_seconds": None,
            "max_seconds": None,
            "avg_seconds": None,
            "status": "未开始",
            "last_text": "",
        })

    def update_stats(self, summary):
        self.correct_value.setText(str(summary.get("correct", 0)))
        self.failed_value.setText(str(summary.get("failed", 0)))
        accuracy = summary.get("accuracy")
        self.accuracy_value.setText("—" if accuracy is None else f"{accuracy * 100:.0f}%")
        self.min_value.setText(self._seconds(summary.get("min_seconds")))
        self.max_value.setText(self._seconds(summary.get("max_seconds")))
        self.avg_value.setText(self._seconds(summary.get("avg_seconds")))
        status = summary.get("status") or "未开始"
        kind = "badgeMuted"
        if status in ("已通过", "已达标"):
            kind = "badgeOk"
        elif status == "未通过":
            kind = "badgeDanger"
        apply_tag(self.status_label, kind)
        self.status_label.setText(status)
        last_text = summary.get("last_text") or "答对 60 题即通过，最多 100 题。"
        self.last_text.setText(last_text)

    def _seconds(self, value):
        if value is None:
            return "—"
        return f"{value:.1f}s"





class ProbeThread(QThread):
    finished_result = Signal(list)

    def __init__(self, model_type, base_url, model, api_key, jev_key, include_jev=False):
        super().__init__()
        self.model_type = model_type
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self.jev_key = jev_key
        self.include_jev = include_jev

    def run(self):
        results = probe_model(
            self.model_type, self.base_url, self.model, self.api_key, self.jev_key, self.include_jev
        )
        self.finished_result.emit(results)


class ModelListThread(QThread):
    """拉取 DeepSeek 当前模型列表。"""

    finished_models = Signal(list, str)

    def __init__(self, base_url, api_key, parent=None):
        super().__init__(parent)
        self.base_url = base_url
        self.api_key = api_key

    def run(self):
        try:
            self.finished_models.emit(list_models(self.base_url, self.api_key), "")
        except Exception as exc:
            self.finished_models.emit([], str(exc))


class ModelConfigWidget(QWidget):
    """模型配置组件"""
    
    def __init__(self, model_type, parent=None):
        super().__init__(parent)
        self.model_type = model_type
        self.answer_mode = "ds"
        self.probe_thread = None
        self.model_list_thread = None
        self._model_list_gen = 0
        self.initUI()
        self.load_settings()

    def _add_field(self, layout, label_text, widget):
        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        layout.addWidget(label)
        layout.addWidget(widget)
    
    def initUI(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(14)

        descriptions = {
            "deepseek": "DeepSeek 按所选思考强度作答，程序再提交。",
            "custom": "兼容 OpenAI 格式的接口。思考模型容易超时，尽量别用。",
        }
        self.mode_desc = QLabel(descriptions.get(self.model_type, ""))
        self.mode_desc.setObjectName("muted")
        self.mode_desc.setWordWrap(True)
        main_layout.addWidget(self.mode_desc)

        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("必填")
        self._add_field(main_layout, "API Key", self.key_input)

        self.get_key_link = QLabel()
        self.get_key_link.setObjectName("linkLabel")
        self.get_key_link.setTextFormat(Qt.TextFormat.RichText)
        self.get_key_link.setOpenExternalLinks(True)
        main_layout.addWidget(self.get_key_link)

        self.url_input = QLineEdit()
        self._add_field(main_layout, "API Base URL", self.url_input)

        if self.model_type == "deepseek":
            self.model_input = QComboBox()
            self.model_input.setMinimumHeight(36)
            self.model_input.setItemDelegate(ComboItemDelegate(self.model_input))
            view = self.model_input.view()
            view.setFrameShape(QFrame.Shape.NoFrame)
            view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.model_hint = QLabel("")
            self.model_hint.setObjectName("muted")
            self.model_hint.setWordWrap(True)
        else:
            self.model_input = QLineEdit()
            self.model_hint = None
        self._add_field(main_layout, "模型名称", self.model_input)
        if self.model_hint is not None:
            main_layout.addWidget(self.model_hint)

        self.effort_input = None
        if self.model_type == "deepseek":
            self.effort_input = QComboBox()
            self.effort_input.setMinimumHeight(36)
            self.effort_input.setItemDelegate(ComboItemDelegate(self.effort_input))
            effort_view = self.effort_input.view()
            effort_view.setFrameShape(QFrame.Shape.NoFrame)
            effort_view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.effort_input.addItem("关闭", "disabled")
            self.effort_input.addItem("轻度", "low")
            self.effort_input.addItem("高度", "high")
            self.effort_input.addItem("最大", "max")
            self.effort_input.currentIndexChanged.connect(self._save_effort)
            self._add_field(main_layout, "思考强度", self.effort_input)
            effort_hint = QLabel("关闭最快。轻度、高度、最大会先思考再回答，强度越高越慢。")
            effort_hint.setObjectName("muted")
            effort_hint.setWordWrap(True)
            main_layout.addWidget(effort_hint)

        self.jev_key_label = None
        self.jev_key_input = None
        if self.model_type == "deepseek":
            self.jev_key_label = QLabel("JEV API Key")
            self.jev_key_label.setObjectName("fieldLabel")
            self.jev_key_input = QLineEdit()
            self.jev_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.jev_key_input.setPlaceholderText("TypeSafe API Key")
            main_layout.addWidget(self.jev_key_label)
            main_layout.addWidget(self.jev_key_input)
            self.set_answer_mode("ds")

        self._set_placeholders()
        if self.model_type == "deepseek":
            self.key_input.editingFinished.connect(self._schedule_model_list)
            self.url_input.editingFinished.connect(self._schedule_model_list)

        if self.model_type == "custom":
            tips = QLabel("硅基流动示例：Base URL https://api.siliconflow.cn ，模型 Qwen/Qwen2.5-32B-Instruct。")
            tips.setObjectName("muted")
            tips.setWordWrap(True)
            main_layout.addWidget(tips)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        self.save_btn = QPushButton("保存配置")
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.clicked.connect(self.save_settings)
        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self.test_connection)
        button_row.addWidget(self.save_btn)
        button_row.addWidget(self.test_btn)
        button_row.addStretch()
        main_layout.addLayout(button_row)

        self.probe_label = QLabel("用当前填写的地址和密钥发一次最短请求。")
        self.probe_label.setObjectName("probeIdle")
        self.probe_label.setWordWrap(True)
        main_layout.addWidget(self.probe_label)
        main_layout.addStretch()
    
    def _set_placeholders(self):
        """根据模型类型设置占位符文本和获取密钥链接"""
        if self.model_type == "deepseek":
            self.url_input.setPlaceholderText("例如：https://api.deepseek.com（必填）")
            self.get_key_link.setText("<a href='https://platform.deepseek.com/api_keys'>获取 DeepSeek API Key</a>")
        elif self.model_type == "custom":
            self.url_input.setPlaceholderText("例如：https://api.siliconflow.cn（必填）")
            self.model_input.setPlaceholderText("例如：deepseek-ai/DeepSeek-V3（必填）")
            self.get_key_link.setText("向所用接口的服务商申请密钥")
    
    def load_settings(self):
        """加载设置"""
        config = load_model_config(self.model_type)
        api_key = load_api_key(self.model_type)
        
        self.url_input.setText(config['base_url'])
        self._set_model_name(config.get('model') or "")
        self.key_input.setText(api_key)
        if self.jev_key_input is not None:
            self.jev_key_input.setText(load_api_key('jev'))
        if self.effort_input is not None:
            self._set_effort(config.get("reasoning_effort") or "low")
        if self.model_type == "deepseek":
            self._schedule_model_list()
    
    def _form_values(self):
        api_key = self.key_input.text().strip()
        base_url = self.url_input.text().strip()
        model_name = self._model_name()
        jev_key = self.jev_key_input.text().strip() if self.jev_key_input is not None else ""
        missing = []
        if not api_key:
            missing.append("API Key")
        if not base_url:
            missing.append("API Base URL")
        if not model_name:
            missing.append("模型名称")
        if self._jev_required() and not jev_key:
            missing.append("JEV API Key")
        if missing:
            return None, "请填写：" + "、".join(missing)
        if not base_url.startswith(("http://", "https://")):
            return None, "API Base URL 需要以 http:// 或 https:// 开头"
        if len(api_key) < 10 or (self._jev_required() and len(jev_key) < 10):
            return None, "API Key 太短，请检查是否粘贴完整"
        return {
            "api_key": api_key,
            "base_url": base_url,
            "model": model_name,
            "jev_key": jev_key,
        }, ""

    def save_settings(self):
        """保存设置"""
        values, error = self._form_values()
        if error:
            QMessageBox.warning(self, "保存失败", error)
            return
        api_key = values["api_key"]
        base_url = values["base_url"]
        model_name = values["model"]
        jev_key = values["jev_key"]
        
        try:
            # 保存API密钥
            save_api_key(self.model_type, api_key)
            if self._jev_required():
                save_api_key('jev', jev_key)
            
            # 保存模型配置
            save_model_config(
                self.model_type,
                base_url,
                model_name,
                reasoning_effort=self._effort_value(),
            )
            
            window = self.window()
            if hasattr(window, "show_toast"):
                window.show_toast("模型配置已保存")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "保存失败",
                f"保存设置时出现错误：\n{str(e)}\n\n请检查配置是否正确"
            )
    
    def test_connection(self):
        values, error = self._form_values()
        if error:
            self._show_probe("bad", error)
            return
        self.save_btn.setEnabled(False)
        self.test_btn.setEnabled(False)
        self.test_btn.setText("测试中")
        self._show_probe("idle", "正在请求…")
        self.probe_thread = ProbeThread(
            "deepseek" if self.model_type == "deepseek" else self.model_type,
            values["base_url"],
            values["model"],
            values["api_key"],
            values["jev_key"],
            include_jev=self._jev_required(),
        )
        self.probe_thread.finished_result.connect(self._on_probe_finished)
        self.probe_thread.start()

    def _on_probe_finished(self, results):
        self.save_btn.setEnabled(True)
        self.test_btn.setEnabled(True)
        self.test_btn.setText("测试连接")
        lines = []
        ok = True
        for item in results:
            mark = "已连通" if item["ok"] else "失败"
            if not item["ok"]:
                ok = False
            lines.append(f"{item['name']}  {mark}  {item['ms']}ms  {item['detail']}")
        self._show_probe("ok" if ok else "bad", "\n".join(lines))

    def _show_probe(self, kind, text):
        names = {"ok": "probeOk", "bad": "probeBad"}
        self.probe_label.setObjectName(names.get(kind, "probeIdle"))
        self.probe_label.setText(text)
        self.probe_label.style().unpolish(self.probe_label)
        self.probe_label.style().polish(self.probe_label)

    def _jev_required(self):
        return self.model_type == "deepseek" and self.answer_mode == "ds_jev"

    def set_answer_mode(self, mode):
        """ds: 纯 DeepSeek。ds_jev: DeepSeek 梳理后由 JEV 选题。"""
        self.answer_mode = mode
        uses_jev = mode == "ds_jev"
        if self.jev_key_label is not None:
            self.jev_key_label.setVisible(uses_jev)
            self.jev_key_input.setVisible(uses_jev)
        if self.model_type == "deepseek":
            self.mode_desc.setText(
                "DeepSeek 轻度思考并整理上下文，JEV 再从结构化选项里选出序号。"
                if uses_jev else
                "DeepSeek 按所选思考强度作答，程序再提交。"
            )

    def _effort_value(self):
        if self.effort_input is None:
            return None
        return self.effort_input.currentData() or "low"

    def _set_effort(self, effort):
        index = self.effort_input.findData(effort)
        self.effort_input.blockSignals(True)
        self.effort_input.setCurrentIndex(index if index >= 0 else self.effort_input.findData("low"))
        self.effort_input.blockSignals(False)

    def _save_effort(self):
        config = load_model_config("deepseek")
        save_model_config(
            "deepseek",
            config.get("base_url", ""),
            config.get("model", ""),
            config.get("api_key", ""),
            reasoning_effort=self._effort_value(),
        )

    def get_api_key(self):
        """获取API密钥"""
        return self.key_input.text().strip()

    def _model_name(self):
        if isinstance(self.model_input, QComboBox):
            return self.model_input.currentText().strip()
        return self.model_input.text().strip()

    def _set_model_name(self, name):
        if isinstance(self.model_input, QComboBox):
            selected = name or CURRENT_MODELS[0]
            self._fill_models(list(CURRENT_MODELS), selected)
            return
        self.model_input.setText(name)

    def _fill_models(self, ids, selected):
        names = []
        for model_id in ids:
            if model_id and model_id not in names:
                names.append(model_id)
        if selected and selected not in names:
            names.insert(0, selected)
        if not names:
            names = list(CURRENT_MODELS)
        self.model_input.blockSignals(True)
        self.model_input.clear()
        for model_id in names:
            self.model_input.addItem(model_id)
        index = self.model_input.findText(selected) if selected else 0
        self.model_input.setCurrentIndex(index if index >= 0 else 0)
        self.model_input.blockSignals(False)

    def _schedule_model_list(self):
        if self.model_type != "deepseek":
            return
        api_key = self.key_input.text().strip()
        base_url = self.url_input.text().strip()
        selected = self._model_name() or CURRENT_MODELS[0]
        if not api_key or not base_url.startswith(("http://", "https://")):
            self._fill_models(list(CURRENT_MODELS), selected)
            self.model_hint.setText("填写 API Key 后会读取 DeepSeek 当前模型。")
            return
        self._model_list_gen += 1
        generation = self._model_list_gen
        self.model_hint.setText("正在读取 DeepSeek 当前模型…")
        self.model_list_thread = ModelListThread(base_url, api_key, self)
        self.model_list_thread.finished_models.connect(
            lambda ids, error, gen=generation: self._on_models_loaded(gen, ids, error)
        )
        self.model_list_thread.start()

    def _on_models_loaded(self, generation, ids, error):
        if generation != self._model_list_gen:
            return
        selected = self._model_name() or CURRENT_MODELS[0]
        if error or not ids:
            self._fill_models(list(CURRENT_MODELS), selected)
            self.model_hint.setText(error or "读取失败，先显示已知模型。")
            return
        self._fill_models(ids, selected)
        self.model_hint.setText("已读取 DeepSeek 当前模型。")


class SettingsWidget(QWidget):
    """设置页面组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        self.current_model_type = "deepseek"  # 默认模型
        self.initUI()
    
    def initUI(self):
        """初始化UI"""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        body.setObjectName("scrollBody")
        layout = QVBoxLayout(body)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        subtitle = QLabel("填写密钥后可以先测试连接，再保存。")
        subtitle.setObjectName("muted")
        layout.addWidget(subtitle)

        self._setup_model_selection(layout)
        self._setup_model_config(layout)
        self.on_model_changed(self.model_combo.currentIndex())
        layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll)
    
    def _setup_model_selection(self, layout):
        """设置模型选择区域"""
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)
        label = QLabel("答题模式")
        label.setObjectName("fieldLabel")
        self.model_combo = QComboBox()
        self.model_combo.setMinimumHeight(36)
        self.model_combo.setItemDelegate(ComboItemDelegate(self.model_combo))
        view = self.model_combo.view()
        view.setFrameShape(QFrame.Shape.NoFrame)
        view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.model_combo.addItem("纯 DeepSeek", "deepseek")
        self.model_combo.addItem("DeepSeek + JEV", "deepseek_jev")
        self.model_combo.addItem("自定义模型", "custom")
        saved_mode = load_answer_mode()
        saved_index = self.model_combo.findData(saved_mode)
        if saved_index >= 0:
            self.model_combo.setCurrentIndex(saved_index)
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)
        card_layout.addWidget(label)
        card_layout.addWidget(self.model_combo)
        layout.addWidget(card)
    
    def _setup_model_config(self, layout):
        """设置模型配置区域"""
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        self.model_stack = QStackedWidget()
        self.deepseek_widget = ModelConfigWidget("deepseek")
        self.model_stack.addWidget(self.deepseek_widget)
        self.custom_widget = ModelConfigWidget("custom")
        self.model_stack.addWidget(self.custom_widget)
        card_layout.addWidget(self.model_stack)
        layout.addWidget(card)
    
    def on_model_changed(self, index):
        """模型选择改变时的回调"""
        model_data = self.model_combo.itemData(index)
        self.current_model_type = model_data
        save_answer_mode(model_data)
        if model_data == "custom":
            self.model_stack.setCurrentIndex(1)
        else:
            self.model_stack.setCurrentIndex(0)
            self.deepseek_widget.set_answer_mode(
                "ds_jev" if model_data == "deepseek_jev" else "ds"
            )
    
    def get_current_model_info(self):
        """获取当前模型信息"""
        if self.current_model_type == "deepseek_jev":
            api_key = self.deepseek_widget.get_api_key()
            model_choice_value = "4"
            label = "DeepSeek + JEV"
        elif self.current_model_type == "custom":
            api_key = self.custom_widget.get_api_key()
            model_choice_value = "3"
            label = "自定义模型"
        else:
            api_key = self.deepseek_widget.get_api_key()
            model_choice_value = "1"
            label = "纯 DeepSeek"
        
        return {
            'type': self.current_model_type,
            'api_key': api_key,
            'choice_value': model_choice_value,
            'label': label,
        }


class GuideAlert(QWidget):
    """首页说明，默认展开，可以收起。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.expanded = True
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("alert")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 12, 12)
        card_layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("使用说明")
        title.setObjectName("cardTitle")
        self.toggle_button = QPushButton("收起")
        self.toggle_button.setObjectName("ghostButton")
        self.toggle_button.clicked.connect(self.toggle)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.toggle_button)
        card_layout.addLayout(header)

        self.body = QLabel(
            "1. 在「模型」页填写密钥，点测试连接，再保存。<br>"
            "2. 在「首页」登录 B 站账号。<br>"
            "3. 点开始答题。<br><br>"
            "<span style='color:#dc2626;'>程序只调用 B 站接口和你配置的模型接口，不会像A/和Z/一样上传你的信息。</span>"
        )
        self.body.setObjectName("alertBody")
        self.body.setTextFormat(Qt.TextFormat.RichText)
        self.body.setWordWrap(True)
        card_layout.addWidget(self.body)
        layout.addWidget(card)

    def toggle(self):
        self.expanded = not self.expanded
        self.body.setVisible(self.expanded)
        self.body.setMaximumHeight(16777215 if self.expanded else 0)
        self.toggle_button.setText("收起" if self.expanded else "展开")
        self.updateGeometry() 