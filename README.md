# Python Folder Organizer

A cross-platform utility tool designed to automatically clean up messy folders (like Downloads) by sorting files into structured categories based on customizable rules.

## Current Progress (Phase 1)
- [x] **Core Backend (`core.py`):** Robust file scanning and moving logic using Python's `pathlib` for cross-platform compatibility (Windows, Linux, macOS).
- [x] **Configurable Rules (`config.json`):** Easily adjust file type mappings, destination paths, and special logic without touching Python code.
- [x] **Advanced Sorting Features:**
  - Standard extension mapping (Documents, Pictures, Archives, etc.).
  - Special video rules (differentiating large movies vs. regular videos using file size and subtitle detection).
  - Optional extension subfolder grouping.
  - Handling for undefined/unknown extensions.
- [ ] **Graphical User Interface (GUI):** PySide6 desktop interface.

## Tech Stack
- **Python 3.x**
- **Pathlib** (for native cross-platform path management)
- **JSON** (for configuration management)

## How to Run the Core Logic (Currently)
You can test the backend engine via python script or interactive shell by importing the `FolderOrganizer` class from `src.core`.