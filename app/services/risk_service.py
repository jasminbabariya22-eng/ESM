from sqlalchemy.orm import Session
from app.models.risk_register import RiskRegister
from app.models.risk_description import RiskDescription
from app.models.risk_treatment import RiskTreatment


def save_risk(db: Session, data):

    # --------------------------
    # SAVE RISK REGISTER
    # --------------------------

    register_data = data.risk_register.dict()

    risk = RiskRegister(**register_data)

    db.add(risk)
    db.commit()
    db.refresh(risk)

    # --------------------------
    # SAVE DESCRIPTION
    # --------------------------

    desc_data = data.risk_description.dict()
    desc_data["risk_register_id"] = risk.risk_register_id

    description = RiskDescription(**desc_data)

    db.add(description)
    db.commit()
    db.refresh(description)

    # --------------------------
    # SAVE TREATMENTS
    # --------------------------

    for treatment in data.risk_treatments:

        treatment_data = treatment.dict()

        treatment_data["risk_register_id"] = risk.risk_register_id
        treatment_data["risk_description_id"] = description.risk_description_id

        new_treatment = RiskTreatment(**treatment_data)

        db.add(new_treatment)

    db.commit()

    return risk


def update_risk(db: Session, risk_id: int, data):

    risk = db.query(RiskRegister).filter(
        RiskRegister.risk_register_id == risk_id
    ).first()

    if not risk:
        return None

    # -------------------
    # UPDATE REGISTER
    # -------------------

    for key, value in data.risk_register.dict().items():
        setattr(risk, key, value)

    db.commit()

    # -------------------
    # UPDATE DESCRIPTION
    # -------------------

    desc = db.query(RiskDescription).filter(
        RiskDescription.risk_register_id == risk_id
    ).first()

    for key, value in data.risk_description.dict().items():
        setattr(desc, key, value)

    db.commit()

    # -------------------
    # DELETE TREATMENTS
    # -------------------

    db.query(RiskTreatment).filter(
        RiskTreatment.risk_register_id == risk_id
    ).delete()

    db.commit()

    # -------------------
    # INSERT NEW
    # -------------------

    for t in data.risk_treatments:

        treatment_data = t.dict()

        treatment_data["risk_register_id"] = risk_id
        treatment_data["risk_description_id"] = desc.risk_description_id

        new_treatment = RiskTreatment(**treatment_data)

        db.add(new_treatment)

    db.commit()

    return risk