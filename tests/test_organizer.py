from pathlib import Path
from unittest.mock import patch

from src.core import FolderOrganizer

def test_comprehensive_folder_organization(tmp_path):
    # 1. Setup a fake messy source folder
    source_dir = tmp_path / "downloads_mock"
    source_dir.mkdir()

    # Create various mock files
    (source_dir / "document.pdf").write_text("pdf content")
    (source_dir / "photo.jpg").write_text("jpg content")
    (source_dir / "funny.gif").write_text("gif content")
    (source_dir / "executable.exe").write_text("exe content")
    (source_dir / "installer.exe").write_text("exe content")
    (source_dir / "setup.msi").write_text("msi content")
    (source_dir / "archive.zip").write_text("zip content")

    # Special rule: Small video (should go to Videos)
    small_video = source_dir / "short_clip.mp4"
    small_video.write_text("small video")

    # Special rule: Large video OR video with subtitle (should go to Movies)
    # Let's make a video with a matching subtitle file
    movie_file = source_dir / "epic_movie.mkv"
    movie_file.write_text("movie bytes")
    subtitle_file = source_dir / "epic_movie.srt"
    subtitle_file.write_text("subtitle text")

    # Undefined file type
    unknown_file = source_dir / "data.xyz"
    unknown_file.write_text("unknown bytes")

    # 2. Initialize Organizer and set target to source for in-place testing
    organizer = FolderOrganizer()
    organizer.config["settings"]["organize_in_place"] = True
    organizer.config["settings"]["handle_undefined"] = True

    # 3. Run the organization
    organizer.organize(str(source_dir))

    # 4. Assert all files landed in their correct respective folders
    assert (source_dir / "Documents" / "document.pdf").exists()
    assert (source_dir / "Pictures" / "photo.jpg").exists()
    assert (source_dir / "Gifs" / "funny.gif").exists()
    assert (source_dir / "Executables" / "executable.exe").exists()
    assert (source_dir / "Installers" / "installer.exe").exists()
    assert (source_dir / "Installers" / "setup.msi").exists()
    assert (source_dir / "Archives" / "archive.zip").exists()

    # Video logic assertions
    assert (source_dir / "Videos" / "short_clip.mp4").exists()
    assert (source_dir / "Movies" / "epic_movie.mkv").exists()
    assert (
        source_dir / "Movies" / "epic_movie.srt"
    ).exists()  # Subtitle should follow or stay grouped depending on rule

    # Undefined logic assertion
    assert (source_dir / "Others" / "data.xyz").exists()


def test_directory_handling(tmp_path):
    # 1. Setup a fake source folder containing a nested sub-directory
    source_dir = tmp_path / "downloads_mock"
    source_dir.mkdir()

    sub_folder = source_dir / "random_folder_to_sort"
    sub_folder.mkdir()
    (sub_folder / "inner_file.txt").write_text("nested content")

    # 2. Initialize Organizer
    organizer = FolderOrganizer()
    organizer.config["settings"]["organize_in_place"] = True

    # 3. Run organization
    organizer.organize(str(source_dir))

    # 4. Assert that the folder was moved into the "Folders" category directory
    expected_folder_path = source_dir / "Folders" / "random_folder_to_sort"
    assert expected_folder_path.exists()
    assert (expected_folder_path / "inner_file.txt").exists()

def test_installer_rule_via_metadata(tmp_path):
    # 1. Setup a fake source folder and a generic .exe file name
    source_dir = tmp_path / "downloads_mock"
    source_dir.mkdir()

    fake_installer = source_dir / "random_file_name.exe"
    fake_installer.write_text("fake binary content")

    # 2. Use patch to mock the imported installer checker used by the organizer
    with patch("src.core.check_if_installer", return_value=True) as mock_check:
        organizer = FolderOrganizer()
        organizer.config["settings"]["organize_in_place"] = True

        # 3. Run the organization
        organizer.organize(str(source_dir))

        # 4. Verify that even though the filename had no keywords,
        # the metadata check routed it to "Installers"
        assert (source_dir / "Installers" / "random_file_name.exe").exists()
        mock_check.assert_called_once()


def test_default_config_path_is_project_relative(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    organizer = FolderOrganizer()

    expected = Path(__file__).resolve().parents[1] / "config.json"
    assert organizer.config_path == expected


def test_default_config_path_uses_executable_directory_when_frozen(monkeypatch, tmp_path):
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    config_file = bundle_dir / "config.json"
    config_file.write_text('{"settings": {"organize_in_place": true}}')

    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("sys.executable", str(bundle_dir / "FolderOrganizer.exe"), raising=False)

    organizer = FolderOrganizer()

    assert organizer.config_path == config_file


def test_managed_folders_can_be_excluded_when_enabled(tmp_path):
    source_dir = tmp_path / "downloads_mock"
    source_dir.mkdir()
    existing_documents = source_dir / "Documents"
    existing_documents.mkdir()
    (source_dir / "report.pdf").write_text("pdf content")

    organizer = FolderOrganizer()
    organizer.config["settings"]["organize_in_place"] = True
    organizer.config["settings"]["exclude_existing_folders"] = True

    organizer.organize(str(source_dir))

    assert (existing_documents / "report.pdf").exists()
    assert not (source_dir / "Folders" / "Documents").exists()
