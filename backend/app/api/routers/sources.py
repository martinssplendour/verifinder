from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_read_db
from app.schemas import SourceRegistryItem
from app.services.area_sources import FLOOD_URL, PLANNING_URL, POLICE_URL
from app.services.epc import OFFICIAL_URL as EPC_OFFICIAL_URL
from app.services.food_loader import OFFICIAL_URL as FOOD_OFFICIAL_URL
from app.services.food_lookup import latest_food_context
from app.services.gias_loader import OFFICIAL_URL as GIAS_OFFICIAL_URL
from app.services.ofsted_loader import OFFICIAL_URL as OFSTED_OFFICIAL_URL
from app.services.school_lookup import latest_ofsted_context, latest_school_context
from app.services.qualification_expansion_loader import QIW_OFFICIAL_URL
from app.services.qualification_loader import OFFICIAL_URL as OFQUAL_OFFICIAL_URL
from app.services.qualification_lookup import (
    latest_qualification_context,
    latest_qualification_unit_context,
    latest_welsh_qualification_context,
)
from app.services.qualification_unit_loader import OFFICIAL_URL as OFQUAL_UNIT_OFFICIAL_URL
from app.services.postcode_loader import OFFICIAL_URL as POSTCODE_OFFICIAL_URL
from app.services.property_loader import OFFICIAL_URL as PROPERTY_OFFICIAL_URL
from app.services.property_lookup import latest_property_context
from app.services.area_lookup import latest_postcode_context
from app.services.sponsor_loader import OFFICIAL_URL
from app.services.sponsor_lookup import latest_sponsor_context
from app.services.study_loader import OFS_OFFICIAL_URL, STUDENT_OFFICIAL_URL
from app.services.study_lookup import latest_ofs_context, latest_student_sponsor_context


router = APIRouter()
settings = get_settings()


