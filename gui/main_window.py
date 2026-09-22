#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QTabWidget, QMessageBox, QScrollArea, QFrame,
                             QProxyStyle, QStyle)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor, QPainter

# 导入样式
from .style import STYLE_SHEET

# 导入组件
from .widgets import (LogWidget, StatusWidget, StatsWidget,
                     SettingsWidget, GuideAlert, Toast)
from .dialogs import QRCodeDialog, CaptchaDialog
from .threads import QuizThread, LoginThread, SwitchAccountThread

from scripts.login import is_login


class AppStyle(QProxyStyle):
    """选中标签不再压住底部分割线，线可以铺满整行。"""

    def pixelMetric(self, metric, option=None, widget=None):
        if metric == QStyle.PixelMetric.PM_TabBarBaseOverlap:
            return 0
        return super().pixelMetric(metric, option, widget)


class HeaderTabWidget(QTabWidget):
    """标签条整行白色，右侧空白不露出页面底色。"""

    def paintEvent(self, event):
        super().paintEvent(event)
        bar = self.tabBar()
        painter = QPainter(self)
        painter.fillRect(0, 0, bar.x(), bar.height(), QColor("#ffffff"))
        painter.fillRect(bar.x() + bar.width(), 0, self.width() - bar.x() - bar.width(), bar.height(), QColor("#ffffff"))
        painter.end()


