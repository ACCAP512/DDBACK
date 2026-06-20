"""Auth routes: login (email + password → JWT) and the current-principal introspection."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from server.api.deps import get_db, get_principal
from server.auth import rbac, service, tokens
from server.auth.context import Principal

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    tenant_id: str


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = service.authenticate(db, email=req.email, password=req.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    token = tokens.create_access_token(
        subject=user.id,
        claims={"tenant": user.tenant_id, "role": user.role.value, "client_scope": user.client_scope_id},
    )
    return TokenResponse(access_token=token, role=user.role.value, tenant_id=user.tenant_id)


@router.get("/me")
def me(principal: Principal = Depends(get_principal)) -> dict:
    return {
        "user_id": principal.user_id,
        "tenant_id": principal.tenant_id,
        "role": principal.role.value,
        "client_scope_id": principal.client_scope_id,
        "permissions": sorted(p.value for p in rbac.permissions_for(principal.role)),
    }
