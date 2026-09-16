import json
import shutil
from pathlib import Path

from src.utils import check_if_installer


class FolderOrganizer:
    def __init__(self, config_path=None):
        if config_path is None:
            config_path = self._default_config_path()
        else:
            config_path = self._resolve_config_path(config_path)
        self.config_path = Path(config_path).expanduser()
        self.load_config()

    @staticmethod
    def _default_config_path() -> Path:
        project_root = Path(__file__).resolve().parents[1]
        return project_root / "config.json"

    @staticmethod
    def _resolve_config_path(config_path):
        path = Path(config_path).expanduser()
        if not path.is_absolute():
            project_root = Path(__file__).resolve().parents[1]
            path = project_root / path
        return path

    def load_config(self):
        """Loads or reloads the configuration from the JSON file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as config_file:
            self.config = json.load(config_file)

    def get_target_base(self) -> Path:
        """Resolves the target base directory, supporting cross-platform paths."""
        raw_path = self.config["settings"]["target_base_directory"]
        return Path(raw_path).expanduser().resolve()

    def organize(self, source_directory: str):
        """Main function to scan and organize files in the source directory."""
        source_path = Path(source_directory).resolve()
        if not source_path.exists() or not source_path.is_dir():
            raise NotADirectoryError(f"Provided source path is invalid: {source_path}")

        settings = self.config.get("settings", {})
        base_target = (
            source_path if settings.get("organize_in_place", False) else self.get_target_base()
        )
        known_folders = self._build_known_folders(settings)

        for item in list(source_path.iterdir()):
            if self._should_skip_item(item, settings, base_target, known_folders):
                continue

            if item.is_dir():
                self._handle_directory(item, base_target)
            elif item.is_file():
                self._handle_file(item, source_path, base_target)

    def _build_known_folders(self, settings):
        known_folders = {
            data["path"] for data in self.config.get("standard_categories", {}).values()
        }
        known_folders.add(settings.get("move_folders_into_directory", "Folders"))
        known_folders.add(settings.get("undefined_path", "Others"))

        for rule in self.config.get("special_rules", {}).values():
            known_folders.add(rule["primary_path"])
            known_folders.add(rule["fallback_path"])

        return known_folders

    def _should_skip_item(self, item, settings, base_target, known_folders):
        if not item.exists():
            return True

        if settings.get("organize_in_place", False):
            if item.is_dir() and item.name in known_folders:
                return True

        if not settings.get("organize_in_place", False) and (
            base_target in item.parents or item == base_target
        ):
            return True

        return False

    def _handle_directory(self, item: Path, base_target: Path):
        """Handles sub-folders based on the configuration settings."""
        folders_dest_name = self.config["settings"].get(
            "move_folders_into_directory", "Folders"
        )
        dest_folder = base_target / folders_dest_name
        dest_folder.mkdir(parents=True, exist_ok=True)

        target_path = dest_folder / item.name
        self._safe_move(item, target_path)

    def _handle_file(self, item: Path, source_path: Path, base_target: Path):
        """Determines where a file goes based on standard categories or rules."""
        ext = item.suffix.lower()
        category_path, matching_sub = self._resolve_category_path(item, source_path, ext)

        settings = self.config.get("settings", {})
        dest_folder = base_target / category_path

        if settings.get("group_by_extension", False) and ext:
            ext_folder_name = ext.lstrip(".").upper()
            dest_folder = dest_folder / ext_folder_name

        dest_folder.mkdir(parents=True, exist_ok=True)

        target_path = dest_folder / item.name
        self._safe_move(item, target_path)

        if matching_sub and matching_sub.exists():
            sub_target_path = dest_folder / matching_sub.name
            self._safe_move(matching_sub, sub_target_path)

    def _resolve_category_path(self, item: Path, source_path: Path, ext: str):
        special_rules = self.config.get("special_rules", {})
        for rule_data in special_rules.values():
            if ext not in [e.lower() for e in rule_data["extensions"]]:
                continue

            keyword = rule_data.get("name_keyword", [])
            has_keyword = keyword and (
                any(kw.lower() in item.name.lower() for kw in keyword)
                or check_if_installer(item, keyword)
            )

            size_threshold = rule_data.get("large_size_threshold_bytes", 0)
            is_large = size_threshold > 0 and item.stat().st_size > size_threshold

            matching_sub = None
            if "subtitle_extensions" in rule_data:
                sub_extensions = [e.lower() for e in rule_data["subtitle_extensions"]]
                for sub_ext in sub_extensions:
                    potential_sub = source_path / f"{item.stem}{sub_ext}"
                    if potential_sub.exists():
                        matching_sub = potential_sub
                        break

            has_subtitle = matching_sub is not None
            category_path = (
                rule_data["primary_path"]
                if has_keyword or is_large or has_subtitle
                else rule_data["fallback_path"]
            )
            return category_path, matching_sub

        standard_cats = self.config.get("standard_categories", {})
        for cat_data in standard_cats.values():
            if ext in [e.lower() for e in cat_data["extensions"]]:
                return cat_data["path"], None

        settings = self.config.get("settings", {})
        if settings.get("handle_undefined", True):
            return settings.get("undefined_path", "Others"), None

        return None, None

    def _apply_special_rule(
        self, item: Path, source_path: Path, base_target: Path, rule_data: dict
    ) -> bool:
        """Applies custom logic like video/movie sizing and subtitle detection."""
        size_threshold = rule_data["large_size_threshold_bytes"]
        sub_extensions = [e.lower() for e in rule_data["subtitle_extensions"]]

        is_large = item.stat().st_size > size_threshold

        matching_sub = None
        for sub_ext in sub_extensions:
            potential_sub = source_path / f"{item.stem}{sub_ext}"
            if potential_sub.exists():
                matching_sub = potential_sub
                break
        has_subtitle = matching_sub is not None

        folder_name = (
            rule_data["primary_path"]
            if is_large or has_subtitle
            else rule_data["fallback_path"]
        )

        dest_folder = base_target / folder_name
        dest_folder.mkdir(parents=True, exist_ok=True)

        target_path = dest_folder / item.name
        self._safe_move(item, target_path)

        if matching_sub:
            sub_target_path = dest_folder / matching_sub.name
            self._safe_move(matching_sub, sub_target_path)

        return True

    def _safe_move(self, src: Path, dest: Path):
        """Moves a file, handling naming collisions if a file with the same name already exists in the destination."""
        if dest.exists():
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
        matching_sub = None

        # 1. Check special rules
        special_rules = self.config.get("special_rules", {})
        for rule_name, rule_data in special_rules.items():
            if ext in [e.lower() for e in rule_data["extensions"]]:

                # Check custom name keyword (e.g., "install")
                keyword = rule_data.get("name_keyword", [])
                has_keyword = keyword and (
                    any(kw.lower() in item.name.lower() for kw in keyword)
                    or check_if_installer(item, keyword)
                )

                # Check size threshold
                size_threshold = rule_data.get("large_size_threshold_bytes", 0)
                is_large = size_threshold > 0 and item.stat().st_size > size_threshold

                # Check subtitle (if rule specifies it, like movies)
                has_subtitle = False
                if "subtitle_extensions" in rule_data:
                    sub_extensions = [
                        e.lower() for e in rule_data["subtitle_extensions"]
                    ]
                    for sub_ext in sub_extensions:
                        potential_sub = source_path / f"{item.stem}{sub_ext}"
                        if potential_sub.exists():
                            matching_sub = potential_sub
                            break
                    has_subtitle = matching_sub is not None

                # Decision logic: if any trigger condition matches, use primary path, else fallback
                if has_keyword or is_large or has_subtitle:
                    category_path = rule_data["primary_path"]
                else:
                    category_path = rule_data["fallback_path"]

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
                return

        # 4. Resolve Final Destination
        dest_folder = base_target / category_path

        if settings.get("group_by_extension", False) and ext:
            ext_folder_name = ext.lstrip(".").upper()
            dest_folder = dest_folder / ext_folder_name

        dest_folder.mkdir(parents=True, exist_ok=True)

        target_path = dest_folder / item.name
        self._safe_move(item, target_path)

        if matching_sub and matching_sub.exists():
            sub_target_path = dest_folder / matching_sub.name
            self._safe_move(matching_sub, sub_target_path)

    def _apply_special_rule(
        self, item: Path, source_path: Path, base_target: Path, rule_data: dict
    ) -> bool:
        """Applies custom logic like Video/Movie size and subtitle check"""
        size_threshold = rule_data["large_size_threshold_bytes"]
        sub_extensions = [e.lower() for e in rule_data["subtitle_extensions"]]

        # Check size
        is_large = item.stat().st_size > size_threshold

        # Look for a matching subtitle file in the source directory
        matching_sub = None
        for sub_ext in sub_extensions:
            potential_sub = source_path / f"{item.stem}{sub_ext}"
            if potential_sub.exists():
                matching_sub = potential_sub
                break
        has_subtitle = matching_sub is not None

        # Decision logic
        if is_large or has_subtitle:
            folder_name = rule_data["primary_path"]
        else:
            folder_name = rule_data["fallback_path"]

        dest_folder = base_target / folder_name
        dest_folder.mkdir(parents=True, exist_ok=True)

        target_path = dest_folder / item.name
        self._safe_move(item, target_path)

        if matching_sub:
            sub_target_path = dest_folder / matching_sub.name
            self._safe_move(matching_sub, sub_target_path)

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
