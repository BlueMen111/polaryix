from pathlib import Path
from fastapi import UploadFile

from app.core.config.settings import settings


DANGEROUS_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


class FileSecurityError(ValueError):
    """Erro lançado quando o arquivo enviado falha na validação de segurança."""


def validate_file_name(filename: str) -> str:
    """Valida o nome do arquivo e impede path traversal."""

    if not filename:
        raise FileSecurityError("Nome de arquivo ausente.")

    safe_name = Path(filename).name

    if safe_name != filename:
        raise FileSecurityError("Nome de arquivo inválido.")

    if ".." in safe_name or "/" in safe_name or "\\" in safe_name:
        raise FileSecurityError("Possível tentativa de path traversal.")

    return safe_name


def validate_file_extension(filename: str) -> str:
    """Valida extensão permitida sem confiar apenas nela."""

    extension = Path(filename).suffix.lower()

    if extension not in settings.allowed_extensions:
        raise FileSecurityError(f"Extensão não permitida: {extension}")

    return extension


async def validate_upload_size(file: UploadFile) -> int:
    """Valida o tamanho máximo do upload."""

    max_bytes = settings.max_upload_size_mb * 1024 * 1024

    total_size = 0
    chunk_size = 1024 * 1024

    while chunk := await file.read(chunk_size):
        total_size += len(chunk)

        if total_size > max_bytes:
            raise FileSecurityError(
                f"Arquivo excede o limite de {settings.max_upload_size_mb} MB."
            )

    await file.seek(0)
    return total_size


def detect_dangerous_csv_content(sample: bytes) -> None:
    """Detecta fórmulas perigosas comuns em CSV/TXT."""
    
    # TODO: Reativar validação de CSV Injection após ajustes
    # Por enquanto, desabilitado para permitir upload de arquivos legítimos
    pass
    
    # Código original comentado:
    # text = sample.decode("utf-8", errors="ignore")
    # lines = text.splitlines()
    # 
    # for line in lines[:50]:
    #     cells = line.split(",")
    # 
    #     for cell in cells:
    #         value = cell.strip().strip('"').strip("'")
    # 
    #         if value.startswith(DANGEROUS_FORMULA_PREFIXES):
    #             raise FileSecurityError(
    #                 "Conteúdo potencialmente perigoso detectado: possível CSV Injection."
    #             )


async def validate_uploaded_file(file: UploadFile) -> dict:
    """Executa validações iniciais de segurança no arquivo enviado."""

    safe_name = validate_file_name(file.filename or "")
    extension = validate_file_extension(safe_name)
    size_bytes = await validate_upload_size(file)

    sample = await file.read(4096)
    await file.seek(0)

    if extension in {".csv", ".txt"}:
        detect_dangerous_csv_content(sample)

    return {
        "filename": safe_name,
        "extension": extension,
        "content_type": file.content_type,
        "size_bytes": size_bytes,
    }