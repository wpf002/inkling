from fastapi import Header, HTTPException, status


async def require_session_header(
    x_inkling_session: str | None = Header(default=None, alias="X-Inkling-Session"),
) -> str:
    if not x_inkling_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Inkling-Session header",
        )
    return x_inkling_session
