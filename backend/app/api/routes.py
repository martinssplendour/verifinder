from fastapi import APIRouter

from app.api.routers import (
    account_billing,
    admin,
    areas,
    browse,
    changes,
    companies,
    food,
    health,
    intelligence,
    properties,
    qualifications,
    reports,
    schools,
    sources,
    sponsors,
    study,
    watchlist,
)

router = APIRouter()
router.include_router(account_billing.router)
router.include_router(admin.router)
router.include_router(areas.router)
router.include_router(browse.router)
router.include_router(changes.router)
router.include_router(companies.router)
router.include_router(food.router)
router.include_router(health.router)
router.include_router(intelligence.router)
router.include_router(properties.router)
router.include_router(qualifications.router)
router.include_router(reports.router)
router.include_router(schools.router)
router.include_router(sources.router)
router.include_router(sponsors.router)
router.include_router(study.router)
router.include_router(watchlist.router)
