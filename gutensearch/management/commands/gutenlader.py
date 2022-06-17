import enum
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from django.core.management.base import BaseCommand, CommandError
from rich.progress import track as tracked_progress

from django_search_example.settings import BASE_DIR
from gutensearch.models import Document

MAX_INTRO_LENGTH = 10000
MAX_INTRO_LINES = 200

DEFAULT_ENCODING = "iso-8859-1"

UNKNOWN_LANGUAGE_CODE = "??"

WARNING_MAPPING_BROKEN_ENCODING = "W100"
WARNING_CANNOT_DETERMINE_ENCODING = "W101"
WARNING_UNKNOWN_PYTHON_ENCODING = "W102"
WARNING_NO_START_MARKER_FOUND = "W200"
WARNING_NO_END_MARKER_FOUND = "W201"
WARNING_NO_ISO_LANGUAGE = "W300"
WARNING_MULTIPLE_LANGUAGES = "W301"
WARNING_UNKNOWN_LANGUAGE = "W302"
WARNING_FILE_TOO_LARGE = "W400"

_BATCH_SIZE = 100

_DEFAULT_BASE_DIR = BASE_DIR / "gutenberg"
_DEFAULT_IGNORE = ",".join(
    [
        WARNING_MAPPING_BROKEN_ENCODING,
        WARNING_CANNOT_DETERMINE_ENCODING,
        WARNING_NO_START_MARKER_FOUND,
        WARNING_NO_END_MARKER_FOUND,
        WARNING_NO_ISO_LANGUAGE,
        WARNING_MULTIPLE_LANGUAGES,
        WARNING_FILE_TOO_LARGE,
    ]
)
_DEFAULT_MAX_COUNT = 100
_DEFAULT_MAX_LENGTH = 512 * 1024

_DOCUMENT_ID_REGEX = re.compile(r"^(?P<id>\d+)-(8.txt|h.htm)$")

_ENCODING_MARKER = "Character set encoding:"
_END_EBOOK_MARKER_REGEX = re.compile(r"^\s*\*+\s*END\s+OF\s+TH(E|IS)\s+PROJECT\s+GUTENBERG\s+EBOOK")
_START_EBOOK_MARKER_REGEX = re.compile(r"^\s*\*+\s*START\s+OF\s+TH(E|IS)\s+PROJECT\s+GUTENBERG\s+EBOOK")

_LANGUAGE_TO_LANGUAGE_CODE_MAP = {
    "": UNKNOWN_LANGUAGE_CODE,
    "Afrikaans": "af",
    "Arabic": "ar",
    "Catalan": "ca",
    "Chinese": "zh",
    "Czech": "cs",
    "Danish": "da",
    "Dutch": "nl",
    "English": "en",
    "Esperanto": "eo",
    "Estonian": "et",
    "Finnish": "fi",
    "French": "fr",
    "Frisian": "fy",
    "Galician": "gl",
    "German": "de",
    "Greek": "el",
    "Hungarian": "hu",
    "Icelandic": "is",
    "Inuktitut": "iu",
    "Italian": "it",
    "Irish": "ga",
    "Japanese": "jp",
    "Latin": "la",
    "Norwegian": "no",
    "Polish": "pl",
    "Portuguese": "pt",
    "Russian": "ru",
    "Serbian": "sr",
    "Slovenian": "sl",
    "Spanish": "es",
    "Swedish": "sv",
    "Tagalog": "tl",
    "Welsh": "cy",
}

# Languages without ISO-639-1 code but for which Gutenberg documents exist.
_NO_ISO_LANGUAGES = {
    "Arapaho",
    "Bagobo",
    "Cebuano",
    "Friulian",
    "Gascon",
    "Iloko",
    "Ilocano",
    "Quiche",
}

_SINGLE_LANGUAGE_REGEX = re.compile(r"^[a-z][a-z\-]+$")

_CP_HYPHEN_REGEX = re.compile("^cp-")

_BROKEN_ENCODING_TO_ENCODING_MAP = {
    "": "cp1252",
    "a": "iso-8859-1",
    "iso latin-1": "iso-8859-1",
    "iso-latin-1": "iso-8859-1",
    "iso-646-us (us-ascii)": "ascii",
    "iso-8559-1": "iso-8859-1",
    "iso-859-1": "iso-8859-1",
    "iso-8858-1": "iso-8859-1",
    "iso-8859": "iso-8859-1",
    "iso 8859-1 (latin-1)": "iso-8859-1",
    "n": "iso-8859-1",
    "unicode utf-8": "utf-8",
}

_unknown_languages = set()

_log = logging.getLogger(__name__)


class _TextScannerState(enum.Enum):
    BEFORE_TEXT = "b"
    IN_TEXT = "t"
    AFTER_TEXT = "a"


