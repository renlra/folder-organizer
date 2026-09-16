import os
import plistlib
import sys

# Requires: pip install pefile
if sys.platform == "win32":
    import win32api


def get_file_description(file_path):
    """Universal router that detects platform file types and extracts descriptions."""
    if not os.path.exists(file_path):
        return "File not found."

    # 1. Windows Executable (.exe / .dll)
    if file_path.lower().endswith((".exe", ".dll")):
        return _get_windows_desc(file_path)

    # 2. macOS App Bundle (.app folder)
    elif file_path.endswith(".app") or os.path.isdir(file_path):
        return _get_macos_desc(file_path)

    # 3. Linux / General Files (Checks for companion .desktop files or ELF notes)
    else:
        return _get_linux_desc(file_path)


# --- Platform-Specific Parsers ---


def _get_windows_desc(path):
    try:
        # 1. Get the language and codepage translation IDs
        lang, codepage = win32api.GetFileVersionInfo(
            path, "\\VarFileInfo\\Translation"
        )[0]

        # 2. Construct the exact string path using those IDs
        str_path = f"\\StringFileInfo\\{lang:04x}{codepage:04x}\\FileDescription"

        # 3. Query the description
        description = win32api.GetFileVersionInfo(path, str_path)
        return description.strip() if description else "No description found."
    except Exception as e:
        return f"Error reading Windows version info: {e}"


def _get_macos_desc(path):
    # macOS apps are directories ending in .app containing an Info.plist
    plist_path = os.path.join(path, "Contents", "Info.plist")
    if not os.path.exists(plist_path):
        return "Not a valid macOS .app bundle (missing Info.plist)."

    try:
        with open(plist_path, "rb") as f:
            plist_data = plistlib.load(f)
            # macOS uses various keys depending on the app
            for key in [
                "CFBundleDisplayName",
                "CFBundleName",
                "NSHumanReadableDescription",
            ]:
                if key in plist_data:
                    return plist_data[key]
    except Exception as e:
        return f"Error reading macOS plist: {e}"
    return "No description found in Info.plist."


def _get_linux_desc(path):
    # Linux raw binaries (ELF) don't have internal descriptions.
    # Usually, GUI apps use a companion .desktop file in /usr/share/applications/
    # Here we check if a matching .desktop file exists nearby or provide a fallback.
    desktop_file = path + ".desktop"
    if os.path.exists(desktop_file):
        try:
            with open(desktop_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("Comment="):
                        return line.split("=", 1)[1].strip()
        except Exception:
            pass

    return "Linux binary (ELF): Raw executables do not store internal descriptions."

def check_if_installer(file_path, keywords) -> bool:
    # Get the description using your cross-platform function
    description = get_file_description(file_path.as_posix())

    if not description or "Error" in description or "not found" in description:
        return False

    # Convert to lowercase to make the search case-insensitive
    desc_lower = description.lower()

    # Check if any of the keywords exist in the description string
    matched_keywords = [kw for kw in keywords if kw in desc_lower]

    if matched_keywords:
        return True

    return False