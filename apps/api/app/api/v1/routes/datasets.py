from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.security.file_security import FileSecurityError, validate_uploaded_file
from app.data_processing.profiling.dataset_profiler import profile_dataframe
from app.data_processing.readers import DatasetReadError, read_dataset
from app.infrastructure.storage.analysis_storage import (
    AnalysisStorageError,
    get_dataset_analysis,
    list_dataset_analyses,
    save_dataset_analysis,
)
from app.infrastructure.storage.local_storage import LocalStorageError, save_upload_to_quarantine

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...)) -> dict:
    """Recebe, valida, salva, analisa e persiste um dataset."""

    try:
        metadata = await validate_uploaded_file(file)
        stored_path = await save_upload_to_quarantine(file, metadata["filename"])

        dataframe = read_dataset(
            path=stored_path,
            extension=metadata["extension"],
        )

        profile = profile_dataframe(dataframe)

        analysis = save_dataset_analysis(
            original_filename=metadata["filename"],
            stored_path=stored_path,
            metadata=metadata,
            profile=profile,
        )

    except FileSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

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

    except AnalysisStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return {
        "message": "Dataset recebido, validado, analisado e salvo com sucesso.",
        "dataset": analysis,
    }


@router.get("")
def list_datasets() -> dict:
    """Lista datasets analisados."""

    return {
        "datasets": list_dataset_analyses(),
    }


@router.get("/{dataset_id}")
def get_dataset(dataset_id: str) -> dict:
    """Busca um dataset analisado pelo ID."""

    dataset = get_dataset_analysis(dataset_id)

    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset não encontrado.",
        )

    return {
        "dataset": dataset,
    }