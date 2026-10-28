"""ONE place for all permission rules. Every router calls these functions."""
ROLES = ("admin", "hr", "engineering", "employee")
UPLOAD_ROLES = ("admin", "hr", "engineering")


def doc_roles(doc) -> list[str]:
    return [r for r in doc["allowed_roles"].split(",") if r]


def can_view(user, doc) -> bool:
    if doc["company_id"] != user.company_id:          # tenant isolation
        return False
    return user.role == "admin" or user.role in doc_roles(doc)


def can_upload(user) -> bool:
    return user.role in UPLOAD_ROLES


def can_delete(user, doc) -> bool:
    if doc["company_id"] != user.company_id:
        return False
    return user.role == "admin" or (can_upload(user) and doc["uploader_id"] == user.id)


def normalize_roles(roles: list[str]) -> list[str]:
    """Validate role names. Admin always has access. Returns ordered unique list."""
    cleaned = {r.strip().lower() for r in roles if r.strip()}
    bad = cleaned - set(ROLES)
    if bad:
        raise ValueError(f"Unknown roles: {', '.join(sorted(bad))}")
    cleaned.add("admin")
    return [r for r in ROLES if r in cleaned]
