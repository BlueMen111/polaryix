from __future__ import annotations

import tempfile
import unittest
from io import BytesIO
from pathlib import Path

import pandas as pd
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from app.api.v1.routes.converter import _convert_stored_file, _save_upload
from app.core.conversion.compatibility import REGISTERED_FORMATS, build_compatibility_matrix, validate_conversion
from app.core.security.file_security import FileSecurityError


class ConversionCompatibilityTests(unittest.TestCase):
    def test_registered_formats_include_current_frontend_options(self) -> None:
        expected = {
            "PNG",
            "DDS",
            "JPG",
            "JPEG",
            "WEBP",
            "TGA",
            "BMP",
            "TIFF",
            "AVIF",
            "SVG",
            "ICO",
            "MP4",
            "MOV",
            "AVI",
            "MKV",
            "WEBM",
            "M4V",
            "FLV",
            "WMV",
            "MP3",
            "WAV",
            "AAC",
            "OGG",
            "FLAC",
            "M4A",
            "WMA",
            "PDF",
            "DOCX",
            "DOC",
            "XLSX",
            "CSV",
            "PPTX",
            "TXT",
            "MD",
            "ZIP",
            "RAR",
            "7Z",
            "TAR",
            "GZ",
            "JSON",
            "XML",
            "HTML",
            "HEIC",
            "PSD",
        }

        self.assertTrue(expected.issubset(REGISTERED_FORMATS))

    def test_allowed_combinations(self) -> None:
        for source, target in [
            ("PNG", "JPG"),
            ("PNG", "WEBP"),
            ("MP3", "WAV"),
            ("MP4", "MP3"),
            ("MP4", "WEBM"),
            ("CSV", "XLSX"),
            ("CSV", "JSON"),
            ("JSON", "HTML"),
            ("TXT", "MD"),
            ("PNG", "ZIP"),
        ]:
            with self.subTest(source=source, target=target):
                result = validate_conversion(source, target)
                self.assertTrue(result.allowed, result.message)

    def test_blocked_or_unsupported_combinations(self) -> None:
        for source, target in [
            ("PNG", "MP3"),
            ("PNG", "MP4"),
            ("JPG", "MP3"),
            ("TXT", "MP4"),
            ("MP3", "PNG"),
            ("DOCX", "PDF"),
            ("PDF", "PNG"),
            ("TXT", "PDF"),
        ]:
            with self.subTest(source=source, target=target):
                result = validate_conversion(source, target)
                self.assertFalse(result.allowed)
                self.assertIn("conversão", result.message.lower())

    def test_matrix_contains_every_registered_pair(self) -> None:
        matrix = build_compatibility_matrix()

        self.assertEqual(set(matrix), REGISTERED_FORMATS)
        for source, targets in matrix.items():
            self.assertEqual(set(targets), REGISTERED_FORMATS, source)

    def test_invalid_format_is_rejected(self) -> None:
        result = validate_conversion("EXE", "PNG")

        self.assertFalse(result.allowed)
        self.assertIn("não suportado", result.message)

    def test_missing_target_format_is_rejected(self) -> None:
        result = validate_conversion("PNG", "")

        self.assertFalse(result.allowed)
        self.assertIn("saída", result.message)


class ConverterFileValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_upload_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            upload = UploadFile(file=BytesIO(b""), filename="empty.csv")

            with self.assertRaises(FileSecurityError) as context:
                await _save_upload(upload, Path(temp_dir) / "empty.csv", "CSV")

            self.assertIn("vazio", str(context.exception))

    async def test_extension_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            upload = UploadFile(file=BytesIO(b"a,b\n1,2\n"), filename="table.txt")

            with self.assertRaises(FileSecurityError) as context:
                await _save_upload(upload, Path(temp_dir) / "table.csv", "CSV")

            self.assertIn("extensão", str(context.exception).lower())

    def test_csv_to_xlsx_conversion_generates_valid_workbook(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workdir = Path(temp_dir)
            source = workdir / "input.csv"
            source.write_text("nome,valor\nPolaryix,10\nTeste,20\n", encoding="utf-8")

            output_path, output_name = _convert_stored_file(source, "input.csv", "CSV", "XLSX", workdir)

            self.assertEqual(output_name, "input-polaryix.xlsx")
            self.assertTrue(output_path.exists())
            self.assertEqual(pd.read_excel(output_path).to_dict(orient="records")[0]["nome"], "Polaryix")

    def test_invalid_combination_never_reaches_processing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workdir = Path(temp_dir)
            source = workdir / "input.png"
            source.write_bytes(b"not-a-real-image")

            with self.assertRaises(HTTPException) as context:
                _convert_stored_file(source, "input.png", "PNG", "MP3", workdir)

            self.assertEqual(context.exception.status_code, 422)
            self.assertIn("não é possível", context.exception.detail)

    def test_corrupted_image_upload_returns_readable_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workdir = Path(temp_dir)
            source = workdir / "broken.png"
            source.write_bytes(b"not-a-real-image")

            with self.assertRaises(HTTPException) as context:
                _convert_stored_file(source, "broken.png", "PNG", "JPG", workdir)

            self.assertEqual(context.exception.status_code, 422)
            self.assertIn("imagem", context.exception.detail.lower())


if __name__ == "__main__":
    unittest.main()
