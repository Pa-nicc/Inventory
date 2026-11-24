"""Add-item and borrow dialogs."""
from pathlib import Path
from typing import Any

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QComboBox, QDateEdit, QDialog, QDialogButtonBox,
                               QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QMessageBox, QPushButton, QSpinBox,
                               QVBoxLayout)

from src.service.inventory_service import InventoryService


class AddItemDialog(QDialog):
    """Admin form: all specification fields plus an optional photo."""

    def __init__(self, svc: InventoryService, parent=None) -> None:
        super().__init__(parent)
        self.svc = svc
        self.new_item_id: int | None = None
        self.image_path = ""
        self.setWindowTitle("Add equipment")
        self.setMinimumWidth(420)

        self.name = QLineEdit()
        self.category = QLineEdit()
        self.manufacturer = QLineEdit()
        self.model = QLineEdit()
        self.serial = QLineEdit()
        self.quantity = QSpinBox()
        self.quantity.setRange(1, 9999)
        self.condition = QComboBox()
        self.condition.addItems(["Good", "Fair", "Needs repair"])
        self.location = QLineEdit()
        self.acquired = QDateEdit(QDate.currentDate())
        self.acquired.setCalendarPopup(True)
        self.acquired.setDisplayFormat("yyyy-MM-dd")

        self.preview = QLabel("No image selected")
        self.preview.setFixedSize(160, 120)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet("border: 1px solid gray;")
        choose = QPushButton("Choose image (JPG/PNG, max 2 MB)...")
        choose.clicked.connect(self.choose_image)

        form = QFormLayout()
        form.addRow("Item ID:", QLabel("(assigned automatically)"))
        form.addRow("Name *", self.name)
        form.addRow("Category *", self.category)
        form.addRow("Manufacturer *", self.manufacturer)
        form.addRow("Model *", self.model)
        form.addRow("Serial No. *", self.serial)
        form.addRow("Quantity *", self.quantity)
        form.addRow("Condition", self.condition)
        form.addRow("Storage location *", self.location)
        form.addRow("Date acquired", self.acquired)

        image_row = QHBoxLayout()
        image_row.addWidget(self.preview)
        image_row.addWidget(choose)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(image_row)
        layout.addWidget(buttons)

    def choose_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose image", "", "Images (*.png *.jpg *.jpeg)")
        if not path:
            return
        pm = QPixmap(path)
        if pm.isNull():
            QMessageBox.warning(self, "Image", "That file could not be read as an image.")
            return
        self.image_path = path
        self.preview.setPixmap(pm.scaled(160, 120, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation))

    def accept(self) -> None:
        required = [("Name", self.name), ("Category", self.category),
                    ("Manufacturer", self.manufacturer), ("Model", self.model),
                    ("Serial No.", self.serial), ("Storage location", self.location)]
        for label, field in required:
            if not field.text().strip():
                QMessageBox.warning(self, "Missing information", f"{label} is required.")
                return
        try:
            item_id = self.svc.add_item(
                self.name.text().strip(), self.category.text().strip(),
                self.manufacturer.text().strip(), self.model.text().strip(),
                self.serial.text().strip(), self.quantity.value(),
                self.condition.currentText(), self.location.text().strip(),
                self.acquired.date().toString("yyyy-MM-dd"))
        except ValueError as e:
            QMessageBox.warning(self, "Cannot add item", str(e))
            return
        self.new_item_id = item_id
        if self.image_path:
            try:
                self.svc.set_item_image(item_id, Path(self.image_path))
            except ValueError as e:
                QMessageBox.warning(
                    self, "Item saved without image",
                    f"{e}\n\nYou can attach a photo later with 'Change image'.")
        super().accept()


class BorrowDialog(QDialog):
    """Borrow an item, or join its waitlist when no unit is available."""

    def __init__(self, item: dict[str, Any], user: dict[str, Any],
                 is_admin: bool, parent=None) -> None:
        super().__init__(parent)
        self.values: dict[str, str] = {}
        self.available = item["available"] > 0
        self.setWindowTitle(("Borrow: " if self.available else "Join waitlist: ") + item["name"])
        self.setMinimumWidth(380)

        self.borrower_id = QLineEdit()
        self.borrower_name = QLineEdit()
        self.role = QComboBox()
        self.role.addItems(["Student", "Faculty"])
        if not is_admin:                     # users can only act as themselves
            self.borrower_id.setText(user["username"])
            self.borrower_name.setText(user["full_name"])
            self.role.setCurrentText(user["role"])
            self.borrower_id.setReadOnly(True)
            self.borrower_name.setReadOnly(True)
            self.role.setEnabled(False)
        self.purpose = QLineEdit()
        self.due = QDateEdit(QDate.currentDate().addDays(7))
        self.due.setCalendarPopup(True)
        self.due.setDisplayFormat("yyyy-MM-dd")
        self.due.setMinimumDate(QDate.currentDate())

        form = QFormLayout()
        form.addRow("ID number *", self.borrower_id)
        form.addRow("Name *", self.borrower_name)
        form.addRow("Role *", self.role)
        form.addRow("Purpose *", self.purpose)
        layout = QVBoxLayout(self)
        if self.available:
            form.addRow("Due date *", self.due)
            layout.addLayout(form)
        else:
            note = QLabel("No units are available right now. You will be added to the "
                          "waitlist and get the item automatically (7-day loan) "
                          "when it is returned.")
            note.setWordWrap(True)
            layout.addWidget(note)
            layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self) -> None:
        for label, field in [("ID number", self.borrower_id),
                             ("Name", self.borrower_name), ("Purpose", self.purpose)]:
            if not field.text().strip():
                QMessageBox.warning(self, "Missing information", f"{label} is required.")
                return
        self.values = {
            "borrower_id": self.borrower_id.text().strip(),
            "borrower_name": self.borrower_name.text().strip(),
            "role": self.role.currentText(),
            "purpose": self.purpose.text().strip(),
            "due_date": self.due.date().toString("yyyy-MM-dd"),
        }
        super().accept()