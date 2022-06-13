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

_BATCH_SIZE = 100

_DEFAULT_BASE_DIR = BASE_DIR / "gutenberg"
_DEFAULT_MAX_COUNT = 100
_DEFAULT_MAX_LENGTH = 512 * 1024

_DOCUMENT_ID_REGEX = re.compile(r"^(?P<id>\d+)-(8.txt|h.htm)$")

UNKNOWN_LANGUAGE_CODE = "??"

_LANGUAGE_TO_LANGUAGE_CODE_MAP = {
    "": UNKNOWN_LANGUAGE_CODE,
    "Afrikaans": "af",
    "Arabic": "ar",
    "Chinese": "zh",
    "Czech": "cs",
    "Danish": "da",
    "Dutch": "nl",
    "English": "en",
    "Esperanto": "eo",
    "Finnish": "fi",
    "French": "fr",
    "Galician": "gl",
    "German": "de",
    "Greek": "el",
    "Hungarian": "hu",
    "Italian": "it",
    "Irish": "ga",
    "Latin": "la",
    "Norwegian": "no",
    "Polish": "pl",
    "Portuguese": "pt",
    "Russian": "ru",
    "Slovenian": "sl",
    "Spanish": "es",
    "Swedish": "sv",
    "Tagalog": "tl",
}

_BROKEN_ENCODING_TO_ENCODING_MAP = {
    "": "cp1252",
    "cp-1250": "cp1250",
    "cp-1251": "cp1251",
    "cp-1252": "cp1252",
    "iso latin-1": "iso-8859-1",
    "iso-latin-1": "iso-8859-1",
    "iso-646-us (us-ascii)": "ascii",
    "iso-859-1": "iso-8859-1",
    "iso-8859": "iso-8859-1",
    "iso 8859-1 (latin-1)": "iso-8859-1",
    "unicode utf-8": "utf-8",
}

_unknown_languages = set()

_log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import local documents from Project Gutenberg into database"

    _id_to_text_path_map: Optional[Dict[int, Path]] = None
    _id_to_html_path_map: Optional[Dict[int, Path]] = None
    _base_dir: Path = _DEFAULT_BASE_DIR
    _max_count: int = _DEFAULT_MAX_COUNT
    _max_length: int = _DEFAULT_MAX_LENGTH

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-dir",
            "-b",
            default=_DEFAULT_BASE_DIR,
            type=Path,
            help="directory to scan for Gutenberg documents; default: %(default)s",
        )
        parser.add_argument(
            "--max-count",
            "-c",
            default=_DEFAULT_MAX_COUNT,
            type=int,
            help="maximum number of documents to import; default: %(default)d",
        )
        parser.add_argument(
            "--max-length",
            "-l",
            default=_DEFAULT_MAX_LENGTH,
            type=int,
            help="maximum length of documents to import; default: %(default)d",
        )

    def handle(self, *args, **options):
        self._base_dir: Path = options["base_dir"]
        self._max_count: int = options["max_count"]
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
        document_ids_to_add = sorted(self._id_to_text_path_map.keys() & self._id_to_html_path_map.keys())[
            : self._max_count
        ]
        documents_to_add = []
        Document.objects.all().delete()
        for document_id in tracked_progress(document_ids_to_add, description="  Importing documents"):
            try:
                text_path = self._id_to_text_path_map[document_id]
                text = _file_contents(text_path)
                text_length = len(text)
                if text_length <= _DEFAULT_MAX_LENGTH:
                    html_path = self._id_to_html_path_map[document_id]
                    html = _file_contents(html_path)
                    if html is not None:
                        title, authors, language = _title_authors_language_from(text)
                        language_code = _language_code(language)
                        documents_to_add.append(
                            Document(
                                id=document_id,
                                authors=authors,
                                html=html,
                                language_code=language_code,
                                text=text,
                                title=title,
                            )
                        )
                else:
                    # TODO: _log.warning('Skipping too long file: "%s" (%.2f MB)', text_path, text_length / 1024 / 1024)
                    pass
            except CommandError as error:
                self.stdout.write(f"Warning: {error}")
            if len(documents_to_add) >= _BATCH_SIZE:
                Document.objects.bulk_create(documents_to_add)
                documents_to_add.clear()
        Document.objects.bulk_create(documents_to_add)


def _intro_lines(text: str) -> List[str]:
    return text[:MAX_INTRO_LENGTH].split("\n")[:MAX_INTRO_LINES]


def _title_authors_language_from(text: str) -> Tuple[str, str, str]:
    title = ""
    authors = ""
    language = ""
    lines = _intro_lines(text)
    line_count = len(lines)
    line_index = 0
    while line_index < line_count and (not title or not authors or not language):
        line = lines[line_index]
        if line.startswith("Author:"):
            authors = _text_after_colon(line)
        elif line.startswith("Language:"):
            language = _text_after_colon(line)
        elif line.startswith("Title:"):
            title = _text_after_colon(line)
        line_index += 1
    return title, authors, language


def _language_code(language: str) -> str:
    result = _LANGUAGE_TO_LANGUAGE_CODE_MAP.get(language) if len(language) != 2 else language.lower()
    if result is None:
        result = UNKNOWN_LANGUAGE_CODE
        if language not in _unknown_languages:
            _unknown_languages.add(language)
            _log.warning('Unknown language "%s" should be added to _LANGUAGE_TO_LANGUAGE_CODE_MAP', language)
    return result


def _text_after_colon(line: str) -> str:
    return line.split(":", 1)[1].split("<", 1)[0].strip()


def _file_contents(path: Path, encoding: str = None) -> str:
    try:
        if encoding is None:
            actual_encoding = DEFAULT_ENCODING
            result = _file_contents(path, actual_encoding)
            lines = _intro_lines(result)
            encoding_line = next((line for line in lines if line.startswith("Character set encoding:")), None)
            if encoding_line is not None:
                actual_encoding = _text_after_colon(encoding_line).lower()
                actual_encoding = _BROKEN_ENCODING_TO_ENCODING_MAP.get(actual_encoding, actual_encoding)
                if actual_encoding.lower() != DEFAULT_ENCODING:
                    result = None
        else:
            actual_encoding = encoding
            result = None
        if result is None:
            with open(path, encoding=actual_encoding, errors="backslashreplace") as file:
                result = file.read()
    except Exception as error:
        raise CommandError(f'Cannot process "{path}": {error}')
    return result
