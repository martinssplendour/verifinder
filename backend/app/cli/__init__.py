from __future__ import annotations

from .areas import ingest_postcode_file
from .food import ingest_food_file
from .properties import ingest_property_files
from .qualifications import (
    ingest_qualification_files,
    ingest_qualification_unit_files,
    ingest_welsh_qualification_file,
)
from .schools import ingest_ofsted_file, ingest_school_file
from .sponsors import ingest_sponsor_file
from .study import ingest_study_provider_files

__all__ = [
    "ingest_food_file",
    "ingest_ofsted_file",
    "ingest_postcode_file",
    "ingest_property_files",
    "ingest_qualification_files",
    "ingest_qualification_unit_files",
    "ingest_school_file",
    "ingest_sponsor_file",
    "ingest_study_provider_files",
    "ingest_welsh_qualification_file",
]
