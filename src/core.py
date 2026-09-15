import json
import shutil
from pathlib import Path


class FolderOrganizer:
    def __init__(self, config_path="config.json"):
        self.config_path = Path(config_path)
        self.load_config()

    def load_config(self):
        """Loads or reloads the configuration from the JSON file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

    def get_target_base(self) -> Path:
        """Resolves the target base directory, supporting cross-platform paths"""
        raw_path = self.config["settings"]["target_base_directory"]
        return Path(raw_path).expanduser().resolve()

    def organize(self, source_directory: str):
        """Main function to scan and organize files in the source directory"""
        source_path = Path(source_directory).resolve()
        if not source_path.exists() or not source_path.is_dir():
            raise NotADirectoryError(f"Provided source path is invalid: {source_path}")

        base_target = self.get_target_base()

        # Iterate through everything in the source folder
        for item in source_path.iterdir():
            # Skip the target base directory itself if it's nested inside the source
            if base_target in item.parents or item == base_target:
                continue

        if item.is_dir():
            self._handle_directory(item, base_target)
        elif item.is_file():
            self._handle_file(item, source_path, base_target)

    def _handle_directory(self, item: Path, base_target: Path):
        """Handles sub-folders based on the configuration settings"""
        folders_dest_name = self.config["settings"].get(
            "move_folders_into_directory", "Folders"
        )
        dest_folder = base_target / folders_dest_name
        dest_folder.mkdir(parents=True, exist_ok=True)

        target_path = dest_folder / item.name
        self._safe_move(item, target_path)

    def _handle_file(self, item: Path, source_path: Path, base_target: Path):
        """Determines where a file goes based on standard categories or rules"""
        ext = item.suffix.lower()
        moved = False
        category_path = None

        # 1. Check special rules
        special_rules = self.config.get("special_rules", {})
        for rule_name, rule_data in special_rules.items():
            if ext in [e.lower() for e in rule_data["extensions"]]:
                is_large = item.stat().st_size > rule_data["large_size_threshold_bytes"]
                has_subtitle = any(
                    (source_path / f"{item.stem}{sub_ext}").exists()
                    for sub_ext in rule_data["subtitle_extensions"]
                )

                category_path = (
                    rule_data["primary_path"]
                    if (is_large or has_subtitle)
                    else rule_data["fallback_path"]
                )
                moved = True
                break

        # 2. Check Standard Categories if not caught by special rules
        if not moved:
            standard_cats = self.config.get("standard_categories", {})
            for cat_name, cat_data in standard_cats.items():
                if ext in [e.lower() for e in cat_data["extensions"]]:
                    category_path = cat_data["path"]
                    moved = True
                    break

        # 3. Handle Undefined Extensions
        settings = self.config.get("settings", {})
        if not moved:
            if settings.get("handle_undefined", True):
                category_path = settings.get("undefined_path", "Others")
                moved = True
            else:
                return  # Skip moving if undefined files shouldn't be handled

        # 4. Resolve Final Destination (incorporating group_by_extension if enabled)
        dest_folder = base_target / category_path

        if settings.get("group_by_extension", False) and ext:
            # Creates a subfolder like Pictures/JPG or Pictures/png
            ext_folder_name = ext.lstrip(".").upper()
            dest_folder = dest_folder / ext_folder_name

        dest_folder.mkdir(parents=True, exist_ok=True)
        target_path = dest_folder / item.name
        self._safe_move(item, target_path)

    def _apply_special_rule(
        self, item: Path, source_path: Path, base_target: Path, rule_data: dict
    ) -> bool:
        """Applies custom logic like Video/Movie size and subtitle check"""
        size_threshold = rule_data["large_size_threshold_bytes"]
        sub_extensions = [e.lower() for e in rule_data.get("subtitle_extensions", [])]

        # Check size
        is_large = item.stat().st_size > size_threshold

        # Check for external subtitle files in the same directory
        has_subtitle = any(
            (source_path / (item.stem + sub_ext)).exists() for sub_ext in sub_extensions
        )

        # Decision logic
        if is_large or has_subtitle:
            folder_name = rule_data["primary_path"]
        else:
            folder_name = rule_data["fallback_path"]

        dest_folder = base_target / folder_name
        dest_folder.mkdir(parents=True, exist_ok=True)

        target_path = dest_folder / item.name
        self._safe_move(item, target_path)

        return True

    def _safe_move(self, src: Path, dest: Path):
        """Moves a file, handling naming collisions if a file with the same name already exists in the destination"""
        if dest.exists():
            # Handle naming collision
            counter = 1
            while True:
                new_name = (
                    f"{src.stem}_{counter}{src.suffix}"
                    if src.is_file()
                    else f"{src.name}_{counter}"
                )
                new_dest = dest.parent / new_name
                if not new_dest.exists():
                    dest = new_dest
                    break
                counter += 1

        shutil.move(str(src), str(dest))
