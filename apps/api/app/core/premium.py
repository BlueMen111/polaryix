from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class PlanLimits:
    plan: str
    billing: str
    display_name: str
    price_monthly_brl: float
    monthly_credits: int
    max_file_size_mb: int
    max_concurrent_conversions: int
    priority_level: int
    is_premium: bool


FREE_PLAN = PlanLimits(
    plan="free",
    billing="daily",
    display_name="Gratuito",
    price_monthly_brl=0,
    monthly_credits=30,
    max_file_size_mb=100,
    max_concurrent_conversions=2,
    priority_level=0,
    is_premium=False,
)

PREMIUM_PLANS: dict[tuple[str, str], PlanLimits] = {
    ("basic", "annual"): PlanLimits("basic", "annual", "Basic Anual", 4.99, 1000, 300, 30, 5, True),
    ("pro", "annual"): PlanLimits("pro", "annual", "Pro Premium Anual", 12.99, 3000, 1024, 600, 10, True),
    ("basic", "monthly"): PlanLimits("basic", "monthly", "Basic Mensal", 9.99, 1000, 300, 30, 5, True),
    ("pro", "monthly"): PlanLimits("pro", "monthly", "Pro Premium Mensal", 18.99, 3000, 1024, 600, 10, True),
}


def normalize_plan(plan: str | None) -> str:
    value = (plan or "free").strip().lower()
    return value if value in {"free", "basic", "pro"} else "free"


def normalize_billing(billing: str | None) -> str:
    value = (billing or "monthly").strip().lower()
    return value if value in {"monthly", "annual"} else "monthly"


def get_plan_limits(plan: str | None, billing: str | None = "monthly", is_premium: bool | None = None) -> PlanLimits:
    normalized_plan = normalize_plan(plan)
    normalized_billing = normalize_billing(billing)
    if normalized_plan == "free" or is_premium is False:
        return FREE_PLAN

    return PREMIUM_PLANS.get((normalized_plan, normalized_billing), PREMIUM_PLANS[(normalized_plan, "monthly")])


def current_month_key(now: datetime | None = None) -> str:
    current = now or datetime.now(UTC)
    return current.strftime("%Y-%m")


def public_plan_data(plan: PlanLimits) -> dict:
    return asdict(plan)