class Command(BaseCommand):
    help = "Import local documents from Project Gutenberg into database"

    _id_to_text_path_map: Optional[Dict[int, Path]] = None
    _id_to_html_path_map: Optional[Dict[int, Path]] = None
    _base_dir: Path = _DEFAULT_BASE_DIR
    _max_count: int = _DEFAULT_MAX_COUNT
    _max_length: int = _DEFAULT_MAX_LENGTH
    _warning_codes_to_ignore = None

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-dir",
            "-b",
            default=_DEFAULT_BASE_DIR,
            type=Path,
            help="directory to scan for Gutenberg documents; default: %(default)s",
        )
        parser.add_argument(
            "--ignore",
            "-i",
            default=_DEFAULT_IGNORE,
            metavar="LIST",
            help=(
                "comma separated list of warning codes to ignore; "
                "use empty to enable all warnings; default: %(default)s"
            ),
        )
        parser.add_argument(
            "--max-count",
            "-c",
            default=_DEFAULT_MAX_COUNT,
            metavar="NUMBER",
            type=int,
            help="maximum number of documents to import; use 0 for no limit; default: %(default)d",
        )
        parser.add_argument(
            "--max-length",
            "-l",
            default=_DEFAULT_MAX_LENGTH,
            metavar="NUMBER",
            type=int,
            help=(
                "maximum length of documents (in unicode characters) to import; "
                "use 0 for no limit; default: %(default)d"
            ),
        )

    def handle(self, *args, **options):
        self._base_dir: Path = options["base_dir"]
        self._max_count: int = options["max_count"]
        warning_codes_to_ignore: str = options["ignore"] or ""
        self._warning_codes_to_ignore = [code.strip() for code in warning_codes_to_ignore.split(",")]
        self.stdout.write(f"Scanning {self._base_dir}")

        self._id_to_text_path_map = self._id_to_path_map("[0-9]*-8.txt")
        self._id_to_html_path_map = self._id_to_path_map("[0-9]*-h.htm")
        self._import_documents()
        document_count = Document.objects.count()
        self.stdout.write(self.style.SUCCESS(f"Successfully imported {document_count} documents"))

    def _id_to_path_map(self, name_pattern: str) -> Dict[int, Path]:
        self.stdout.write(f"  Scanning for {name_pattern} document files")
        result = {}
        pattern = "**" + os.sep + name_pattern
        for document_path in self._base_dir.rglob(pattern):
            document_name = document_path.name
            name_match = _DOCUMENT_ID_REGEX.match(document_name)
            if name_match is not None:
                document_id = name_match.group("id")
                result[document_id] = document_path
        self.stdout.write(f"    Found {len(result)} document files")
        return result

    def _import_documents(self):
        document_ids_to_add = sorted(self._id_to_text_path_map.keys() & self._id_to_html_path_map.keys())
        if self._max_count >= 1:
            document_ids_to_add = document_ids_to_add[: self._max_count]
        documents_to_add = []
        Document.objects.all().delete()
        for document_id in tracked_progress(document_ids_to_add, description="  Importing documents"):
            try:
                document_to_add = self._document_from_id(document_id)
                if document_to_add is not None:
                    documents_to_add.append(document_to_add)
            except CommandError as error:
                self.stdout.write(f"Warning: {error}")
            if len(documents_to_add) >= _BATCH_SIZE:
                Document.objects.bulk_create(documents_to_add)
                documents_to_add.clear()
        Document.objects.bulk_create(documents_to_add)

    def _document_from_id(self, document_id: int) -> Optional[Document]:
        result = None
        text_path = self._id_to_text_path_map[document_id]
        full_text = self._full_text_from(text_path)
        full_text_length = len(full_text)
        if full_text_length <= self._max_length or self._max_length <= 0:
            html_path = self._id_to_html_path_map[document_id]
            html = self._full_text_from(html_path)
            if html is not None:
                intro_lines, text_lines = self._intro_and_text_lines(text_path, full_text)
                title, authors, language = _title_authors_language_from(intro_lines)
                language_code = self._language_code(text_path, language)
                text = "\n".join(text_lines).strip(" \n\t")
                result = Document(
                    id=document_id,
                    authors=authors,
                    html=html,
                    language_code=language_code,
                    text=text,
                    title=title,
                )
        else:
            full_text_length_in_mb = full_text_length / 1024 / 1024
            self._log_document_warning(
                text_path, WARNING_FILE_TOO_LARGE, f"Skipping too long file: {full_text_length_in_mb:.2f} MB"
            )
        return result

    def _log_document_warning(self, path: Path, code, message: str):
        if code not in self._warning_codes_to_ignore:
            _log.warning("%s: %s %s", path.name, code, message)

    def _full_text_from(self, path: Path) -> str:
        try:
            with open(path, "rb") as text_file:
                content = text_file.read().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        except Exception as error:
            raise CommandError(f'Cannot process "{path}": {error}')

        actual_encoding = None
        result = content.decode(DEFAULT_ENCODING, errors="replace")
        for line in result.split("\n"):
            if _START_EBOOK_MARKER_REGEX.match(line) is not None or _END_EBOOK_MARKER_REGEX.match(line) is not None:
                break
            if line.startswith(_ENCODING_MARKER):
                actual_encoding = _text_after_colon(line).lower()
                actual_encoding = _CP_HYPHEN_REGEX.sub("cp", actual_encoding)
                mapped_broken_encoding = _BROKEN_ENCODING_TO_ENCODING_MAP.get(actual_encoding)
                if mapped_broken_encoding is not None:
                    self._log_document_warning(
                        path,
                        WARNING_MAPPING_BROKEN_ENCODING,
                        f"Mapping broken encoding {actual_encoding!r} to {mapped_broken_encoding!r}",
                    )
                    actual_encoding = mapped_broken_encoding
                break
        if actual_encoding is None:
            actual_encoding = DEFAULT_ENCODING
            self._log_document_warning(
                path, WARNING_CANNOT_DETERMINE_ENCODING, f"Cannot determine encoding, using default {actual_encoding}"
            )

        if actual_encoding != DEFAULT_ENCODING:
            try:
                result = content.decode(actual_encoding, errors="replace")
            except LookupError:
                self._log_document_warning(
                    path,
                    WARNING_UNKNOWN_PYTHON_ENCODING,
                    f"Cannot find Python encoding for {actual_encoding!r}, using default encoding",
                )

        result = result.strip(" \n\t")
        return result

    def _intro_and_text_lines(self, path: Path, full_text: str) -> Tuple[List[str], List[str]]:
        intro_lines = []
        text_lines = []
        state = _TextScannerState.BEFORE_TEXT
        lines = full_text.split("\n")
        line_count = len(lines)
        line_index = 0
        while line_index < line_count and state != _TextScannerState.AFTER_TEXT:
            line = lines[line_index]
            if state == _TextScannerState.BEFORE_TEXT:
                if _START_EBOOK_MARKER_REGEX.match(line) is not None:
                    state = _TextScannerState.IN_TEXT
                else:
                    intro_lines.append(line)
            elif state == _TextScannerState.IN_TEXT:
                if _END_EBOOK_MARKER_REGEX.match(line) is not None:
                    state = _TextScannerState.AFTER_TEXT
                else:
                    text_lines.append(line)
            line_index += 1

        if state == _TextScannerState.BEFORE_TEXT:
            self._log_document_warning(
                path,
                WARNING_NO_START_MARKER_FOUND,
                "No gutenberg start marker found, document is considered to be empty",
            )
        elif state == _TextScannerState.IN_TEXT:
            self._log_document_warning(
                path,
                WARNING_NO_END_MARKER_FOUND,
                "No gutenberg end marker found, document might include unwanted suffix lines",
            )
        else:
            assert state == _TextScannerState.AFTER_TEXT

        return intro_lines, text_lines

    def _language_code(self, path: Path, language: str) -> str:
        language_lower = language.lower()
        is_single_language = _SINGLE_LANGUAGE_REGEX.match(language_lower) is not None
        result = _LANGUAGE_TO_LANGUAGE_CODE_MAP.get(language) if len(language) != 2 else language_lower
        if result is None:
            cleaned_language = language.title()
            result = _LANGUAGE_TO_LANGUAGE_CODE_MAP.get(cleaned_language)
            if result is None:
                result = UNKNOWN_LANGUAGE_CODE
                if cleaned_language in _NO_ISO_LANGUAGES:
                    self._log_document_warning(
                        path,
                        WARNING_NO_ISO_LANGUAGE,
                        f"Language {language!r} has no ISO-639-1 code, treating as unknown language",
                    )
                elif not is_single_language:
                    self._log_document_warning(
                        path,
                        WARNING_MULTIPLE_LANGUAGES,
                        f"Document is written in multiple languages, treating as unknown language: {language!r}",
                    )
                elif cleaned_language not in _unknown_languages:
                    _unknown_languages.add(cleaned_language)
                    self._log_document_warning(
                        path,
                        WARNING_UNKNOWN_LANGUAGE,
                        f"Unknown language {cleaned_language!r} should be added to _LANGUAGE_TO_LANGUAGE_CODE_MAP "
                        f"or _NO_ISO_LANGUAGES",
                    )
        return result


def _title_authors_language_from(intro_lines: List[str]) -> Tuple[str, str, str]:
    title = ""
    authors = ""
    language = ""
    intro_line_count = len(intro_lines)
    intro_line_index = 0
    while intro_line_index < intro_line_count and (not title or not authors or not language):
        intro_line = intro_lines[intro_line_index]
        if intro_line.startswith("Author:"):
            authors = _text_after_colon(intro_line)
        elif intro_line.startswith("Language:"):
            language = _text_after_colon(intro_line)
        elif intro_line.startswith("Title:"):
            title = _text_after_colon(intro_line)
        intro_line_index += 1
    return title, authors, language


def _text_after_colon(line: str) -> str:
    return line.split(":", 1)[1].split("<", 1)[0].strip()
