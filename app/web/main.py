from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import WebUser
from app.database.repository import create_web_user, get_web_user_by_email, get_web_user_by_id, list_web_users, update_web_user_password
from app.database.session import engine, init_db, run_migrations
from app.services.cache_service import cache_key, default_cache
from app.services.fixture_menu_service import FixtureMenuService, SAO_PAULO_TZ
from app.web.dependencies import current_web_user, get_db_session
from app.web.schemas import (
    ChangeUserPasswordRequest,
    CreateUserRequest,
    FixtureAnalysisResponse,
    FixtureListResponse,
    LeagueRead,
    LoginRequest,
    PasswordResetRequest,
    RegisterRequest,
    StatusResponse,
    TextPanelResponse,
    WebUserRead,
)
from app.web.security import LoginRateLimiter, create_session_token, hash_password, verify_password
from app.web.user_admin import ADMIN_EMAIL, DEFAULT_USER_ROLE


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.database_migrate_on_startup:
        run_migrations()
    init_db()
    yield


app = FastAPI(
    title="Assist Bet Dashboard",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)
login_limiter = LoginRateLimiter(
    max_attempts=settings.login_rate_limit_attempts,
    window_seconds=settings.login_rate_limit_window_seconds,
)


def _service() -> FixtureMenuService:
    return FixtureMenuService()


def _user_read(user: WebUser) -> WebUserRead:
    return WebUserRead(id=user.id, email=user.email, role=user.role)


def _require_admin(user: WebUser) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a administradores.")


