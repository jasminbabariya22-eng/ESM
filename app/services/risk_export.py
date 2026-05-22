from sqlalchemy.orm import Session
from io import BytesIO
import pandas as pd

from app.models.risk_register import RiskRegister
from app.models.risk_description import RiskDescription
from app.models.risk_treatment import RiskTreatment


def generate_risk_excel(db: Session, risk_id: str):

    risk = db.query(RiskRegister).filter(
        RiskRegister.risk_id == risk_id
    ).first()

    if not risk:
        raise Exception("Risk not found")

    descriptions = db.query(RiskDescription).filter(
        RiskDescription.risk_register_id == risk.risk_register_id
    ).all()

    rows = []

    for desc in descriptions:

        treatments = db.query(RiskTreatment).filter(
            RiskTreatment.risk_description_id == desc.risk_description_id
        ).all()

        # If description has NO treatment
        if not treatments:

            rows.append({
                "Risk ID": risk.risk_id,
                "Risk Name": risk.risk_name,
                "Description": desc.risk_description,
                "Mitigation": desc.mitigation,
                "Action Plan": "",
                "Owner": "",
                "Progress": ""
            })

        # If description has multiple treatments
        else:

            for tr in treatments:

                rows.append({
                    "Risk ID": risk.risk_id,
                    "Risk Name": risk.risk_name,
                    "Description": desc.risk_description,
                    "Mitigation": desc.mitigation,
                    "Action Plan": tr.action_plan,
                    "Owner": tr.action_owner_id,
                    "Progress": tr.progress
                })

    df = pd.DataFrame(rows)

    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Risk Register")

    output.seek(0)

    return output