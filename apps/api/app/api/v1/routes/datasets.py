from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.security.file_security import FileSecurityError, validate_uploaded_file
from app.data_processing.profiling.dataset_profiler import profile_dataframe
from app.data_processing.readers import DatasetReadError, read_dataset
from app.infrastructure.storage.local_storage import LocalStorageError, save_upload_to_quarantine

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...)) -> dict:
    """Recebe, valida, salva e analisa um dataset."""

    try:
        metadata = await validate_uploaded_file(file)
        stored_path = await save_upload_to_quarantine(file, metadata["filename"])

        dataframe = read_dataset(
            path=stored_path,
            extension=metadata["extension"],
        )

        profile = profile_dataframe(dataframe)

    except FileSecurityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except DatasetReadError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except LocalStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return {
        "message": "Dataset recebido, validado e analisado com sucesso.",
        "file": metadata,
        "profile": profile,
    }