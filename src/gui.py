import sys
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt

from src.core import FolderOrganizer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python Folder Organizer")
        self.setMinimumSize(600, 500)

        self.organizer = FolderOrganizer()

        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # 1. Source Directory Layout
        source_layout = QHBoxLayout()
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("Select folder to organize...")
        source_button = QPushButton("Browse Source...")
        source_button.clicked.connect(self.select_source_folder)
        source_layout.addWidget(QLabel("Source:"))
        source_layout.addWidget(self.source_input)
        source_layout.addWidget(source_button)
        main_layout.addLayout(source_layout)

        # 2. Output Base Directory Layout
        output_layout = QHBoxLayout()
        self.output_input = QLineEdit()
        self.output_input.setPlaceholderText("Select output base destination...")
        output_button = QPushButton("Browse Output...")
        output_button.clicked.connect(self.select_output_folder)
        output_layout.addWidget(QLabel("Output:"))
        output_layout.addWidget(self.output_input)
        output_layout.addWidget(output_button)
        main_layout.addLayout(output_layout)

        # 3. Settings Checkboxes
        settings_layout = QHBoxLayout()
        self.group_ext_checkbox = QCheckBox("Group by Extension Subfolders")
        self.handle_undef_checkbox = QCheckBox("Move Unknown Extensions to 'Others'")
        settings_layout.addWidget(self.group_ext_checkbox)
        settings_layout.addWidget(self.handle_undef_checkbox)
        main_layout.addLayout(settings_layout)

        # 4. Action Button
        self.run_button = QPushButton("Run Organizer")
        self.run_button.setStyleSheet(
            "background-color: #2ecc71; color: white; font-weight: bold; font-size: 14pt; padding: 10px;"
        )
        self.run_button.clicked.connect(self.run_organization)
        main_layout.addWidget(self.run_button)

        # 5. Live Console Log Box
        main_layout.addWidget(QLabel("Activity Log:"))
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet(
            "background-color: #1e1e1e; color: #00ffcc; font-family: Courier; font-size: 10pt;"
        )
        main_layout.addWidget(self.log_output)

        self.setCentralWidget(central_widget)
        self.load_ui_from_config()

    def load_ui_from_config(self):
        settings = self.organizer.config.get("settings", {})
        self.output_input.setText(settings.get("target_base_directory", ""))
        self.group_ext_checkbox.setChecked(settings.get("group_by_extension", False))
        self.handle_undef_checkbox.setChecked(settings.get("handle_undefined", True))
        self.log_output.append("Configuration loaded successfully from config.json.")

    def select_source_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Source Directory")
        if dir_path:
            self.source_input.setText(dir_path)

    def select_output_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.output_input.setText(dir_path)
            self.update_config_setting("target_base_directory", dir_path)

    def update_config_setting(self, key: str, value):
        self.organizer.config["settings"][key] = value
        with open(self.organizer.config_path, "w", encoding="utf-8") as f:
            json.dump(self.organizer.config, f, indent=4)
        self.organizer.load_config()

    def run_organization(self):
        source_dir = self.source_input.text().strip()
        if not source_dir:
            QMessageBox.warning(self, "Warning", "Please select a source folder first!")
            return

        self.update_config_setting(
            "group_by_extension", self.group_ext_checkbox.isChecked()
        )
        self.update_config_setting(
            "handle_undefined", self.handle_undef_checkbox.isChecked()
        )

        self.log_output.append(f"\n--- Starting organization of: {source_dir} ---")
        try:
            self.organizer.organize(source_dir)
            self.log_output.append("Organization completed successfully!")
            QMessageBox.information(
                self, "Success", "Folder organization completed successfully!"
            )
        except Exception as e:
            self.log_output.append(f"ERROR: {str(e)}")
            QMessageBox.critical(self, "Error", f"An error occurred:\n{str(e)}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
