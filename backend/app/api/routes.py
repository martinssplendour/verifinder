import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.billing_database import get_billing_db
from app.database import get_read_db
from app.models import ChangeEvent, IngestionRun, RunStatus
from app.schemas import (
    AccountStatusResponse,
    AreaCheckResponse,
    AskRequest,
    AskResponse,
    ChangeItem,
    CheckoutRequest,
    CompanyProfile,
    FoodEstablishmentView,
    FoodSearchResponse,
    Officer,
    OperationCheckView,
    QualificationRecordView,
    QualificationSearchResponse,
    PropertyDetail,
    PropertySearchResponse,
    SchoolDetail,
    SchoolSearchResponse,
    SearchResponse,
    SponsorRecordView,
    SponsorSearchResponse,
    DecisionPlanResponse,
    PlanRequest,
    RedirectResponse,
    ReportAccessResponse,
    SavedReportCreate,
    SavedReportReady,
    SavedReportView,
    SignedDownloadResponse,
    StudyProviderDetail,
    StudyProviderSearchResponse,
    SourceAttribution,
    SourceRegistryItem,
    WatchlistAlertView,
    WatchlistEntryCreate,
    WatchlistEntryUpdate,
    WatchlistEntryView,
)
from app.services.area_lookup import get_area_check, latest_postcode_context
from app.services.area_sources import FLOOD_URL, PLANNING_URL, POLICE_URL
from app.services.companies_house import CompaniesHouseClient, CompaniesHouseError
from app.services.epc import EPCClient
from app.services.epc import OFFICIAL_URL as EPC_OFFICIAL_URL
from app.services.food_loader import OFFICIAL_URL as FOOD_OFFICIAL_URL
from app.services.food_lookup import get_food_establishment, latest_food_context, search_food_establishments
from app.services.gias_loader import OFFICIAL_URL as GIAS_OFFICIAL_URL
from app.services.ofsted_loader import OFFICIAL_URL as OFSTED_OFFICIAL_URL
from app.services.school_lookup import get_school, latest_ofsted_context, latest_school_context, search_schools
from app.services.qualification_expansion_loader import QIW_OFFICIAL_URL
from app.services.qualification_loader import OFFICIAL_URL as OFQUAL_OFFICIAL_URL
from app.services.qualification_lookup import (
    get_qualification,
    latest_qualification_context,
    latest_qualification_unit_context,
    latest_welsh_qualification_context,
    search_qualifications,
)
from app.services.qualification_unit_loader import OFFICIAL_URL as OFQUAL_UNIT_OFFICIAL_URL
from app.services.postcode_loader import OFFICIAL_URL as POSTCODE_OFFICIAL_URL
from app.services.property_loader import OFFICIAL_URL as PROPERTY_OFFICIAL_URL
from app.services.property_lookup import get_property, latest_property_context, search_properties
from app.services.sponsor_loader import OFFICIAL_URL
from app.services.sponsor_lookup import (
    SponsorResolution,
    latest_sponsor_context,
    get_sponsor_record,
    resolve_company_sponsorship,
    search_sponsor_records,
    source_attribution,
)
from app.services.study_loader import OFS_OFFICIAL_URL, STUDENT_OFFICIAL_URL
from app.services.study_lookup import (
    get_study_provider,
    latest_ofs_context,
    latest_student_sponsor_context,
    search_study_providers,
)
from app.services.decision_intelligence import answer_question, build_plan
from app.services.auth import RequestIdentity, identity_dependency, require_authenticated
from app.services.entitlements import (
    check_report_entitlement,
    check_watchlist_entitlement,
    entitlement_snapshot,
    get_or_create_profile,
    reserve_ask,
    reserve_planner,
)
from app.services.watchlists import (
    add_watchlist_entry,
    list_alerts,
    list_watchlist,
    remove_watchlist_entry,
    set_watchlist_notifications,
)
from app.services.reports import (
    ReportStorageError,
    build_plan_pdf,
    delete_pdf,
    list_saved_reports,
    report_storage_configured,
    signed_download_url,
    upload_pdf,
)
from app.services.stripe_billing import (
    BillingConfigurationError,
    billing_configured,
    create_checkout_session,
    create_portal_session,
    process_webhook,
)
from app.billing_models import OperationCheck, Profile, SavedReport, SchedulerLease, SubscriptionTier
from app.services.notifications import email_configured
from app.services.operations import JOB_NAME


