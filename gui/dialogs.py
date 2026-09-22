#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

import qrcode
import requests
from io import BytesIO
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QCheckBox, QWidget,
                             QScrollArea, QFrame)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QPixmap


class QRCodeDialog(QDialog):
    """二维码登录对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.url = None
        self.login_result = False
        self.initUI()
    
    def initUI(self):
        """初始化UI"""
        self.setWindowTitle("B站扫码登录")
        self.setMinimumSize(300, 400)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # 提示文本
        hint_label = QLabel("请使用哔哩哔哩 APP 扫描二维码登录")
        hint_label.setObjectName("cardTitle")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint_label)
        
        # 二维码图像
        self.qrcode_label = QLabel()
        self.qrcode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qrcode_label.setMinimumSize(200, 200)
        layout.addWidget(self.qrcode_label)
        
        # 状态提示
        self.status_label = QLabel("等待扫码...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.setObjectName("outlineButton")
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(cancel_button)
    
    def set_qr_code(self, url):
        """设置二维码图像"""
        self.url = url
        
        try:
            # 生成二维码图像
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=5,
                border=2,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            # 创建图像
            img = qr.make_image(fill_color="black", back_color="white")
            
            # 将PIL图像转换为QPixmap
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue())
            
            # 缩放图像到合适的大小
            pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, 
                                  Qt.TransformationMode.SmoothTransformation)
            
            # 显示二维码
            self.qrcode_label.setPixmap(pixmap)
            
            # 以文本方式也显示链接
            self.status_label.setText(f"<a href='{url}'>如果二维码无法显示，点击这里打开链接</a>")
            self.status_label.setOpenExternalLinks(True)
        except Exception as e:
            self.status_label.setText(f"生成二维码失败: {e}")
    
    def set_status(self, status):
        """设置状态提示文本"""
        self.status_label.setText(status)
    
    def set_login_result(self, success):
        """设置登录结果"""
        self.login_result = success
        if success:
            self.set_status("登录成功！")
            self.accept()
        else:
            self.set_status("登录失败，请重试")


def fetch_captcha_bytes(url):
    """用当前登录态拉取验证码。裸请求会被 B 站拒绝，浏览器打开则带着 Cookie。"""
    from tools.request_b import headers as bili_headers

    request_headers = {
        "User-Agent": bili_headers.get("User-Agent") or "Mozilla/5.0",
        "Referer": "https://www.bilibili.com/",
        "Cookie": bili_headers.get("cookie") or "",
    }
    response = requests.get(url, headers=request_headers, timeout=10)
    response.raise_for_status()
    content_type = (response.headers.get("Content-Type") or "").lower()
    if content_type.startswith("image/") or _looks_like_image(response.content):
        return response.content

    text = response.text or ""
    image_url = _image_url_from_html(text)
    if not image_url:
        raise Exception("返回的不是图片")
    if image_url.startswith("//"):
        image_url = "https:" + image_url
    nested = requests.get(image_url, headers=request_headers, timeout=10)
    nested.raise_for_status()
    if not _looks_like_image(nested.content) and not (nested.headers.get("Content-Type") or "").lower().startswith("image/"):
        raise Exception("返回的不是图片")
    return nested.content


def _looks_like_image(data):
    return (
        data.startswith(b"\x89PNG")
        or data.startswith(b"\xff\xd8")
        or data.startswith(b"GIF87a")
        or data.startswith(b"GIF89a")
        or data.startswith(b"RIFF")
    )


def _image_url_from_html(text):
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', text, re.I)
    if match:
        return match.group(1)
    match = re.search(r'url\((["\']?)(https?:[^)\'"]+)\1\)', text, re.I)
    return match.group(2) if match else ""


class CaptchaDialog(QDialog):
    """验证码输入对话框"""
    
    def __init__(self, url=None, categories=None, parent=None):
        super().__init__(parent)
        self.url = url
        self.categories = categories
        self.captcha_text = ""
        self.category_ids = ""
        self.initUI()
    
    def initUI(self):
        """分类和验证码在同一个窗口里提交。"""
        self.setWindowTitle("开始答题")
        self.setMinimumWidth(420)
        self.category_checks = []
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("选择分类并填写验证码")
        title.setObjectName("cardTitle")
        layout.addWidget(title)
        
        if self.categories:
            self._setup_categories_section(layout)
        
        if self.url:
            self._setup_captcha_image_section(layout)
            self._setup_captcha_input_section(layout)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #dc2626; background: transparent;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)
        
        self._setup_buttons(layout)
    
    def _setup_categories_section(self, layout):
        """设置分类选择区域"""
        cats_label = QLabel("分类")
        cats_label.setObjectName("fieldLabel")
        layout.addWidget(cats_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMaximumHeight(168)
        body = QWidget()
        box = QVBoxLayout(body)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(6)
        for cat in self.categories:
            name = cat.get("name") or str(cat.get("id"))
            check = QCheckBox(name)
            check.setProperty("category_id", str(cat.get("id")))
            self.category_checks.append(check)
            box.addWidget(check)
        scroll.setWidget(body)
        layout.addWidget(scroll)
    
    def _setup_captcha_image_section(self, layout):
        """设置验证码图片区域"""
        # 添加验证码图片标签
        self.captcha_img_label = QLabel("加载验证码中...")
        self.captcha_img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.captcha_img_label.setMinimumHeight(100)
        layout.addWidget(self.captcha_img_label)
        
        # 加载验证码图片
        self.load_captcha_image()
        
        url_label = QLabel(f"<a href='{self.url}'>图片打不开时打开链接</a>")
        url_label.setObjectName("linkLabel")
        url_label.setOpenExternalLinks(True)
        layout.addWidget(url_label)
    
    def _setup_captcha_input_section(self, layout):
        """设置验证码输入区域"""
        captcha_label = QLabel("验证码")
        captcha_label.setObjectName("fieldLabel")
        layout.addWidget(captcha_label)
        
        self.captcha_input = QLineEdit()
        layout.addWidget(self.captcha_input)
    
    def _setup_buttons(self, layout):
        """设置按钮区域"""
        row = QHBoxLayout()
        row.setSpacing(8)
        cancel_button = QPushButton("取消")
        cancel_button.setObjectName("outlineButton")
        cancel_button.clicked.connect(self.reject)
        ok_button = QPushButton("确定")
        ok_button.setObjectName("primaryButton")
        ok_button.clicked.connect(self.accept)
        row.addWidget(cancel_button)
        row.addWidget(ok_button)
        layout.addLayout(row)
    
    def load_captcha_image(self):
        """加载验证码图片"""
        class ImageDownloader(QThread):
            image_loaded = Signal(bytes)
            failed = Signal(str)

            def __init__(self, url):
                super().__init__()
                self.url = url

            def run(self):
                try:
                    self.image_loaded.emit(fetch_captcha_bytes(self.url))
                except Exception as e:
                    self.failed.emit(str(e))

        self.downloader = ImageDownloader(self.url)
        self.downloader.image_loaded.connect(self.set_captcha_image)
        self.downloader.failed.connect(self._show_captcha_error)
        self.downloader.start()

    def _show_captcha_error(self, message):
        self.captcha_img_label.setText(f"验证码图片加载失败：{message}")
    
    def set_captcha_image(self, image_data):
        """设置验证码图片"""
        try:
            pixmap = QPixmap()
            if not pixmap.loadFromData(image_data):
                from PIL import Image
                image = Image.open(BytesIO(image_data))
                buffer = BytesIO()
                image.convert("RGBA").save(buffer, format="PNG")
                pixmap.loadFromData(buffer.getvalue())
            if pixmap.isNull():
                self._show_captcha_error("图片格式无法显示")
                return

            if pixmap.width() > 400:
                pixmap = pixmap.scaled(400, pixmap.height() * 400 // pixmap.width(), 
                                      Qt.AspectRatioMode.KeepAspectRatio, 
                                      Qt.TransformationMode.SmoothTransformation)
            
            self.captcha_img_label.setPixmap(pixmap)
            self.captcha_img_label.setText("")
        except Exception as e:
            self._show_captcha_error(str(e))
    
    def accept(self):
        """接受对话框输入"""
        ids = [
            check.property("category_id")
            for check in self.category_checks
            if check.isChecked() and check.property("category_id")
        ]
        self.category_ids = ",".join(ids)
        self.captcha_text = self.captcha_input.text().strip() if hasattr(self, "captcha_input") else ""
        if self.category_checks and not self.category_ids:
            self.error_label.setText("请至少选择一个分类")
            return
        if self.url and not self.captcha_text:
            self.error_label.setText("请输入验证码")
            return
        super().accept() 