def _validate_password(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A senha deve ter pelo menos 8 caracteres.")


def _role_for_email(email: str) -> str:
    return "admin" if email.lower().strip() == ADMIN_EMAIL else DEFAULT_USER_ROLE


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        settings.web_session_cookie_name,
        token,
        max_age=settings.web_session_expire_minutes * 60,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


@app.post("/api/auth/login", response_model=WebUserRead)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db_session),
) -> WebUserRead:
    client_host = request.client.host if request.client else "unknown"
    limiter_key = f"{client_host}:{payload.email.lower().strip()}"
    if login_limiter.is_limited(limiter_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Aguarde alguns minutos e tente novamente.",
        )

    user = get_web_user_by_email(db, payload.email)
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        login_limiter.record_failure(limiter_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha invalidos.")

    login_limiter.record_success(limiter_key)
    token = create_session_token(user.id, user.email, user.role)
    _set_session_cookie(response, token)
    return _user_read(user)


@app.post("/api/auth/logout")
def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(
        settings.web_session_cookie_name,
        path="/",
        secure=settings.is_production,
        samesite="lax",
    )
    return {"ok": True}


@app.post("/api/auth/register", response_model=WebUserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db_session)) -> WebUserRead:
    _validate_password(payload.password)
    email = payload.email.lower().strip()
    if get_web_user_by_email(db, email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuario ja existe.")

    user = create_web_user(
        db,
        email=email,
        password_hash=hash_password(payload.password),
        role=_role_for_email(email),
    )
    token = create_session_token(user.id, user.email, user.role)
    _set_session_cookie(response, token)
    return _user_read(user)


@app.post("/api/auth/reset-password", response_model=WebUserRead)
def reset_password(payload: PasswordResetRequest, db: Session = Depends(get_db_session)) -> WebUserRead:
    if not settings.password_reset_code:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Recuperacao de senha nao configurada.")
    if payload.reset_code != settings.password_reset_code:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chave de recuperacao invalida.")
    _validate_password(payload.password)

    user = get_web_user_by_email(db, payload.email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado.")
    return _user_read(update_web_user_password(db, user, hash_password(payload.password)))


@app.get("/api/me", response_model=WebUserRead)
def me(user: WebUser = Depends(current_web_user)) -> WebUserRead:
    return _user_read(user)


@app.get("/api/admin/users", response_model=list[WebUserRead])
def admin_list_users(user: WebUser = Depends(current_web_user), db: Session = Depends(get_db_session)) -> list[WebUserRead]:
    _require_admin(user)
    return [_user_read(item) for item in list_web_users(db)]


@app.post("/api/admin/users", response_model=WebUserRead, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    payload: CreateUserRequest,
    user: WebUser = Depends(current_web_user),
    db: Session = Depends(get_db_session),
) -> WebUserRead:
    _require_admin(user)
    _validate_password(payload.password)
    email = payload.email.lower().strip()
    if get_web_user_by_email(db, email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuario ja existe.")
    created = create_web_user(
        db,
        email=email,
        password_hash=hash_password(payload.password),
        role=_role_for_email(email),
    )
    return _user_read(created)


@app.put("/api/admin/users/{user_id}/password", response_model=WebUserRead)
def admin_change_user_password(
    user_id: int,
    payload: ChangeUserPasswordRequest,
    user: WebUser = Depends(current_web_user),
    db: Session = Depends(get_db_session),
) -> WebUserRead:
    _require_admin(user)
    _validate_password(payload.password)
    target = get_web_user_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado.")
    return _user_read(update_web_user_password(db, target, hash_password(payload.password)))


@app.get("/api/leagues", response_model=list[LeagueRead])
def leagues(_: WebUser = Depends(current_web_user)) -> list[LeagueRead]:
    return [
        LeagueRead(key=item.key, label=item.label, league_id=item.league_id, season=item.season)
        for item in _service().get_supported_leagues()
    ]


@app.get("/api/fixtures", response_model=FixtureListResponse)
def fixtures(
    date: str = Query(default="today"),
    league_key: str = Query(...),
    _: WebUser = Depends(current_web_user),
) -> FixtureListResponse:
    service = _service()
    target_date = _resolve_date(date)
    result = service.get_fixtures_for_date(league_key, target_date)
    league = result.get("league")
    return FixtureListResponse(
        ok=bool(result.get("ok")),
        date=str(result.get("date") or target_date),
        league=LeagueRead(
            key=league.key,
            label=league.label,
            league_id=league.league_id,
            season=league.season,
        )
        if league
        else None,
        fixtures=result.get("fixtures") or [],
        error=result.get("error"),
    )


@app.get("/api/fixtures/{fixture_id}/analysis", response_model=FixtureAnalysisResponse)
def fixture_analysis(fixture_id: str, _: WebUser = Depends(current_web_user)) -> FixtureAnalysisResponse:
    payload = _fixture_payload(fixture_id)
    if payload.get("error"):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(payload["error"]))
    return FixtureAnalysisResponse(
        fixture=payload.get("fixture") or {},
        advisor_text=str(payload.get("advisor_text") or ""),
        analysis_mode=str(payload.get("analysis_mode") or ""),
        analysis=payload.get("analysis") or {},
        advice=payload.get("advice") or {},
        dossier=payload.get("dossier") or {},
        card_text=str(payload.get("card_text") or ""),
        player_advice_text=str(payload.get("player_advice_text") or ""),
        injuries_text=str(payload.get("injuries_text") or ""),
    )


@app.get("/api/fixtures/{fixture_id}/players", response_model=TextPanelResponse)
def fixture_players(fixture_id: str, _: WebUser = Depends(current_web_user)) -> TextPanelResponse:
    payload = _fixture_payload(fixture_id)
    if payload.get("error"):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(payload["error"]))
    return TextPanelResponse(
        fixture_id=fixture_id,
        text=str(payload.get("player_advice_text") or ""),
        payload=payload.get("player_advice") or {},
    )


@app.get("/api/fixtures/{fixture_id}/injuries", response_model=TextPanelResponse)
def fixture_injuries(fixture_id: str, _: WebUser = Depends(current_web_user)) -> TextPanelResponse:
    payload = _fixture_payload(fixture_id)
    if payload.get("error"):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(payload["error"]))
    return TextPanelResponse(
        fixture_id=fixture_id,
        text=str(payload.get("injuries_text") or ""),
        payload={"dossier_absences": (payload.get("dossier") or {}).get("absences") or {}},
    )


@app.get("/api/status", response_model=StatusResponse)
def api_status(user: WebUser = Depends(current_web_user)) -> StatusResponse:
    _require_admin(user)
    return StatusResponse(
        environment=settings.environment,
        database=engine.url.drivername,
        api_football_configured=bool(settings.api_football_key),
        openai_configured=bool(settings.openai_api_key),
        cache=default_cache.stats(),
    )


def _fixture_payload(fixture_id: str) -> dict[str, Any]:
    key = cache_key("web.fixture_advisor_payload", fixture_id, include_players=True)
    return default_cache.get_or_set(
        key,
        settings.fixture_payload_cache_seconds,
        lambda: _service().build_fixture_advisor_payload(fixture_id),
    )


def _resolve_date(value: str) -> str:
    normalized = value.strip().lower()
    today = datetime.now(SAO_PAULO_TZ).date()
    if normalized == "today":
        return today.isoformat()
    if normalized == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Data invalida. Use today, tomorrow ou YYYY-MM-DD.") from None


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def serve_spa(full_path: str) -> FileResponse:
    index_file = FRONTEND_DIST / "index.html"
    requested = FRONTEND_DIST / full_path
    if requested.is_file() and requested.resolve().is_relative_to(FRONTEND_DIST.resolve()):
        return FileResponse(requested)
    if index_file.exists():
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Frontend build nao encontrado. Rode o build do React.")