router = APIRouter()
settings = get_settings()
COMPANIES_HOUSE_UNAVAILABLE = "Companies House is not connected. Configure COMPANIES_HOUSE_API_KEY to enable legal-company records."


def _entitlement_error(result) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail={
            "code": result.code or "upgrade_required",
            "message": result.message or "Upgrade to continue.",
            "upgrade_required": True,
            "reset_at": result.reset_at.isoformat() if result.reset_at else None,
        },
    )


@router.post("/intelligence/ask", response_model=AskResponse)
async def ask_verifinder(
    request: AskRequest,
    public_session: Session = Depends(get_read_db),
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    if identity.authenticated:
        get_or_create_profile(billing_session, identity.subject_id, identity.email)
    entitlement = reserve_ask(
        billing_session,
        identity.subject_id,
        request.question,
        subject_ids=identity.quota_subject_ids,
        network_hash=identity.network_hash,
    )
    if not entitlement.allowed:
        raise _entitlement_error(entitlement)
    return await answer_question(public_session, request)


@router.post("/plans", response_model=DecisionPlanResponse)
async def create_plan(
    request: PlanRequest,
    public_session: Session = Depends(get_read_db),
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    if identity.authenticated:
        get_or_create_profile(billing_session, identity.subject_id, identity.email)
    entitlement = reserve_planner(
        billing_session,
        identity.subject_id,
        subject_ids=identity.quota_subject_ids,
        network_hash=identity.network_hash,
    )
    if not entitlement.allowed:
        raise _entitlement_error(entitlement)
    return await build_plan(public_session, request)


@router.get("/account/me", response_model=AccountStatusResponse)
async def account_status(
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    if identity.authenticated:
        get_or_create_profile(billing_session, identity.subject_id, identity.email)
    snapshot = entitlement_snapshot(
        billing_session,
        identity.subject_id,
        subject_ids=identity.quota_subject_ids,
        network_hash=identity.network_hash,
    )
    profile = billing_session.get(Profile, identity.subject_id)
    return AccountStatusResponse(
        authenticated=identity.authenticated,
        email=identity.email,
        entitlements=snapshot,
        billing_configured=billing_configured(),
        has_billing_account=bool(profile and profile.stripe_customer_id),
    )


@router.post("/billing/checkout", response_model=RedirectResponse)
async def billing_checkout(
    request: CheckoutRequest,
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    require_authenticated(identity)
    try:
        url = create_checkout_session(
            billing_session,
            identity.subject_id,
            identity.email,
            SubscriptionTier(request.tier),
            request.cadence,
        )
    except BillingConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return RedirectResponse(url=url)


@router.post("/billing/portal", response_model=RedirectResponse)
async def billing_portal(
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    require_authenticated(identity)
    try:
        url = create_portal_session(billing_session, identity.subject_id)
    except BillingConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return RedirectResponse(url=url)


@router.post("/billing/report-access", response_model=ReportAccessResponse)
async def report_access(
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    result = check_report_entitlement(billing_session, identity.subject_id)
    if not result.allowed:
        raise _entitlement_error(result)
    return ReportAccessResponse(allowed=True)


def _saved_report_view(report: SavedReport) -> SavedReportView:
    return SavedReportView(
        id=report.id,
        source_report_id=report.source_report_id,
        report_type=report.report_type,
        title=report.title,
        mime_type=report.mime_type,
        size_bytes=report.size_bytes,
        provenance_count=report.provenance_count,
        created_at=report.created_at,
    )


@router.post("/reports", response_model=SavedReportReady)
async def save_report(
    request: SavedReportCreate,
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    result = check_report_entitlement(billing_session, identity.subject_id)
    if not result.allowed:
        raise _entitlement_error(result)
    if not report_storage_configured():
        raise HTTPException(status_code=503, detail="Private report storage is not configured.")
    existing = billing_session.scalar(
        select(SavedReport).where(
            SavedReport.subject_id == identity.subject_id,
            SavedReport.source_report_id == request.plan.id,
            SavedReport.status == "ready",
        )
    )
    try:
        if existing:
            url, expires_at = await signed_download_url(existing.storage_path)
            return SavedReportReady(report=_saved_report_view(existing), download_url=url, expires_at=expires_at)

        report_id = str(uuid.uuid4())
        storage_path = f"{identity.subject_id}/{datetime.now(timezone.utc):%Y/%m}/{report_id}.pdf"
        pdf = await asyncio.to_thread(build_plan_pdf, request.plan)
        await upload_pdf(storage_path, pdf)
        report = SavedReport(
            id=report_id,
            subject_id=identity.subject_id,
            source_report_id=request.plan.id,
            title=request.plan.title,
            storage_bucket=settings.report_storage_bucket,
            storage_path=storage_path,
            size_bytes=len(pdf),
            provenance_count=sum(1 for item in request.plan.evidence if item.source is not None),
        )
        billing_session.add(report)
        try:
            billing_session.commit()
        except Exception:
            billing_session.rollback()
            await delete_pdf(storage_path)
            raise
        url, expires_at = await signed_download_url(storage_path)
    except ReportStorageError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return SavedReportReady(report=_saved_report_view(report), download_url=url, expires_at=expires_at)


@router.get("/reports", response_model=list[SavedReportView])
async def get_saved_reports(
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    require_authenticated(identity)
    return [_saved_report_view(report) for report in list_saved_reports(billing_session, identity.subject_id)]


@router.post("/reports/{report_id}/download", response_model=SignedDownloadResponse)
async def get_report_download(
    report_id: str,
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    report = billing_session.get(SavedReport, report_id)
    if report is None or report.subject_id != identity.subject_id or report.status != "ready":
        raise HTTPException(status_code=404, detail="Saved report not found.")
    try:
        url, expires_at = await signed_download_url(report.storage_path)
    except ReportStorageError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return SignedDownloadResponse(url=url, expires_at=expires_at)


@router.delete("/reports/{report_id}")
async def remove_saved_report(
    report_id: str,
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    require_authenticated(identity)
    report = billing_session.get(SavedReport, report_id)
    if report is None or report.subject_id != identity.subject_id:
        raise HTTPException(status_code=404, detail="Saved report not found.")
    try:
        await delete_pdf(report.storage_path)
    except ReportStorageError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    billing_session.delete(report)
    billing_session.commit()
    return {"status": "removed"}


@router.post("/billing/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    billing_session: Session = Depends(get_billing_db),
):
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header.")
    payload = await request.body()
    try:
        processed = process_webhook(billing_session, payload, stripe_signature)
    except BillingConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature.") from error
    return {"received": True, "processed": processed}


def companies_house_client() -> CompaniesHouseClient | None:
    return CompaniesHouseClient(settings.companies_house_api_key) if settings.companies_house_api_key else None


def epc_client() -> EPCClient | None:
    return EPCClient(settings.epc_api_key) if settings.epc_api_key else None


async def _company_profile(company_number: str, session: Session) -> tuple[CompanyProfile, SponsorResolution]:
    client = companies_house_client()
    if not client:
        raise HTTPException(status_code=503, detail=COMPANIES_HOUSE_UNAVAILABLE)
    try:
        base_profile = await client.profile(company_number)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Company not found.") from error
    except CompaniesHouseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    resolution = resolve_company_sponsorship(
        session,
        company_name=base_profile.company_name,
        registered_office=base_profile.registered_office,
    )
    return base_profile.model_copy(update={"sponsorship": resolution.summary}), resolution


def _change_item(event: ChangeEvent, source: SourceAttribution) -> ChangeItem:
    payload = event.new_value or event.previous_value or {}
    organisation = payload.get("organisation_name", "Sponsor organisation")
    titles = {
        "sponsor_added": f"{organisation} was added to the sponsor register",
        "sponsor_removed": f"{organisation} was removed from the sponsor register",
        "route_changed": f"Sponsorship routes changed for {organisation}",
        "rating_changed": f"Sponsor rating changed for {organisation}",
        "organisation_changed": f"Sponsor information changed for {organisation}",
    }
    return ChangeItem(
        id=event.id,
        change_type=event.change_type,
        title=titles.get(event.change_type, f"Sponsor information changed for {organisation}"),
        detected_at=event.detected_at,
        source=source,
    )


@router.get("/health")
async def health(
    session: Session = Depends(get_read_db),
    billing_session: Session = Depends(get_billing_db),
) -> dict:
    sponsor_context = latest_sponsor_context(session)
    qualification_context = latest_qualification_context(session)
    welsh_qualification_context = latest_welsh_qualification_context(session)
    qualification_unit_context = latest_qualification_unit_context(session)
    student_sponsor_context = latest_student_sponsor_context(session)
    ofs_context = latest_ofs_context(session)
    food_context = latest_food_context(session)
    postcode_context = latest_postcode_context(session)
    property_context = latest_property_context(session)
    school_context = latest_school_context(session)
    ofsted_context = latest_ofsted_context(session)
    transaction_database = billing_session.get_bind().dialect.name
    return {
        "status": "ok",
        "public_data_store": session.get_bind().dialect.name,
        "transaction_database": transaction_database,
        "companies_house": "configured" if settings.companies_house_api_key else "not_configured",
        "epc": "configured" if settings.epc_api_key else "not_configured",
        "gemini": "configured" if settings.gemini_api_key else "not_configured",
        "supabase_auth": "configured" if settings.supabase_url and settings.supabase_publishable_key else "not_configured",
        "stripe": "configured" if billing_configured() else "not_configured",
        "report_storage": "configured" if report_storage_configured() else "not_configured",
        "email_notifications": "configured" if email_configured() else "not_configured",
        "sponsor_register": "healthy" if sponsor_context else "not_ingested",
        "sponsor_dataset_version": sponsor_context.version.version_identifier if sponsor_context else None,
        "qualifications": "healthy" if qualification_context else "not_ingested",
        "qualification_dataset_version": qualification_context[1].version_identifier if qualification_context else None,
        "welsh_qualifications": "healthy" if welsh_qualification_context else "not_ingested",
        "qualification_units": "healthy" if qualification_unit_context else "not_ingested",
        "student_sponsors": "healthy" if student_sponsor_context else "not_ingested",
        "ofs_register": "healthy" if ofs_context else "not_ingested",
        "food_hygiene": "healthy" if food_context else "not_ingested",
        "food_dataset_version": food_context[1].version_identifier if food_context else None,
        "postcodes": "healthy" if postcode_context else "not_ingested",
        "postcode_dataset_version": postcode_context[1].version_identifier if postcode_context else None,
        "property_sales": "healthy" if property_context else "not_ingested",
        "property_dataset_version": property_context[1].version_identifier if property_context else None,
        "gias_schools": "healthy" if school_context else "not_ingested",
        "gias_dataset_version": school_context[1].version_identifier if school_context else None,
        "ofsted_inspections": "healthy" if ofsted_context else "not_ingested",
        "ofsted_dataset_version": ofsted_context[1].version_identifier if ofsted_context else None,
        "police_uk": "configured",
        "planning_data": "configured",
        "flood_monitoring": "configured",
    }


@router.get("/operations/status")
async def operations_status(billing_session: Session = Depends(get_billing_db)) -> dict:
    recent = list(
        billing_session.scalars(select(OperationCheck).order_by(OperationCheck.checked_at.desc()).limit(100))
    )
    latest: dict[str, OperationCheckView] = {}
    for check in recent:
        if check.check_name not in latest:
            latest[check.check_name] = OperationCheckView(
                check_name=check.check_name,
                status=check.status,
                detail=check.detail,
                checked_at=check.checked_at,
            )
    lease = billing_session.get(SchedulerLease, JOB_NAME)
    locked_until = lease.locked_until if lease else None
    if locked_until and locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    scheduler_stale = bool(
        lease
        and lease.last_status == "running"
        and locked_until
        and locked_until < datetime.now(timezone.utc)
    )
    return {
        "status": "ok" if latest and not scheduler_stale and all(item.status != "failed" for item in latest.values()) else "attention",
        "scheduler": {
            "enabled": settings.scheduler_enabled,
            "interval_minutes": settings.scheduler_interval_minutes,
            "last_started_at": lease.last_started_at if lease else None,
            "last_finished_at": lease.last_finished_at if lease else None,
            "last_status": "stale" if scheduler_stale else (lease.last_status if lease else "not_run"),
            "phase": (lease.last_detail or {}).get("phase") if lease else None,
            "detail": lease.last_detail if lease else None,
        },
        "checks": list(latest.values()),
    }


@router.get("/search", response_model=SearchResponse)
async def search(q: str = Query(min_length=2, max_length=160), limit: int = Query(default=8, ge=1, le=20)):
    client = companies_house_client()
    if not client:
        return SearchResponse(
            query=q,
            results=[],
            total=0,
            data_mode="unavailable",
            message=COMPANIES_HOUSE_UNAVAILABLE,
        )
    try:
        results = await client.search(q, limit)
    except CompaniesHouseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return SearchResponse(query=q, results=results, total=len(results), data_mode="live")


@router.get("/companies/{company_number}", response_model=CompanyProfile)
async def company_profile(company_number: str, session: Session = Depends(get_read_db)):
    profile, _ = await _company_profile(company_number, session)
    return profile


@router.get("/companies/{company_number}/sponsorship")
async def company_sponsorship(company_number: str, session: Session = Depends(get_read_db)):
    profile, _ = await _company_profile(company_number, session)
    return profile.sponsorship


@router.get("/companies/{company_number}/officers", response_model=list[Officer])
async def company_officers(company_number: str):
    client = companies_house_client()
    if not client:
        return []
    try:
        return await client.officers(company_number)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Company not found.") from error
    except CompaniesHouseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/companies/{company_number}/sources", response_model=list[SourceAttribution])
async def company_sources(company_number: str, session: Session = Depends(get_read_db)):
    profile, _ = await _company_profile(company_number, session)
    sources = [profile.company_source]
    if profile.sponsorship.source:
        sources.append(profile.sponsorship.source)
    return sources


@router.get("/sponsors/search", response_model=SponsorSearchResponse)
async def sponsor_search(
    q: str = Query(min_length=2, max_length=160),
    limit: int = Query(default=8, ge=1, le=20),
    session: Session = Depends(get_read_db),
):
    results, context = search_sponsor_records(session, q, limit)
    return SponsorSearchResponse(
        query=q,
        results=results,
        total=len(results),
        dataset_version=context.version.version_identifier if context else None,
        message=None if context else "The sponsor register has not been imported.",
    )


@router.get("/sponsors/{record_id}", response_model=SponsorRecordView)
async def sponsor_detail(record_id: str, session: Session = Depends(get_read_db)):
    record = get_sponsor_record(session, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Sponsor record not found in the latest dataset version.")
    return record


@router.get("/qualifications/search", response_model=QualificationSearchResponse)
async def qualification_search(
    q: str = Query(min_length=2, max_length=200),
    limit: int = Query(default=10, ge=1, le=25),
    session: Session = Depends(get_read_db),
):
    results, context = search_qualifications(session, q, limit)
    contexts = [
        item
        for item in (latest_qualification_context(session), latest_welsh_qualification_context(session))
        if item
    ]
    return QualificationSearchResponse(
        query=q,
        results=results,
        total=len(results),
        dataset_version=" · ".join(item[1].version_identifier for item in contexts) or None,
        message=None if context else "No qualification register has been imported.",
    )


@router.get("/qualifications/{record_id}", response_model=QualificationRecordView)
async def qualification_detail(record_id: str, session: Session = Depends(get_read_db)):
    record = get_qualification(session, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Qualification not found in the latest register snapshot.")
    return record


@router.get("/study/search", response_model=StudyProviderSearchResponse)
async def study_provider_search(
    q: str = Query(min_length=2, max_length=200),
    limit: int = Query(default=10, ge=1, le=25),
    session: Session = Depends(get_read_db),
):
    results, student_context, ofs_context = search_study_providers(session, q, limit)
    return StudyProviderSearchResponse(
        query=q,
        results=results,
        total=len(results),
        message=None if student_context or ofs_context else "No study-provider register has been imported.",
    )


@router.get("/study/{record_type}/{record_id}", response_model=StudyProviderDetail)
async def study_provider_detail(record_type: str, record_id: int, session: Session = Depends(get_read_db)):
    record = get_study_provider(session, record_type, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Study-provider record not found in the latest snapshots.")
    return record


@router.get("/food/search", response_model=FoodSearchResponse)
async def food_search(
    q: str = Query(min_length=2, max_length=200),
    limit: int = Query(default=10, ge=1, le=25),
    session: Session = Depends(get_read_db),
):
    results, context = search_food_establishments(session, q, limit)
    return FoodSearchResponse(
        query=q,
        results=results,
        total=len(results),
        dataset_version=context[1].version_identifier if context else None,
        message=None if context else "The Food Standards Agency ratings dataset has not been imported.",
    )


@router.get("/food/{record_id}", response_model=FoodEstablishmentView)
async def food_detail(record_id: str, session: Session = Depends(get_read_db)):
    record = get_food_establishment(session, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Food establishment not found in the latest ratings snapshot.")
    return record


@router.get("/areas/check", response_model=AreaCheckResponse)
async def area_check(
    postcode: str = Query(min_length=5, max_length=10),
    session: Session = Depends(get_read_db),
):
    result = await get_area_check(session, postcode)
    if result is None:
        if latest_postcode_context(session) is None:
            raise HTTPException(status_code=503, detail="The Code-Point Open postcode dataset has not been imported.")
        raise HTTPException(status_code=404, detail="Postcode not found in the current Great Britain postcode snapshot.")
    return result


@router.get("/properties/search", response_model=PropertySearchResponse)
async def property_search(
    q: str = Query(min_length=2, max_length=240),
    limit: int = Query(default=20, ge=1, le=40),
    session: Session = Depends(get_read_db),
):
    results, context = search_properties(session, q, limit)
    return PropertySearchResponse(
        query=q,
        results=results,
        total=len(results),
        dataset_version=context[1].version_identifier if context else None,
        message=None if context else "The HM Land Registry Price Paid snapshot has not been imported.",
    )


@router.get("/properties/{property_key}", response_model=PropertyDetail)
async def property_detail(property_key: str, session: Session = Depends(get_read_db)):
    result = await get_property(session, property_key, epc_client=epc_client())
    if result is None:
        raise HTTPException(status_code=404, detail="Property not found in the latest imported sales snapshot.")
    return result


@router.get("/schools/search", response_model=SchoolSearchResponse)
async def school_search(
    q: str = Query(min_length=2, max_length=200),
    limit: int = Query(default=10, ge=1, le=25),
    session: Session = Depends(get_read_db),
):
    results, context = search_schools(session, q, limit)
    return SchoolSearchResponse(
        query=q,
        results=results,
        total=len(results),
        dataset_version=context[1].version_identifier if context else None,
        message=None if context else "The GIAS establishment register has not been imported.",
    )


@router.get("/schools/{urn}", response_model=SchoolDetail)
async def school_detail(urn: str, session: Session = Depends(get_read_db)):
    record = get_school(session, urn)
    if record is None:
        raise HTTPException(status_code=404, detail="School not found in the latest imported GIAS snapshot.")
    return record


@router.get("/companies/{company_number}/changes", response_model=list[ChangeItem])
async def company_changes(company_number: str, session: Session = Depends(get_read_db)):
    _, resolution = await _company_profile(company_number, session)
    if not resolution.record or not resolution.context:
        return []
    events = list(
        session.scalars(
            select(ChangeEvent)
            .where(ChangeEvent.source_record_key == resolution.record.source_record_key)
            .order_by(ChangeEvent.detected_at.desc())
            .limit(50)
        )
    )
    attribution = source_attribution(resolution.context)
    return [_change_item(event, attribution) for event in events]


@router.get("/changes", response_model=list[ChangeItem])
async def changes(session: Session = Depends(get_read_db)):
    context = latest_sponsor_context(session)
    if not context:
        return []
    events = list(session.scalars(select(ChangeEvent).order_by(ChangeEvent.detected_at.desc()).limit(100)))
    attribution = source_attribution(context)
    return [_change_item(event, attribution) for event in events]


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


@router.get("/admin/summary")
async def admin_summary(session: Session = Depends(get_read_db)):
    sponsor_context = latest_sponsor_context(session)
    qualification_context = latest_qualification_context(session)
    welsh_qualification_context = latest_welsh_qualification_context(session)
    qualification_unit_context = latest_qualification_unit_context(session)
    student_sponsor_context = latest_student_sponsor_context(session)
    ofs_context = latest_ofs_context(session)
    food_context = latest_food_context(session)
    postcode_context = latest_postcode_context(session)
    property_context = latest_property_context(session)
    school_context = latest_school_context(session)
    ofsted_context = latest_ofsted_context(session)
    runs = list(session.scalars(select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(20)))
    failed_imports = session.scalar(
        select(func.count()).select_from(IngestionRun).where(IngestionRun.status == RunStatus.FAILED)
    ) or 0
    healthy_sources = sum(
        (
            int(bool(settings.companies_house_api_key)),
            int(bool(settings.epc_api_key)),
            int(bool(sponsor_context)),
            int(bool(qualification_context)),
            int(bool(welsh_qualification_context)),
            int(bool(qualification_unit_context)),
            int(bool(student_sponsor_context)),
            int(bool(ofs_context)),
            int(bool(food_context)),
            int(bool(postcode_context)),
            int(bool(property_context)),
            int(bool(school_context)),
            int(bool(ofsted_context)),
            1,
            1,
            1,
        )
    )
    return {
        "data_mode": "live" if settings.companies_house_api_key else "unavailable",
        "sources": {"total": 16, "healthy": healthy_sources, "attention": 16 - healthy_sources},
        "ingestion_runs": [
            {
                "id": run.id,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "status": run.status.value,
                "records_processed": run.records_processed,
                "records_added": run.records_added,
                "records_removed": run.records_removed,
                "records_changed": run.records_changed,
                "error_message": run.error_message,
            }
            for run in runs
        ],
        "unresolved_matches": 0,
        "failed_imports": failed_imports,
        "message": (
            "Official datasets are connected and independently versioned."
            if sponsor_context
            and qualification_context
            and welsh_qualification_context
            and qualification_unit_context
            and student_sponsor_context
            and ofs_context
            and food_context
            and postcode_context
            and property_context
            and school_context
            and ofsted_context
            else "One or more public datasets still need an initial import."
        ),
        "generated_at": datetime.now(timezone.utc),
    }


def _watchlist_entry_view(entry) -> WatchlistEntryView:
    return WatchlistEntryView(
        id=entry.id,
        entity_type=entry.entity_type,
        entity_id=entry.entity_id,
        label=entry.label,
        notifications_enabled=entry.notifications_enabled,
        created_at=entry.created_at,
    )


def _watchlist_alert_view(alert) -> WatchlistAlertView:
    return WatchlistAlertView(
        id=alert.id,
        entity_type=alert.entity_type,
        entity_id=alert.entity_id,
        summary=alert.summary,
        detail=alert.detail,
        email_status=alert.email_status,
        created_at=alert.created_at,
    )


@router.post("/watchlist", response_model=WatchlistEntryView)
async def add_to_watchlist(
    request: WatchlistEntryCreate,
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    require_authenticated(identity)
    entitlement = check_watchlist_entitlement(billing_session, identity.subject_id)
    if not entitlement.allowed:
        raise _entitlement_error(entitlement)
    try:
        entry = add_watchlist_entry(
            billing_session, identity.subject_id, request.entity_type, request.entity_id, request.label
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return _watchlist_entry_view(entry)


@router.patch("/watchlist/{entry_id}", response_model=WatchlistEntryView)
async def update_watchlist_entry(
    entry_id: int,
    request: WatchlistEntryUpdate,
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    require_authenticated(identity)
    entry = set_watchlist_notifications(
        billing_session, identity.subject_id, entry_id, request.notifications_enabled
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Watchlist entry not found.")
    return _watchlist_entry_view(entry)


@router.delete("/watchlist/{entry_id}")
async def remove_from_watchlist(
    entry_id: int,
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    require_authenticated(identity)
    if not remove_watchlist_entry(billing_session, identity.subject_id, entry_id):
        raise HTTPException(status_code=404, detail="Watchlist entry not found.")
    return {"status": "removed"}


@router.get("/watchlist", response_model=list[WatchlistEntryView])
async def get_watchlist(
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    require_authenticated(identity)
    return [_watchlist_entry_view(entry) for entry in list_watchlist(billing_session, identity.subject_id)]


@router.get("/watchlist/alerts", response_model=list[WatchlistAlertView])
async def get_watchlist_alerts(
    limit: int = Query(default=50, ge=1, le=200),
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    require_authenticated(identity)
    return [_watchlist_alert_view(alert) for alert in list_alerts(billing_session, identity.subject_id, limit)]
