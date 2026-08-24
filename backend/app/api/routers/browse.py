from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_read_db
from app.schemas import BrowseCatalogue, BrowseDataset, BrowseResponse
from app.services.browse import (
    BROWSABLE,
    COUNTRIES,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    attribution,
    browse_records,
    latest_context,
    list_places,
)


router = APIRouter()


def _dataset(dataset_id: str):
    dataset = BROWSABLE.get(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="That register is not available to browse.")
    return dataset


@router.get("/browse", response_model=BrowseCatalogue)
def browse_catalogue(session: Session = Depends(get_read_db)):
    """The registers that can be browsed, and the countries they cover."""
    datasets = []
    for dataset in BROWSABLE.values():
        context = latest_context(session, dataset.source_id)
        datasets.append(
            BrowseDataset(
                id=dataset.id,
                label=dataset.label,
                description=dataset.description,
                organisation=context[0].organisation if context else "",
                place_label=dataset.place_label,
                countries=[country.code for country in COUNTRIES],
                imported=context is not None,
                message=None if context else "This register has not been imported yet.",
            )
        )
    return BrowseCatalogue(countries=COUNTRIES, datasets=datasets)


@router.get("/browse/{dataset_id}/places", response_model=list[str])
def browse_places(dataset_id: str, session: Session = Depends(get_read_db)):
    """Every place this register holds, for the filter."""
    return list_places(session, _dataset(dataset_id))


@router.get("/browse/{dataset_id}", response_model=BrowseResponse)
def browse_dataset(
    dataset_id: str,
    country: str | None = Query(default=None, max_length=8),
    place: str | None = Query(default=None, max_length=180),
    page: int = Query(default=1, ge=1, le=2000),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    session: Session = Depends(get_read_db),
):
    dataset = _dataset(dataset_id)
    if country and country.upper() not in {option.code for option in COUNTRIES}:
        raise HTTPException(status_code=404, detail="VeriFinder does not hold records for that country yet.")
    records, total, context = browse_records(
        session, dataset, place=place, page=page, page_size=page_size
    )
    return BrowseResponse(
        dataset=dataset.id,
        country=(country or "").upper() or None,
        place=place if dataset.place_column is not None else None,
        page=page,
        page_size=page_size,
        total=total,
        records=records,
        dataset_version=context[1].version_identifier if context else None,
        source=attribution(context) if context else None,
        message=None if context else f"{dataset.label} has not been imported yet.",
    )