class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.quiz_thread = None
        self.initUI()
        self.setup_connections()
        self.load_initial_state()
    
    def initUI(self):
        """初始化UI"""
        # 设置窗口属性
        app = QApplication.instance()
        if app is not None and not isinstance(app.style(), AppStyle):
            app.setStyle(AppStyle("Fusion"))
        self.setWindowTitle("小B硬核会员答题助手")
        self.resize(920, 800)
        self.setMinimumSize(820, 680)
        
        # 创建中央部件
        central_widget = QWidget()
        central_widget.setObjectName("page")
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建标签页
        self.tab_widget = HeaderTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 创建各个标签页
        self.setup_tabs()
        self.toast = Toast(central_widget)
    
    def setup_tabs(self):
        """设置标签页"""
        # 首页 - 修改为与设置页面一致的布局
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        home_widget = QWidget()
        home_widget.setObjectName("scrollBody")
        home_layout = QVBoxLayout(home_widget)
        home_layout.setContentsMargins(20, 16, 20, 16)
        home_layout.setSpacing(12)

        self.guide_alert = GuideAlert()
        home_layout.addWidget(self.guide_alert)
        
        # 状态组件
        self.status_widget = StatusWidget()
        home_layout.addWidget(self.status_widget)

        self.stats_widget = StatsWidget()
        home_layout.addWidget(self.stats_widget)
        
        # 日志组件
        self.log_widget = LogWidget()
        home_layout.addWidget(self.log_widget, 1)
        
        scroll.setWidget(home_widget)
        self.tab_widget.addTab(scroll, "首页")
        
        # 设置页
        self.settings_widget = SettingsWidget()
        self.tab_widget.addTab(self.settings_widget, "模型")
    
    def setup_connections(self):
        """设置信号连接"""
        # 状态组件信号
        self.status_widget.login_clicked.connect(self.login)
        self.status_widget.logout_clicked.connect(self.logout)
        self.status_widget.switch_account_clicked.connect(self.switch_account)
        self.status_widget.start_quiz_clicked.connect(self.start_quiz)
        self.status_widget.stop_quiz_clicked.connect(self.stop_quiz)
    
    def load_initial_state(self):
        """加载初始状态"""
        # 检查登录状态
        self.status_widget.set_login_status(is_login())
    
    def login(self):
        """登录B站"""
        # 禁用按钮防止重复点击
        self.status_widget.login_clicked.disconnect()
        
        # 添加登录日志
        self.log_widget.append_log("正在准备B站登录...")
        
        # 创建并显示二维码对话框
        qr_dialog = QRCodeDialog(self)
        
        # 创建登录线程
        login_thread = LoginThread()
        
        # 连接信号
        login_thread.update_qr.connect(lambda url: qr_dialog.set_qr_code(url))
        login_thread.login_finished.connect(
            lambda result: self._on_login_finished(result, qr_dialog, login_thread)
        )
        
        # 启动线程
        login_thread.start()
        
        # 显示对话框
        qr_dialog.exec()
    
    def _on_login_finished(self, result, dialog, thread):
        """登录完成后的回调"""
        # 更新UI
        if result and is_login():
            self.status_widget.set_login_status(True)
            self.log_widget.append_log("登录成功")
            dialog.accept()
        else:
            self.log_widget.append_log("登录失败，请重试")
            dialog.reject()
        
        # 重新连接信号
        self.status_widget.login_clicked.connect(self.login)
    
    def logout(self):
        """退出登录"""
        from core.auth_manager import AuthManager
        
        # 创建认证管理器实例
        auth_manager = AuthManager()
        
        # 执行登出
        result = auth_manager.logout()
        
        if result:
            # 更新UI状态
            self.status_widget.set_login_status(False)
            self.log_widget.append_log("已成功退出登录")
        else:
            self.log_widget.append_log("退出登录失败")
    
    def switch_account(self):
        """切换账号"""
        # 添加日志
        self.log_widget.append_log("正在切换账号...")
        
        # 禁用按钮防止重复点击
        self.status_widget.switch_account_clicked.disconnect()
        
        # 创建并显示二维码对话框
        qr_dialog = QRCodeDialog(self)
        
        # 创建切换账号线程
        switch_thread = SwitchAccountThread()
        
        # 连接信号
        switch_thread.logout_signal.connect(
            lambda result: self.log_widget.append_log("已登出当前账号" if result else "登出失败，无法切换账号")
        )
        switch_thread.update_qr.connect(lambda url: qr_dialog.set_qr_code(url))
        switch_thread.finished.connect(
            lambda result: self._on_switch_account_finished(result, qr_dialog, switch_thread)
        )
        
        # 启动线程
        switch_thread.start()
        
        # 显示对话框
        qr_dialog.exec()
    
    def _on_switch_account_finished(self, result, dialog, thread):
        """切换账号完成后的回调"""
        # 更新UI
        if result and is_login():
            self.status_widget.set_login_status(True)
            self.log_widget.append_log("新账号登录成功")
            dialog.accept()
        else:
            if not dialog.login_result:  # 避免重复显示错误消息
                self.log_widget.append_log("登录失败，请重试")
            dialog.reject()
        
        # 重新连接信号
        self.status_widget.switch_account_clicked.connect(self.switch_account)
    
    def start_quiz(self):
        """开始答题"""
        # 检查是否已登录
        if not is_login():
            QMessageBox.warning(self, "未登录", "请先登录B站账号")
            return
        
        # 获取当前模型信息
        model_info = self.settings_widget.get_current_model_info()
        
        if not model_info['api_key']:
            QMessageBox.warning(self, "API密钥缺失", 
                              f"请先在设置中配置{model_info['type'].upper()} API密钥")
            return
        
        # 设置全局模型选择
        import config.config
        config.config.model_choice = model_info['choice_value']
        
        self.log_widget.clear_log()
        self.stats_widget.reset()
        
        # 创建并启动答题线程
        if self.quiz_thread is not None and self.quiz_thread.isRunning():
            self.stop_quiz()
        
        self.quiz_thread = QuizThread()
        self.quiz_thread.log_signal.connect(self.log_widget.append_log)
        self.quiz_thread.stats_signal.connect(self.stats_widget.update_stats)
        self.quiz_thread.finished_signal.connect(self.on_quiz_finished)
        self.quiz_thread.captcha_signal.connect(self.show_captcha_dialog)
        
        # 设置线程中QuizSession的模型选择
        self.quiz_thread.quiz_session.update_model_choice(model_info['choice_value'])
        
        self.quiz_thread.start()
        
        self.log_widget.append_log(f"开始使用 {model_info.get('label', model_info['type'])} 答题...")
        
        self.status_widget.set_quiz_running(True)
    
    def stop_quiz(self):
        """停止答题"""
        if self.quiz_thread is not None and self.quiz_thread.isRunning():
            self.quiz_thread.stop()
            self.log_widget.append_log("正在停止答题...")
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "toast"):
            self.toast.place()

    def show_toast(self, text):
        self.toast.show_message(text)

    def on_quiz_finished(self):
        """答题完成回调"""
        self.status_widget.set_quiz_running(False)
        self.log_widget.append_log("答题已结束")
    
    def show_captcha_dialog(self, url, categories):
        """在主线程中显示验证码对话框"""
        dialog = CaptchaDialog(url, categories, self)
        if dialog.exec():
            if categories:
                self.quiz_thread.set_captcha_result(dialog.captcha_text, dialog.category_ids)
            else:
                self.quiz_thread.set_captcha_result(dialog.captcha_text)
        else:
            # 用户取消了对话框，停止答题
            self.stop_quiz()


def main():
    """主程序入口"""
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle(AppStyle("Fusion"))
    app.setStyleSheet(STYLE_SHEET)
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Link, QColor("#18181b"))
    app.setPalette(palette)
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 