import json
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

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

        # 3. Settings Checkboxes Layout
        settings_layout = QVBoxLayout()  # Changed to vertical for cleaner stacking

        self.inplace_checkbox = QCheckBox(
            "Organize in-place (use source folder as output)"
        )
        self.inplace_checkbox.setChecked(True)
        self.inplace_checkbox.toggled.connect(self.toggle_inplace_mode)
        settings_layout.addWidget(self.inplace_checkbox)

        options_layout = QHBoxLayout()
        self.group_ext_checkbox = QCheckBox("Group by Extension Subfolders")
        self.handle_undef_checkbox = QCheckBox("Move Unknown Extensions to 'Others'")
        options_layout.addWidget(self.group_ext_checkbox)
        options_layout.addWidget(self.handle_undef_checkbox)
        settings_layout.addLayout(options_layout)

        main_layout.addLayout(settings_layout)

        # 4. Action Button
        self.run_button = QPushButton("Run Organizer")
        self.run_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71; 
                color: white; 
                font-weight: bold; 
                font-size: 14pt; 
                padding: 10px;
            }
            QPushButton:pressed {
                background-color: #27ae60;
            }
        """)
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

        inplace = settings.get("organize_in_place", True)
        self.inplace_checkbox.setChecked(inplace)
        self.output_input.setEnabled(not inplace)

        self.log_output.append("Configuration loaded successfully from config.json.")

    def toggle_inplace_mode(self, checked):
        """Greys out the output path input when in-place mode is active"""
        self.output_input.setEnabled(not checked)
        if checked:
            # Mirror source to output if source exists
            if self.source_input.text():
                self.output_input.setText(self.source_input.text())
            self.update_config_setting("organize_in_place", True)
        else:
            self.update_config_setting("organize_in_place", False)

    def select_source_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Source Directory")
        if dir_path:
            self.source_input.setText(dir_path)
            # If in-place is checked, automatically update the output field too
            if self.inplace_checkbox.isChecked():
                self.output_input.setText(dir_path)

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
