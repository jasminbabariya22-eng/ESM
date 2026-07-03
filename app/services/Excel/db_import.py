from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.department import Department
from app.models.role import UserRole
from app.models.user_type import UserType
from app.models.risk_register import RiskRegister
from app.models.risk_description import RiskDescription
from app.models.risk_treatment import RiskTreatment

from app.schemas.risk_register import RiskRegisterCreate
from app.schemas.risk_description import RiskDescriptionCreate
from app.schemas.risk_treatment import RiskTreatmentCreate

from app.services.Excel.excel_parser import RiskRegisterRecord, normalize_risk_code

logger = logging.getLogger("risk_import")


PIPELINE_VERSION = "2026-07-03.1"


# --------------------------------------------------------------------------
# config
# --------------------------------------------------------------------------

DEFAULT_PASSWORD = "123456"

IMPORTER_USER_ID = 1               #admin

FINANCIAL_YEAR = "2026-2027"
DEFAULT_RISK_STATUS = 9
# DEFAULT_APPROVAL_STATUS = 12
DEFAULT_ACTION_STATUS = None


ROLE_TYPE_BY_LABEL = {
    "Risk Owner": {"role_key": "risk_owner", "type_key": "risk owner"},
    "Action Owner": {"role_key": "action_owner", "type_key": "action owner"},
    "Functional Head": {"role_key": "functional_head", "type_key": "functional head"},
}


PRESERVE_ORIGINAL_RISK_ID = True

IMPACT_MAP = {1: "A", 2: "B", 3: "C", 4: "D", 5: "E"}
IMPACT_REVERSE = {v: k for k, v in IMPACT_MAP.items()}


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def split_name(full_name: str) -> tuple[str, str]:
    full_name = (full_name or "").strip()
    if not full_name:
        return "", ""
    parts = full_name.split()
    return parts[0], " ".join(parts[1:])


