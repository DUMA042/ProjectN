"""Rules settings endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from owl.rules.engine import load_rules, save_rule, seed_defaults

router = APIRouter(tags=["rules"])


class RuleUpdateRequest(BaseModel):
    value: dict | list | str | int | float | bool


@router.get("/rules")
def get_all_rules():
    return load_rules()


@router.get("/rules/{key}")
def get_single_rule(key: str):
    rules = load_rules()
    if key not in rules:
        raise HTTPException(status_code=404, detail=f"Rule '{key}' not found")
    return {key: rules[key]}


@router.put("/rules/{key}")
def update_rule(key: str, body: RuleUpdateRequest):
    save_rule(key, body.value)
    return {"status": "ok", "key": key}


@router.post("/rules/seed")
def seed_rules():
    defaults = {
        "working_hours": {
            "monday": {"checkin": {"early_before": "08:30", "normal_start": "08:30", "normal_end": "09:00", "late_after": "09:00"}, "checkout": {"early_before": "17:00", "normal_start": "17:00", "normal_end": "18:00", "late_after": "18:00"}},
            "tuesday": {"checkin": {"early_before": "08:30", "normal_start": "08:30", "normal_end": "09:00", "late_after": "09:00"}, "checkout": {"early_before": "17:00", "normal_start": "17:00", "normal_end": "18:00", "late_after": "18:00"}},
            "wednesday": {"checkin": {"early_before": "08:30", "normal_start": "08:30", "normal_end": "09:00", "late_after": "09:00"}, "checkout": {"early_before": "17:00", "normal_start": "17:00", "normal_end": "18:00", "late_after": "18:00"}},
            "thursday": {"checkin": {"early_before": "08:30", "normal_start": "08:30", "normal_end": "09:00", "late_after": "09:00"}, "checkout": {"early_before": "17:00", "normal_start": "17:00", "normal_end": "18:00", "late_after": "18:00"}},
            "friday": {"checkin": {"early_before": "08:30", "normal_start": "08:30", "normal_end": "09:00", "late_after": "09:00"}, "checkout": {"early_before": "16:00", "normal_start": "16:00", "normal_end": "17:00", "late_after": "17:00"}},
            "saturday": None,
            "sunday": None
        },
        "incomplete_threshold": {"hours": 1},
        "holidays": {"dates": []},
        "eligible_statuses": {"statuses": ["Active"]},
        "leave_overrides_training": True
    }
    seed_defaults(defaults)
    return {"status": "ok", "seeded": list(defaults.keys())}
