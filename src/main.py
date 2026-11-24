"""Entry point. Run from the top folder with:  python -m src.main"""
import sys

from PySide6.QtCore import QLockFile
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from src.bootstrap import bootstrap_app
from src.db.db_manager import get_data_dir
from src.gui.login_dialog import LoginDialog
from src.gui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)

    lock = QLockFile(str(get_data_dir() / "app.lock"))        # single-instance lock
    if not lock.tryLock(100):
        QMessageBox.warning(None, "Already running",
                            "Engineering Inventory is already open.")
        return 0

    db, svc, auth, images, base = bootstrap_app()
    login = LoginDialog(auth)
    if login.exec() != QDialog.DialogCode.Accepted:
        db.close()
        lock.unlock()
        return 0

    svc.current_user = login.user["username"]
    window = MainWindow(db, svc, auth, images, base, login.user)
    window.show()
    code = app.exec()
    db.close()
    lock.unlock()
    return code


if __name__ == "__main__":
    sys.exit(main())