@router.get("/sources", response_model=list[SourceRegistryItem])
async def sources(session: Session = Depends(get_read_db)):
    sponsor_context = latest_sponsor_context(session)
    sponsor_source = sponsor_context.source if sponsor_context else None
    qualification_context = latest_qualification_context(session)
    qualification_source = qualification_context[0] if qualification_context else None
    welsh_qualification_context = latest_welsh_qualification_context(session)
    welsh_qualification_source = welsh_qualification_context[0] if welsh_qualification_context else None
    qualification_unit_context = latest_qualification_unit_context(session)
    qualification_unit_source = qualification_unit_context[0] if qualification_unit_context else None
    student_sponsor_context = latest_student_sponsor_context(session)
    student_sponsor_source = student_sponsor_context[0] if student_sponsor_context else None
    ofs_context = latest_ofs_context(session)
    ofs_source = ofs_context[0] if ofs_context else None
    food_context = latest_food_context(session)
    food_source = food_context[0] if food_context else None
    postcode_context = latest_postcode_context(session)
    postcode_source = postcode_context[0] if postcode_context else None
    property_context = latest_property_context(session)
    property_source = property_context[0] if property_context else None
    school_context = latest_school_context(session)
    school_source = school_context[0] if school_context else None
    ofsted_context = latest_ofsted_context(session)
    ofsted_source = ofsted_context[0] if ofsted_context else None
    return [
        SourceRegistryItem(
            id="companies-house",
            organisation="Companies House",
            name="Company profile API",
            official_url="https://developer.company-information.service.gov.uk/",
            source_type="API",
            refresh_frequency="On demand with responsible caching",
            health="healthy" if settings.companies_house_api_key else "unavailable",
            integration_status="configured" if settings.companies_house_api_key else "not_configured",
        ),
        SourceRegistryItem(
            id="epc-register",
            organisation="Ministry of Housing, Communities and Local Government",
            name="Energy Performance Certificate register",
            official_url=EPC_OFFICIAL_URL,
            source_type="API",
            refresh_frequency="On demand with responsible caching",
            health="healthy" if settings.epc_api_key else "unavailable",
            integration_status="configured" if settings.epc_api_key else "not_configured",
        ),
        SourceRegistryItem(
            id="home-office-worker-sponsors",
            organisation=sponsor_source.organisation if sponsor_source else "UK Visas and Immigration",
            name=sponsor_source.name if sponsor_source else "Register of licensed sponsors: workers",
            official_url=sponsor_source.official_url if sponsor_source else OFFICIAL_URL,
            source_type="CSV",
            refresh_frequency="Checked daily",
            health=sponsor_source.health.value if sponsor_source else "unavailable",
            last_successful_retrieval=sponsor_source.last_successful_retrieval if sponsor_source else None,
            integration_status="connected" if sponsor_context else "not_configured",
        ),
        SourceRegistryItem(
            id="ofqual-register",
            organisation=qualification_source.organisation if qualification_source else "Ofqual",
            name=qualification_source.name if qualification_source else "Register of Regulated Qualifications",
            official_url=qualification_source.official_url if qualification_source else OFQUAL_OFFICIAL_URL,
            source_type="CSV",
            refresh_frequency="Checked daily",
            health=qualification_source.health.value if qualification_source else "unavailable",
            last_successful_retrieval=(
                qualification_source.last_successful_retrieval if qualification_source else None
            ),
            integration_status="connected" if qualification_context else "not_configured",
        ),
        SourceRegistryItem(
            id="qualifications-wales-qiw",
            organisation=welsh_qualification_source.organisation if welsh_qualification_source else "Qualifications Wales",
            name=welsh_qualification_source.name if welsh_qualification_source else "Qualifications in Wales complete register",
            official_url=welsh_qualification_source.official_url if welsh_qualification_source else QIW_OFFICIAL_URL,
            source_type="CSV",
            refresh_frequency="Checked weekly",
            health=welsh_qualification_source.health.value if welsh_qualification_source else "unavailable",
            last_successful_retrieval=(
                welsh_qualification_source.last_successful_retrieval if welsh_qualification_source else None
            ),
            integration_status="connected" if welsh_qualification_context else "not_configured",
        ),
        SourceRegistryItem(
            id="ofqual-qualification-units",
            organisation=qualification_unit_source.organisation if qualification_unit_source else "Ofqual",
            name=qualification_unit_source.name if qualification_unit_source else "Qualification units and mappings",
            official_url=(
                qualification_unit_source.official_url if qualification_unit_source else OFQUAL_UNIT_OFFICIAL_URL
            ),
            source_type="CSV",
            refresh_frequency="Checked weekly",
            health=qualification_unit_source.health.value if qualification_unit_source else "unavailable",
            last_successful_retrieval=(
                qualification_unit_source.last_successful_retrieval if qualification_unit_source else None
            ),
            integration_status="connected" if qualification_unit_context else "not_configured",
        ),
        SourceRegistryItem(
            id="home-office-student-sponsors",
            organisation=student_sponsor_source.organisation if student_sponsor_source else "UK Visas and Immigration",
            name=student_sponsor_source.name if student_sponsor_source else "Register of licensed sponsors: students",
            official_url=student_sponsor_source.official_url if student_sponsor_source else STUDENT_OFFICIAL_URL,
            source_type="CSV",
            refresh_frequency="Checked daily",
            health=student_sponsor_source.health.value if student_sponsor_source else "unavailable",
            last_successful_retrieval=(
                student_sponsor_source.last_successful_retrieval if student_sponsor_source else None
            ),
            integration_status="connected" if student_sponsor_context else "not_configured",
        ),
        SourceRegistryItem(
            id="office-for-students-register",
            organisation=ofs_source.organisation if ofs_source else "Office for Students",
            name=ofs_source.name if ofs_source else "Register of English higher education providers",
            official_url=ofs_source.official_url if ofs_source else OFS_OFFICIAL_URL,
            source_type="XLSX",
            refresh_frequency="Checked weekly",
            health=ofs_source.health.value if ofs_source else "unavailable",
            last_successful_retrieval=ofs_source.last_successful_retrieval if ofs_source else None,
            integration_status="connected" if ofs_context else "not_configured",
        ),
        SourceRegistryItem(
            id="fsa-food-hygiene",
            organisation=food_source.organisation if food_source else "Food Standards Agency",
            name=food_source.name if food_source else "Food Hygiene Rating Scheme open data",
            official_url=food_source.official_url if food_source else FOOD_OFFICIAL_URL,
            source_type="CSV",
            refresh_frequency="Checked daily",
            health=food_source.health.value if food_source else "unavailable",
            last_successful_retrieval=food_source.last_successful_retrieval if food_source else None,
            integration_status="connected" if food_context else "not_configured",
        ),
        SourceRegistryItem(
            id="os-code-point-open",
            organisation=postcode_source.organisation if postcode_source else "Ordnance Survey",
            name=postcode_source.name if postcode_source else "Code-Point Open",
            official_url=postcode_source.official_url if postcode_source else POSTCODE_OFFICIAL_URL,
            source_type="ZIP/CSV",
            refresh_frequency="Quarterly",
            health=postcode_source.health.value if postcode_source else "unavailable",
            last_successful_retrieval=postcode_source.last_successful_retrieval if postcode_source else None,
            integration_status="connected" if postcode_context else "not_configured",
        ),
        SourceRegistryItem(
            id="hm-land-registry-price-paid",
            organisation=property_source.organisation if property_source else "HM Land Registry",
            name=property_source.name if property_source else "Price Paid Data (2025–2026 snapshot)",
            official_url=property_source.official_url if property_source else PROPERTY_OFFICIAL_URL,
            source_type="CSV",
            refresh_frequency="Monthly",
            health=property_source.health.value if property_source else "unavailable",
            last_successful_retrieval=property_source.last_successful_retrieval if property_source else None,
            integration_status="connected" if property_context else "not_configured",
        ),
        SourceRegistryItem(
            id="police-uk-street-crime",
            organisation="Home Office",
            name="Police.uk street-level crime API",
            official_url=POLICE_URL,
            source_type="API",
            refresh_frequency="Monthly",
            health="healthy",
            integration_status="configured",
        ),
        SourceRegistryItem(
            id="planning-data",
            organisation="Ministry of Housing, Communities and Local Government",
            name="Planning Data designations",
            official_url=PLANNING_URL,
            source_type="API",
            refresh_frequency="On demand",
            health="healthy",
            integration_status="configured",
        ),
        SourceRegistryItem(
            id="environment-agency-flood-monitoring",
            organisation="Environment Agency",
            name="Real-time flood monitoring",
            official_url=FLOOD_URL,
            source_type="API",
            refresh_frequency="Near real time",
            health="healthy",
            integration_status="configured",
        ),
        SourceRegistryItem(
            id="gias-establishments",
            organisation=school_source.organisation if school_source else "Department for Education",
            name=school_source.name if school_source else "Get Information about Schools (GIAS) establishment register",
            official_url=school_source.official_url if school_source else GIAS_OFFICIAL_URL,
            source_type="CSV",
            refresh_frequency="Checked daily",
            health=school_source.health.value if school_source else "unavailable",
            last_successful_retrieval=school_source.last_successful_retrieval if school_source else None,
            integration_status="connected" if school_context else "not_configured",
        ),
        SourceRegistryItem(
            id="ofsted-school-inspections",
            organisation=ofsted_source.organisation if ofsted_source else "Ofsted",
            name=ofsted_source.name if ofsted_source else "State-funded school inspections and outcomes: management information",
            official_url=ofsted_source.official_url if ofsted_source else OFSTED_OFFICIAL_URL,
            source_type="CSV",
            refresh_frequency="Checked monthly",
            health=ofsted_source.health.value if ofsted_source else "unavailable",
            last_successful_retrieval=ofsted_source.last_successful_retrieval if ofsted_source else None,
            integration_status="connected" if ofsted_context else "not_configured",
        ),
    ]
