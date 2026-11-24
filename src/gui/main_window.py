"""Main window: inventory browser, loans, overdue list and admin tools."""
import logging
from datetime import date, datetime
from html import escape
from typing import Any

from PySide6.QtCore import QSize, Qt, QStringListModel, QTimer
from PySide6.QtGui import QAction, QBrush, QColor, QIcon, QKeySequence, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QCompleter, QDialog,
                               QFileDialog, QHBoxLayout, QHeaderView, QInputDialog,
                               QLabel, QLineEdit, QMainWindow, QMessageBox,
                               QPushButton, QTabWidget, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from src.dsa.merge_sort import merge_sort
from src.gui.dialogs import AddItemDialog, BorrowDialog
from src.service.backup_service import create_backup, restore_backup
from src.service.inventory_service import InventoryService

log = logging.getLogger("audit")


class MainWindow(QMainWindow):
    MAX_ROWS = 300            # the table shows at most this many rows at once

    def __init__(self, db, svc: InventoryService, auth, images, base, user) -> None:
        super().__init__()
        self.db, self.svc, self.auth = db, svc, auth
        self.images, self.base, self.user = images, base, user
        self.is_admin = user["role"] == "Admin"
        self.setWindowTitle(f"Engineering Equipment Inventory - "
                            f"{user['full_name']} ({user['role']})")
        self.resize(1150, 700)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_inventory_tab(), "Inventory")
        self.tabs.addTab(self._build_loans_tab(),
                         "Active loans" if self.is_admin else "My loans")
        self.tabs.addTab(self._build_overdue_tab(), "Overdue")
        self.setCentralWidget(self.tabs)
        self._build_menu()
        self.refresh_all()
        QTimer.singleShot(300, self.launch_alert)

    # ------------------------------------------------------------ building
    def _make_table(self, headers: list[str], stretch: int) -> QTableWidget:
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        t.verticalHeader().setVisible(False)
        header = t.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(stretch, QHeaderView.ResizeMode.Stretch)
        return t

    def _build_inventory_tab(self) -> QWidget:
        page = QWidget()
        outer = QHBoxLayout(page)

        left = QVBoxLayout()
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by name prefix or exact item ID...")
        self.search.setClearButtonEnabled(True)
        self.completer_model = QStringListModel(self)
        completer = QCompleter(self.completer_model, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self.search.setCompleter(completer)
        self.category = QComboBox()
        self.category.addItem("All categories")
        top.addWidget(self.search, 1)
        top.addWidget(self.category)
        if self.is_admin:
            add = QPushButton("Add item")
            add.clicked.connect(self.on_add)
            top.addWidget(add)
        left.addLayout(top)

        self.table = self._make_table(
            ["Photo", "Name", "Category", "Available", "Condition", "Location"], 1)
        self.table.setIconSize(QSize(56, 56))
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 70)
        left.addWidget(self.table)
        outer.addLayout(left, 1)

        right = QVBoxLayout()
        self.photo = QLabel("No item selected")
        self.photo.setFixedSize(300, 230)
        self.photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.photo.setStyleSheet("border: 1px solid gray;")
        self.details = QLabel("")
        self.details.setWordWrap(True)
        self.details.setTextFormat(Qt.TextFormat.RichText)
        self.details.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.details.setFixedWidth(300)
        self.btn_borrow = QPushButton("Borrow")
        self.btn_borrow.clicked.connect(self.on_borrow)
        right.addWidget(self.photo)
        right.addWidget(self.details)
        right.addWidget(self.btn_borrow)
        self.btn_image = QPushButton("Change image")
        self.btn_delete = QPushButton("Delete item")
        self.btn_image.clicked.connect(self.on_change_image)
        self.btn_delete.clicked.connect(self.on_delete)
        if self.is_admin:
            right.addWidget(self.btn_image)
            right.addWidget(self.btn_delete)
        right.addStretch(1)
        outer.addLayout(right)

        self.search.textChanged.connect(lambda _t: self.apply_filters())
        self.category.currentIndexChanged.connect(lambda _i: self.apply_filters())
        self.table.itemSelectionChanged.connect(self.show_detail)
        return page

    def _build_loans_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.loans_table = self._make_table(
            ["Loan #", "Item", "Borrower", "Role", "Borrowed", "Due", "Purpose"], 6)
        btn = QPushButton("Return selected loan")
        btn.clicked.connect(self.on_return)
        legend = QLabel("Rows in red are overdue.")
        layout.addWidget(self.loans_table)
        layout.addWidget(legend)
        layout.addWidget(btn)
        return page

    def _build_overdue_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.overdue_table = self._make_table(
            ["Days overdue", "Item", "Borrower", "Due date", "Loan #"], 1)
        btn = QPushButton("Refresh overdue list")
        btn.clicked.connect(self.refresh_overdue)
        layout.addWidget(self.overdue_table)
        layout.addWidget(btn)
        return page

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        if self.is_admin:
            file_menu.addAction("Back up data...", self.on_backup)
            file_menu.addAction("Restore from backup...", self.on_restore)
            file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        toolbar = self.addToolBar("Main")
        refresh = QAction("Refresh", self)
        refresh.setShortcut(QKeySequence("F5"))
        refresh.triggered.connect(lambda: self.refresh_all())
        toolbar.addAction(refresh)
        if self.is_admin:
            undo = QAction("Undo last return", self)
            undo.setShortcut(QKeySequence("Ctrl+Z"))
            undo.triggered.connect(self.on_undo)
            toolbar.addAction(undo)

    # ------------------------------------------------------------ refreshing
    def refresh_all(self, keep: int | None = None) -> None:
        if keep is None:
            keep = self.selected_item_id()
        self.refresh_categories()
        self.apply_filters(select=keep)
        self.refresh_loans()
        self.refresh_overdue()

    def refresh_categories(self) -> None:
        current = self.category.currentText()
        names = merge_sort(list({i["category"] for i in self.svc.browse()}),
                           key=str.lower)
        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItem("All categories")
        self.category.addItems(names)
        index = self.category.findText(current)
        self.category.setCurrentIndex(index if index >= 0 else 0)
        self.category.blockSignals(False)

    def apply_filters(self, select: int | None = None) -> None:
        """Live search (trie + AVL), exact ID match, then the category filter."""
        if select is None:
            select = self.selected_item_id()
        text = self.search.text().strip()
        items = self.svc.search_by_prefix(text) if text else self.svc.browse()
        if text.isdigit():
            hit = self.svc.get_by_id(int(text))
            if hit is not None and all(i["item_id"] != hit["item_id"] for i in items):
                items = [hit] + items
        if self.category.currentIndex() > 0:
            wanted = self.category.currentText().lower()
            items = [i for i in items if i["category"].lower() == wanted]

        suggestions = merge_sort(self.svc.names.search_prefix(text), key=str.lower) if text else []
        self.completer_model.setStringList(suggestions[:10])

        total = len(items)
        items = items[:self.MAX_ROWS]
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self.table.setRowCount(len(items))
        for row, it in enumerate(items):
            first = QTableWidgetItem()
            first.setData(Qt.ItemDataRole.UserRole, it["item_id"])
            if it["image_file"]:
                pm = QPixmap(str(self.images.thumb_path(it["image_file"])))
                if not pm.isNull():
                    first.setIcon(QIcon(pm))
            self.table.setItem(row, 0, first)
            cells = [it["name"], it["category"], f"{it['available']} / {it['quantity']}",
                     it["item_condition"], it["location"]]
            for col, value in enumerate(cells, start=1):
                self.table.setItem(row, col, QTableWidgetItem(value))
            self.table.setRowHeight(row, 60)
            if it["item_id"] == select:
                self.table.selectRow(row)
        self.table.blockSignals(False)
        shown = f"Showing {len(items)} of {total} items"
        if total > len(items):
            shown += " (type more to narrow down)"
        self.statusBar().showMessage(shown)
        self.show_detail()

    def selected_item_id(self) -> int | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        return self.table.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)

    def show_detail(self) -> None:
        item_id = self.selected_item_id()
        it = self.svc.get_by_id(item_id) if item_id is not None else None
        for button in (self.btn_borrow, self.btn_image, self.btn_delete):
            button.setEnabled(it is not None)
        if it is None:
            self.photo.setText("No item selected")
            self.details.setText("")
            return
        pm = QPixmap(str(self.images.image_path(it["image_file"]))) if it["image_file"] else QPixmap()
        if pm.isNull():
            self.photo.setText("No photo")
        else:
            self.photo.setPixmap(pm.scaled(300, 230, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation))
        facts = [("Item ID", it["item_id"]), ("Category", it["category"]),
                 ("Manufacturer", it["manufacturer"]), ("Model", it["model"]),
                 ("Serial No.", it["serial_no"]), ("Condition", it["item_condition"]),
                 ("Location", it["location"]), ("Acquired", it["date_acquired"]),
                 ("Available", f"{it['available']} of {it['quantity']}")]
        rows = "".join(f"<tr><td><b>{k}:</b>&nbsp;</td><td>{escape(str(v))}</td></tr>"
                       for k, v in facts)
        text = f"<h3>{escape(it['name'])}</h3><table>{rows}</table>"
        waiting = self.svc.waitlist_size(item_id)
        if waiting:
            nxt = self.svc.next_in_line(item_id)
            text += (f"<p><b>Waitlist:</b> {waiting} waiting. "
                     f"Next in line: {escape(nxt['borrower_name'])}</p>")
        self.details.setText(text)
        self.btn_borrow.setText("Borrow" if it["available"] > 0 else "Join waitlist")

    def _fill(self, table: QTableWidget, rows: list[tuple[list[Any], bool]]) -> None:
        table.setRowCount(len(rows))
        for r, (cells, overdue) in enumerate(rows):
            for c, value in enumerate(cells):
                cell = QTableWidgetItem(str(value))
                if overdue:
                    cell.setBackground(QBrush(QColor(255, 220, 220)))
                    cell.setForeground(QBrush(QColor(0, 0, 0)))
                table.setItem(r, c, cell)

    def visible_loans(self) -> list[dict[str, Any]]:
        loans = self.svc.get_active_loans()
        if not self.is_admin:
            loans = [l for l in loans if l["borrower_id"] == self.user["username"]]
        return merge_sort(loans, key=lambda l: (l["due_date"], l["loan_id"]))

    def visible_overdue(self) -> list[dict[str, Any]]:
        loans = self.svc.overdue_loans()
        if not self.is_admin:
            loans = [l for l in loans if l["borrower_id"] == self.user["username"]]
        return loans

    def _item_name(self, item_id: int) -> str:
        it = self.svc.get_by_id(item_id)
        return it["name"] if it else f"#{item_id}"

    def refresh_loans(self) -> None:
        today = date.today().isoformat()
        rows = [([l["loan_id"], self._item_name(l["item_id"]),
                  f"{l['borrower_name']} ({l['borrower_id']})", l["role"],
                  l["borrowed_on"], l["due_date"], l["purpose"]], l["due_date"] < today)
                for l in self.visible_loans()]
        self._fill(self.loans_table, rows)

    def refresh_overdue(self) -> None:
        rows = [([l["days_overdue"], self._item_name(l["item_id"]),
                  f"{l['borrower_name']} ({l['borrower_id']})", l["due_date"], l["loan_id"]], True)
                for l in self.visible_overdue()]
        self._fill(self.overdue_table, rows)

    def launch_alert(self) -> None:
        overdue = self.visible_overdue()
        if overdue:
            self.tabs.setCurrentIndex(2)
            worst = overdue[0]
            QMessageBox.warning(
                self, "Overdue items",
                f"{len(overdue)} loan(s) are overdue.\nMost overdue: "
                f"{self._item_name(worst['item_id'])} by {worst['borrower_name']} "
                f"({worst['days_overdue']} days).")

    # ------------------------------------------------------------ actions
    def on_add(self) -> None:
        dlg = AddItemDialog(self.svc, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh_all(keep=dlg.new_item_id)

    def on_borrow(self) -> None:
        item_id = self.selected_item_id()
        it = self.svc.get_by_id(item_id) if item_id is not None else None
        if it is None:
            return
        dlg = BorrowDialog(it, self.user, self.is_admin, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        v = dlg.values
        try:
            kind, ref = self.svc.request_item(item_id, v["borrower_id"], v["borrower_name"],
                                              v["role"], v["purpose"], v["due_date"])
        except ValueError as e:
            QMessageBox.warning(self, "Cannot complete request", str(e))
            return
        if kind == "loan":
            QMessageBox.information(self, "Borrowed",
                                    f"Loan #{ref} created. Due {v['due_date']}.")
        else:
            QMessageBox.information(self, "Waitlist",
                                    "No units were available, so you were added to the waitlist.")
        self.refresh_all(keep=item_id)

    def on_return(self) -> None:
        row = self.loans_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Return", "Select a loan in the table first.")
            return
        loan_id = int(self.loans_table.item(row, 0).text())
        condition, ok = QInputDialog.getItem(
            self, "Return item", "Condition of the returned item:",
            ["Good", "Damaged", "Lost"], 0, False)
        if not ok:
            return
        if condition == "Lost":
            sure = QMessageBox.question(
                self, "Confirm",
                "Mark this item as LOST? The total quantity will be reduced.")
            if sure != QMessageBox.StandardButton.Yes:
                return
        try:
            info = self.svc.return_item(loan_id, condition)
        except ValueError as e:
            QMessageBox.warning(self, "Cannot return", str(e))
            return
        message = f"Loan #{loan_id} returned as {condition}."
        if info["promoted_wait"]:
            message += (f"\n\n{info['promoted_wait']['borrower_name']} was first on the "
                        f"waitlist and now has the item (7-day loan).")
        QMessageBox.information(self, "Returned", message)
        self.refresh_all()

    def on_undo(self) -> None:
        try:
            info = self.svc.undo_last_return()
        except ValueError as e:
            QMessageBox.information(self, "Undo", str(e))
            return
        QMessageBox.information(self, "Undo", f"The return of loan #{info['loan_id']} was undone.")
        self.refresh_all()

    def on_delete(self) -> None:
        item_id = self.selected_item_id()
        it = self.svc.get_by_id(item_id) if item_id is not None else None
        if it is None:
            return
        sure = QMessageBox.question(
            self, "Delete item",
            f"Delete '{it['name']}' permanently? This cannot be undone.")
        if sure != QMessageBox.StandardButton.Yes:
            return
        try:
            self.svc.delete_item(item_id)
        except ValueError as e:
            QMessageBox.warning(self, "Cannot delete", str(e))
            return
        self.refresh_all(keep=-1)

    def on_change_image(self) -> None:
        item_id = self.selected_item_id()
        if item_id is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose image", "", "Images (*.png *.jpg *.jpeg)")
        if not path:
            return
        try:
            self.svc.set_item_image(item_id, path)
        except ValueError as e:
            QMessageBox.warning(self, "Cannot use image", str(e))
            return
        self.refresh_all(keep=item_id)

    def on_backup(self) -> None:
        folder = self.base / "backups"
        folder.mkdir(parents=True, exist_ok=True)
        default = str(folder / f"backup_{datetime.now():%Y%m%d_%H%M%S}.zip")
        path, _ = QFileDialog.getSaveFileName(self, "Save backup", default, "Zip files (*.zip)")
        if not path:
            return
        try:
            dest = create_backup(self.db, self.base, path)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "Backup failed", str(e))
            return
        log.info("BACKUP file=%s user=%s", dest, self.user["username"])
        QMessageBox.information(self, "Backup", f"Backup saved to:\n{dest}")

    def on_restore(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose backup", str(self.base / "backups"), "Zip files (*.zip)")
        if not path:
            return
        sure = QMessageBox.question(
            self, "Restore backup",
            "This REPLACES all current data (items, loans, users, images) with the backup.\n"
            "Continue?")
        if sure != QMessageBox.StandardButton.Yes:
            return
        try:
            restore_backup(self.db, self.base, path)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "Restore failed", str(e))
            return
        self.svc = InventoryService(self.db, self.images)     # reload every structure
        self.svc.current_user = self.user["username"]
        log.info("RESTORE file=%s user=%s", path, self.user["username"])
        self.refresh_all(keep=-1)
        QMessageBox.information(self, "Restore", "Backup restored.")