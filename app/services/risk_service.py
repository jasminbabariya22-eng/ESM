from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.department import Department
from app.models.risk_register import RiskRegister
from app.models.risk_description import RiskDescription
from app.models.risk_treatment import RiskTreatment

from app.models.risk_register_hist import RiskRegisterHist
from app.models.risk_description_hist import RiskDescriptionHist
from app.models.risk_treatment_hist import RiskTreatmentHist
# -----------------------------
# Generate Risk ID
# -----------------------------
def generate_risk_id(db: Session, dept_id: int):

    dept = db.query(Department).filter(
        Department.id == dept_id
    ).with_for_update().first()

    if not dept:
        raise Exception("Department not found")

    dept.last_risk_number += 1

    number = dept.last_risk_number

    risk_id = f"{dept.dept_short_name}-{str(number).zfill(4)}"

    return risk_id


# -----------------------------
# SAVE FULL RISK
# -----------------------------
def save_full_risk(db: Session, data, current_user):

    try:

        # -----------------------------
        # CREATE RISK REGISTER
        # -----------------------------
        dept_id = data.risk_register.dept_id

        risk_id = generate_risk_id(db, dept_id)

        risk = RiskRegister(
            risk_id=risk_id,
            risk_name=data.risk_register.risk_name,
            dept_id=data.risk_register.dept_id,
            risk_owner_id=data.risk_register.risk_owner_id,
            financial_year=data.risk_register.financial_year,
            risk_status=data.risk_register.risk_status,
            risk_progress=data.risk_register.risk_progress,
            created_by=current_user["id"],
            created_on=datetime.now(timezone.utc),
            is_active=0,
            is_deleted=0
        )

        db.add(risk)
        db.flush()

        # HISTORY
        hist_register = RiskRegisterHist(
            risk_register_id=risk.risk_register_id,
            risk_id=risk.risk_id,
            risk_name=risk.risk_name,
            dept_id=risk.dept_id,
            risk_owner_id=risk.risk_owner_id,
            financial_year=risk.financial_year,
            risk_status=risk.risk_status,
            risk_progress=risk.risk_progress,
            created_by=risk.created_by,
            created_on=datetime.now(timezone.utc),
            is_active=risk.is_active,
            is_deleted=risk.is_deleted
        )

        db.add(hist_register)

        # -----------------------------
        # CREATE RISK DESCRIPTION
        # -----------------------------
        desc = RiskDescription(

            risk_register_id=risk.risk_register_id,
            risk_id=risk.risk_id,

            risk_description=data.risk_description.risk_description,

            inherent_risk_likelihood_id=data.risk_description.inherent_risk_likelihood_id,
            inherent_risk_impact_id=data.risk_description.inherent_risk_impact_id,

            mitigation=data.risk_description.mitigation,

            current_risk_likelihood_id=data.risk_description.current_risk_likelihood_id,
            current_risk_impact_id=data.risk_description.current_risk_impact_id,

            created_by=current_user["id"],
            created_on=datetime.now(timezone.utc),
            is_deleted=0
        )

        db.add(desc)
        db.flush()

        # HISTORY
        hist_desc = RiskDescriptionHist(
            risk_description_id=desc.risk_description_id,
            risk_register_id=desc.risk_register_id,
            risk_id=desc.risk_id,
            risk_description=desc.risk_description,
            inherent_risk_likelihood_id=desc.inherent_risk_likelihood_id,
            inherent_risk_impact_id=desc.inherent_risk_impact_id,
            mitigation=desc.mitigation,
            current_risk_likelihood_id=desc.current_risk_likelihood_id,
            current_risk_impact_id=desc.current_risk_impact_id,
            created_by=desc.created_by,
            created_on=desc.created_on,
            is_deleted=desc.is_deleted
        )

        db.add(hist_desc)

        # -----------------------------
        # CREATE RISK TREATMENTS
        # -----------------------------
        for treatment in data.risk_treatments:

            new_treatment = RiskTreatment(

                risk_description_id=desc.risk_description_id,
                risk_register_id=risk.risk_register_id,
                risk_id=risk.risk_id,

                action_plan=treatment.action_plan,
                action_owner_id=treatment.action_owner_id,
                target_date=treatment.target_date,

                progress=treatment.progress,
                action_status_id=treatment.action_status_id,

                next_followup_date=treatment.next_followup_date,

                created_by=current_user["id"],
                created_on=datetime.now(timezone.utc),

                is_deleted=0
            )

            db.add(new_treatment)
            db.flush()

            # HISTORY
            hist_treatment = RiskTreatmentHist(

                risk_treatment_id=new_treatment.risk_treatment_id,
                risk_description_id=new_treatment.risk_description_id,
                risk_register_id=new_treatment.risk_register_id,
                risk_id=new_treatment.risk_id,

                action_plan=new_treatment.action_plan,
                action_owner_id=new_treatment.action_owner_id,

                target_date=new_treatment.target_date,
                progress=new_treatment.progress,

                action_status_id=new_treatment.action_status_id,
                next_followup_date=new_treatment.next_followup_date,

                created_by=new_treatment.created_by,
                created_on=new_treatment.created_on,

                is_deleted=new_treatment.is_deleted
            )

            db.add(hist_treatment)

        db.commit()

        return risk

    except Exception as e:
        db.rollback()
        raise e


# -----------------------------
# UPDATE RISK
# -----------------------------

def update_risk(db: Session, risk_id: int, data):

    risk = db.query(RiskRegister).filter(
        RiskRegister.risk_register_id == risk_id
    ).first()

    if not risk:
        return None

    # UPDATE REGISTER
    for key, value in data.risk_register.dict().items():
        setattr(risk, key, value)

    # UPDATE DESCRIPTION
    desc = db.query(RiskDescription).filter(
        RiskDescription.risk_register_id == risk_id
    ).first()

    for key, value in data.risk_description.dict().items():
        setattr(desc, key, value)

    # DELETE OLD TREATMENTS
    db.query(RiskTreatment).filter(
        RiskTreatment.risk_register_id == risk_id
    ).delete()

    # INSERT NEW TREATMENTS
    for t in data.risk_treatments:

        treatment_data = t.dict()
        treatment_data["risk_register_id"] = risk_id
        treatment_data["risk_description_id"] = desc.risk_description_id

        new_treatment = RiskTreatment(**treatment_data)

        db.add(new_treatment)

    db.commit()

    return risk



def get_risk_detail(db: Session, risk_id: int):

    risk = db.query(RiskRegister).filter(
        RiskRegister.risk_register_id == risk_id
    ).first()

    if not risk:
        return None

    description = db.query(RiskDescription).filter(
        RiskDescription.risk_register_id == risk_id
    ).first()

    treatments = db.query(RiskTreatment).filter(
        RiskTreatment.risk_register_id == risk_id,
        RiskTreatment.is_deleted == 0
    ).all()

    return {
        "risk": risk,
        "description": description,
        "treatments": treatments
    }