def parse_risk_code_pair(code: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    if not code:
        return None, None
    likelihood = int(code[0])
    impact = IMPACT_REVERSE.get(code[1])
    return likelihood, impact


# --------------------------------------------------------------------------
# stage 0: caches (one query each, reused for the whole import)
# --------------------------------------------------------------------------

@dataclass
class ImportCaches:
    roles: dict[str, int]
    user_types: dict[str, int]
    departments_by_short_name: dict[str, "Department"]
    departments_by_id: dict[int, "Department"]
    existing_users: dict[tuple[str, str, int, int], "User"]  # (first,last,dept_id,role_id) lower -> User
    existing_users_by_email: dict[str, "User"]
    existing_risk_ids: dict[str, "RiskRegister"]             # "HR-0013" -> RiskRegister
    existing_descriptions: dict[tuple, "RiskDescription"]    # dedup key -> RiskDescription
    existing_treatments: dict[tuple, "RiskTreatment"]        # dedup key -> RiskTreatment


def build_caches(db: Session) -> ImportCaches:
    roles = {
        r.name.strip().lower(): r.id
        for r in db.query(UserRole).filter(UserRole.is_deleted == 0).all()
    }
    user_types = {
        u.name.strip().lower(): u.id
        for u in db.query(UserType).filter(UserType.is_deleted == 0).all()
    }

    depts = db.query(Department).filter(Department.is_deleted == 0).all()
    departments_by_short_name = {d.dept_short_name.strip().upper(): d for d in depts}
    departments_by_id = {d.id: d for d in depts}

    users = db.query(User).filter(User.is_deleted == 0).all()
    existing_users = {
        (u.first_name.strip().lower(), (u.last_name or "").strip().lower(),
         u.dept_id, u.role_id): u
        for u in users
    }
    existing_users_by_email = {
        u.email.strip().lower(): u for u in users if u.email
    }

    existing_risk_ids = {
        r.risk_id: r
        for r in db.query(RiskRegister).filter(RiskRegister.is_deleted == 0).all()
    }

    existing_descriptions = {}
    for d in db.query(RiskDescription).filter(RiskDescription.is_deleted == 0).all():
        key = (d.risk_register_id, _norm(d.risk_description),
               d.inherent_risk_likelihood_id, d.inherent_risk_impact_id,
               d.current_risk_likelihood_id, d.current_risk_impact_id)
        existing_descriptions[key] = d

    existing_treatments = {}
    for t in db.query(RiskTreatment).filter(RiskTreatment.is_deleted == 0).all():
        key = (t.risk_description_id, _norm(t.action_plan))
        existing_treatments[key] = t

    return ImportCaches(
        roles=roles,
        user_types=user_types,
        departments_by_short_name=departments_by_short_name,
        departments_by_id=departments_by_id,
        existing_users=existing_users,
        existing_users_by_email=existing_users_by_email,
        existing_risk_ids=existing_risk_ids,
        existing_descriptions=existing_descriptions,
        existing_treatments=existing_treatments,
    )


def resolve_department(caches: ImportCaches, dept_code: str) -> "Department":

    dept = caches.departments_by_short_name.get((dept_code or "").strip().upper())
    if dept is not None:
        return dept
    raise Exception(
        f"Department code {dept_code!r} (from the Excel's Department "
        f"column) does not match any dept_short_name in the DB. "
        f"Available dept_short_names: {sorted(caches.departments_by_short_name)}"
    )


def validate_departments(caches: ImportCaches, registers: list["RiskRegisterRecord"]) -> None:

    needed = {reg.dept_code.strip().upper() for reg in registers if reg.dept_code}
    known = set(caches.departments_by_short_name)
    missing = sorted(needed - known)
    if missing:
        raise Exception(
            f"The following Department codes from the Excel don't match any "
            f"dept_short_name in the DB: {missing}\n"
            f"Available dept_short_names: {sorted(known)}"
        )


# --------------------------------------------------------------------------
# stage 1: users
# --------------------------------------------------------------------------

def validate_role_mappings(caches: ImportCaches, name_info: dict[str, dict]) -> None:
    
    needed_labels = {info["role"] for info in name_info.values()}

    problems = []
    for label in sorted(needed_labels):
        mapping = ROLE_TYPE_BY_LABEL.get(label)
        if mapping is None:
            problems.append(f"  - {label!r}: no entry in ROLE_TYPE_BY_LABEL at all")
            continue
        if mapping["role_key"] not in caches.roles:
            problems.append(
                f"  - {label!r}: role_key {mapping['role_key']!r} not in DB roles"
            )
        if mapping["type_key"] not in caches.user_types:
            problems.append(
                f"  - {label!r}: type_key {mapping['type_key']!r} not in DB user_types"
            )

    if problems:
        raise Exception(
            "Cannot import -- the following role/user_type mappings need fixing "
            "in ROLE_TYPE_BY_LABEL before any user is created:\n"
            + "\n".join(problems)
            + f"\n\nRoles available in DB: {sorted(caches.roles)}"
            + f"\nUser types available in DB: {sorted(caches.user_types)}"
        )


def collect_users_from_registers(registers: list[RiskRegisterRecord]) -> dict[str, dict]:
    
    name_info: dict[str, dict] = {}                  # lower name -> {"role", "dept_code"}
    display_names: dict[str, str] = {}

    def note(name: str, role: str, dept_code: str):
        name = (name or "").strip()
        if not name:
            return
        key = name.lower()
        display_names.setdefault(key, name)

        if key not in name_info:
            name_info[key] = {"role": role, "dept_code": dept_code}
            return

        existing = name_info[key]
        if existing["role"] != role:
            logger.warning(
                "%r appears as both %r and %r in the sheet; keeping %r",
                name, existing["role"], role, existing["role"],
            )
        if existing["dept_code"] != dept_code:
            logger.warning(
                "%r appears under both dept %r and %r in the sheet; keeping %r",
                name, existing["dept_code"], dept_code, existing["dept_code"],
            )

    for reg in registers:
        note(reg.owner, "Risk Owner", reg.dept_code)
        for desc in reg.descriptions:
            note(desc.owner, "Risk Owner", reg.dept_code)
            for t in desc.treatments:
                note(t.action_owner, "Action Owner", reg.dept_code)

    return {display_names[k]: v for k, v in name_info.items()}


def import_users(db: Session, caches: ImportCaches, name_info: dict[str, dict]) -> dict[str, dict]:
    user_map: dict[str, dict] = {}
    created = 0

    for name, info in name_info.items():
        role_label = info["role"]
        first, last = split_name(name)

        mapping = ROLE_TYPE_BY_LABEL[role_label]  
        role_id = caches.roles[mapping["role_key"]]
        user_type_id = caches.user_types[mapping["type_key"]]
        dept = resolve_department(caches, info["dept_code"])

        logger.debug(
            "resolve user %r: excel_dept=%r -> dept_id=%s (%s), role_label=%r -> role_id=%s, user_type_id=%s",
            name, info["dept_code"], dept.id, dept.dept_short_name,
            role_label, role_id, user_type_id,
        )

        key = (first.lower(), last.lower(), dept.id, role_id)
        user = caches.existing_users.get(key)

        if user is None:
            email = f"{first.lower()}@example.com"
            user = User(
                log_id=email,
                password=DEFAULT_PASSWORD,
                first_name=first,
                last_name=last,
                email=email,
                dept_id=dept.id,
                role_id=role_id,
                user_type_id=user_type_id,
                status="Active",
                created_by=IMPORTER_USER_ID,
                created_on=datetime.utcnow(),
                is_deleted=0,
            )
            db.add(user)
            db.flush()
            db.refresh(user)

            caches.existing_users[key] = user
            created += 1

        user_map[name] = {
            "id": user.id,
            "name": f"{user.first_name} {user.last_name}".strip(),
            "email": user.email,
        }

    logger.info("Users: %d matched to existing, %d newly created", len(user_map) - created, created)
    return user_map


# --------------------------------------------------------------------------
# stage 2: risk registers
# --------------------------------------------------------------------------

def generate_risk_id(db: Session, dept: "Department") -> str:
    dept.last_risk_number += 1
    return f"{dept.dept_short_name}-{str(dept.last_risk_number).zfill(4)}"


def _adopt_existing_number(dept: "Department", risk_id: str) -> None:
    m = re.search(r"-(\d+)$", risk_id)
    if not m:
        return
    n = int(m.group(1))
    if n > dept.last_risk_number:
        dept.last_risk_number = n


def import_risk_registers(
    db: Session,
    caches: ImportCaches,
    registers: list[RiskRegisterRecord],
    user_map: dict[str, dict],
) -> dict[tuple[str, str, str], dict]:
    
    risk_register_map: dict[tuple[str, str, str], dict] = {}
    created, reused = 0, 0

    for reg in registers:
        dept = resolve_department(caches, reg.dept_code)

        db_risk = None
        if reg.existing_risk_id:
            db_risk = caches.existing_risk_ids.get(reg.existing_risk_id)

        if db_risk is None:
            owner_info = user_map.get(reg.owner)
            if owner_info is None:
                logger.warning(
                    "Register %s (%r): owner %r not in user_map, skipping register",
                    reg.group_key, reg.category, reg.owner,
                )
                continue

            if reg.existing_risk_id and PRESERVE_ORIGINAL_RISK_ID:
                risk_id = reg.existing_risk_id
                _adopt_existing_number(dept, risk_id)
            else:
                risk_id = generate_risk_id(db, dept)

            risk_schema = RiskRegisterCreate(
                risk_name=reg.category or reg.group_key,
                dept_id=dept.id,
                risk_owner_id=owner_info["id"],
                risk_co_owner_id=owner_info["id"],
                financial_year=FINANCIAL_YEAR,
                risk_status=DEFAULT_RISK_STATUS,
                risk_progress="0",
                is_active=0,
            )
            db_risk = RiskRegister(
                **risk_schema.model_dump(),
                risk_id=risk_id,
                # created_by = the actual risk owner, not a generic importer id
                created_by=owner_info["id"],
                created_on=datetime.utcnow(),
                is_deleted=0,
            )
            db.add(db_risk)
            db.flush()
            db.refresh(db_risk)
            caches.existing_risk_ids[risk_id] = db_risk
            created += 1
        else:
            reused += 1

        risk_register_map[(reg.source_sheet, reg.dept_code, reg.group_key)] = {
            "obj": db_risk,
            "risk_register_id": db_risk.risk_register_id,
            "risk_id": db_risk.risk_id,
            "owner_id": db_risk.risk_owner_id,
        }

    logger.info("Risk registers: %d created, %d reused (already existed)", created, reused)
    return risk_register_map


# --------------------------------------------------------------------------
# stage 3: risk descriptions
# --------------------------------------------------------------------------

def import_risk_descriptions(
    db: Session,
    caches: ImportCaches,
    registers: list[RiskRegisterRecord],
    risk_register_map: dict[tuple[str, str, str], dict],
    user_map: dict[str, dict],
) -> dict[int, dict]:
  
    description_map: dict[int, dict] = {}
    created, reused = 0, 0

    for reg in registers:
        parent = risk_register_map.get((reg.source_sheet, reg.dept_code, reg.group_key))
        if parent is None:
            continue                     # register was skipped above (missing owner etc.)

        parent_obj = parent["obj"]  

        for desc in reg.descriptions:
            inherent_l, inherent_i = parse_risk_code_pair(desc.inherent_code)
            current_l, current_i = parse_risk_code_pair(desc.current_code)

            dedup_key = (
                parent["risk_register_id"], _norm(desc.description),
                inherent_l, inherent_i, current_l, current_i,
            )
            db_desc = caches.existing_descriptions.get(dedup_key)

            if db_desc is None:
                owner_info = user_map.get(desc.owner) or {"id": parent["owner_id"]}

                RiskDescriptionCreate(  #                          still validate shape/types
                    risk_register_id=parent["risk_register_id"],
                    risk_id=parent_obj.risk_id,
                    risk_description=desc.description,
                    inherent_risk_likelihood_id=inherent_l,
                    inherent_risk_impact_id=inherent_i,
                    mitigation=desc.mitigation,
                    current_risk_likelihood_id=current_l,
                    current_risk_impact_id=current_i,
                )
                
                db_desc = RiskDescription(
                    risk_register_id=parent_obj.risk_register_id,
                    risk_id=parent_obj.risk_id,
                    risk_description=desc.description,
                    inherent_risk_likelihood_id=inherent_l,
                    inherent_risk_impact_id=inherent_i,
                    mitigation=desc.mitigation,
                    current_risk_likelihood_id=current_l,
                    current_risk_impact_id=current_i,
                    # created_by = the actual risk owner for THIS description
                    created_by=owner_info["id"],
                    created_on=datetime.utcnow(),
                    is_deleted=0,
                )
                db.add(db_desc)
                db.flush()
                db.refresh(db_desc)
                assert db_desc.risk_id, (
                    f"risk_id still null after insert for description "
                    f"{desc.description[:40]!r} under {parent_obj.risk_id} "
                    f"-- check the RiskDescription model/column, not just this script."
                )
                caches.existing_descriptions[dedup_key] = db_desc
                created += 1
            else:
                reused += 1

            description_map[id(desc)] = {
                "obj": db_desc,
                "risk_description_id": db_desc.risk_description_id,
                "risk_register_id": db_desc.risk_register_id,
                "risk_id": db_desc.risk_id,
            }

    logger.info("Risk descriptions: %d created, %d already existed (skipped)", created, reused)
    return description_map


# --------------------------------------------------------------------------
# stage 4: risk treatments
# --------------------------------------------------------------------------

def import_risk_treatments(
    db: Session,
    caches: ImportCaches,
    registers: list[RiskRegisterRecord],
    description_map: dict[int, dict],
    user_map: dict[str, dict],
) -> dict[int, dict]:
    treatment_map: dict[int, dict] = {}
    created, reused, skipped = 0, 0, 0

    for reg in registers:
        for desc in reg.descriptions:
            parent = description_map.get(id(desc))
            if parent is None:
                continue

            for t in desc.treatments:
                if not t.action_plan:
                    skipped += 1
                    continue

                owner_info = user_map.get(t.action_owner)
                if owner_info is None:
                    logger.warning(
                        "Treatment %r under %s: action owner %r not in user_map, skipping",
                        t.action_plan[:40], parent["risk_id"], t.action_owner,
                    )
                    skipped += 1
                    continue

                dedup_key = (parent["risk_description_id"], _norm(t.action_plan))
                db_treatment = caches.existing_treatments.get(dedup_key)

                if db_treatment is None:
                    desc_obj = parent["obj"]  

                    RiskTreatmentCreate(  
                        risk_description_id=desc_obj.risk_description_id,
                        risk_register_id=desc_obj.risk_register_id,
                        risk_id=desc_obj.risk_id,
                        action_plan=t.action_plan,
                        action_owner_id=owner_info["id"],
                        target_date=t.due_date,
                        progress="0",
                        action_status_id=DEFAULT_ACTION_STATUS,
                        next_followup_date=None,
                    )
                    
                    
                    db_treatment = RiskTreatment(
                        
                        risk_description_id=desc_obj.risk_description_id,
                        risk_register_id=desc_obj.risk_register_id,
                        risk_id=desc_obj.risk_id,
                        action_plan=t.action_plan,
                        action_owner_id=owner_info["id"],
                        target_date=t.due_date,
                        progress="0",
                        action_status_id=DEFAULT_ACTION_STATUS,
                        next_followup_date=None,
                        approval_status=0,
                        # created_by = the actual action owner for THIS treatment
                        created_by=owner_info["id"],
                        created_on=datetime.utcnow(),
                        is_deleted=0,
                    )
                    db.add(db_treatment)
                    db.flush()
                    db.refresh(db_treatment)
                    assert db_treatment.risk_id, (
                        f"risk_id still null after insert for treatment "
                        f"{t.action_plan[:40]!r} under description {desc_obj.risk_description_id}"
                    )
                    caches.existing_treatments[dedup_key] = db_treatment
                    created += 1
                else:
                    reused += 1

                treatment_map[id(t)] = {"risk_treatment_id": db_treatment.risk_treatment_id}

    logger.info(
        "Risk treatments: %d created, %d already existed, %d skipped (no plan/owner)",
        created, reused, skipped,
    )
    return treatment_map


# --------------------------------------------------------------------------
# orchestrator - single transaction, matches your diagram exactly
# --------------------------------------------------------------------------

def run_import(db: Session, registers: list[RiskRegisterRecord]) -> dict:
    try:
        
        caches = build_caches(db)
        validate_departments(caches, registers)

        name_info = collect_users_from_registers(registers)
        validate_role_mappings(caches, name_info)
        user_map = import_users(db, caches, name_info)

        risk_register_map = import_risk_registers(db, caches, registers, user_map)
        description_map = import_risk_descriptions(db, caches, registers, risk_register_map, user_map)
        treatment_map = import_risk_treatments(db, caches, registers, description_map, user_map)

        db.commit()
        logger.info("Import completed successfully.")

        return {
            "user_map": user_map,
            "risk_register_map": risk_register_map,
            "description_map": description_map,
            "treatment_map": treatment_map,
        }

    except Exception:
        db.rollback()
        logger.exception("Import failed, rolled back.")
        raise