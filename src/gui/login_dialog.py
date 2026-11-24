"""Login window."""
from PySide6.QtWidgets import (QDialog, QFormLayout, QLabel, QLineEdit,
                               QPushButton, QVBoxLayout, QHBoxLayout)

from src.service.auth_service import AuthService


class LoginDialog(QDialog):
    def __init__(self, auth: AuthService) -> None:
        super().__init__()
        self.auth = auth
        self.user = None
        self.setWindowTitle("Engineering Inventory - Login")
        self.setMinimumWidth(340)

        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.error = QLabel("")
        self.error.setStyleSheet("color: #c0392b;")
        hint = QLabel("Sample accounts (first run): admin / admin123, "
                      "2024-001 / student123, fac-001 / faculty123")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray;")

        form = QFormLayout()
        form.addRow("Username / ID:", self.username)
        form.addRow("Password:", self.password)

        login = QPushButton("Log in")
        login.setDefault(True)
        login.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(login)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.error)
        layout.addLayout(buttons)
        layout.addWidget(hint)

    def accept(self) -> None:
        try:
            self.user = self.auth.login(self.username.text(), self.password.text())
        except ValueError as e:
            self.error.setText(str(e))
            self.password.clear()
            return
        super().accept()