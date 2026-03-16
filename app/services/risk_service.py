from sqlalchemy.orm import Session
from datetime import datetime, timezone
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import joinedload
import pandas as pd
import io

from app.models.department import Department
from app.models.risk_register import RiskRegister
from app.models.risk_description import RiskDescription
from app.models.risk_treatment import RiskTreatment
from app.models.risk_action_followup import RiskActionFollowup

from app.models.risk_register_hist import RiskRegisterHist
from app.models.risk_description_hist import RiskDescriptionHist
from app.models.risk_treatment_hist import RiskTreatmentHist

from app.models.mst_status import Status
from app.models.user import User


# Generate Risk ID
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


# Type Conversion
def to_int(val):
    return int(val) if val not in [None, ""] else None


def to_float(val):
    return float(val) if val not in [None, ""] else None


def to_datetime(val):
    from datetime import datetime
    return datetime.fromisoformat(val) if val not in [None, ""] else None


def model_to_dict(obj):
    return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}


# CREATE OR UPDATE RISK
def create_update_risk(db: Session, data, current_user):

    try:

        if not data or not data.risk_register:
            raise ValueError("risk_register is required")

        register_data = data.risk_register
        desc_data = data.risk_description
        treatments = data.risk_treatments or []

        # -----------------------------
        # CREATE OR UPDATE RISK REGISTER
        # -----------------------------

        if to_int(register_data.risk_register_id) == 0:

            risk_id = generate_risk_id(db, to_int(register_data.dept_id))

            risk = RiskRegister(
                risk_id=risk_id,
                risk_name=register_data.risk_name,
                dept_id=to_int(register_data.dept_id),
                risk_owner_id=to_int(register_data.risk_owner_id),
                risk_co_owner_id=to_int(register_data.risk_co_owner_id),
                financial_year=register_data.financial_year,
                risk_status=to_int(register_data.risk_status),
                risk_progress=to_float(register_data.risk_progress),
                created_by=current_user["id"],
                created_on=datetime.now(timezone.utc),
                is_active=0,
                is_deleted=0
            )

            db.add(risk)
            db.flush()

        else:

            risk = db.query(RiskRegister).filter(
                RiskRegister.risk_register_id == to_int(register_data.risk_register_id)
            ).first()

            if not risk:
                raise ValueError("RiskRegister not found")

            risk.risk_name = register_data.risk_name
            risk.dept_id = to_int(register_data.dept_id)
            risk.risk_owner_id = to_int(register_data.risk_owner_id)
            risk.risk_co_owner_id = to_int(register_data.risk_co_owner_id)
            risk.financial_year = register_data.financial_year
            risk.risk_status = to_int(register_data.risk_status)
            risk.risk_progress = to_float(register_data.risk_progress)

            risk.modified_by = current_user["id"]
            risk.modified_on = datetime.now(timezone.utc)

        # -----------------------------
        # HISTORY - RISK REGISTER
        # -----------------------------

        hist_register = RiskRegisterHist(
            risk_register_id=risk.risk_register_id,
            risk_id=risk.risk_id,
            risk_name=risk.risk_name,
            dept_id=risk.dept_id,
            risk_owner_id=risk.risk_owner_id,
            risk_co_owner_id=risk.risk_co_owner_id,
            financial_year=risk.financial_year,
            risk_status=risk.risk_status,
            risk_progress=risk.risk_progress,
            created_by=risk.created_by,
            created_on=risk.created_on,
            modified_by=risk.modified_by,
            modified_on=risk.modified_on,
            is_active=risk.is_active,
            is_deleted=risk.is_deleted
        )

        db.add(hist_register)

        # -----------------------------
        # RISK DESCRIPTION (OPTIONAL)
        # -----------------------------

        description = None

        if desc_data and any([
            desc_data.risk_description not in [None, ""],
            desc_data.mitigation not in [None, ""],
            to_int(desc_data.inherent_risk_likelihood_id) not in [None, 0],
            to_int(desc_data.inherent_risk_impact_id) not in [None, 0],
            to_int(desc_data.current_risk_likelihood_id) not in [None, 0],
            to_int(desc_data.current_risk_impact_id) not in [None, 0]
        ]):

            if to_int(desc_data.risk_description_id) == 0:

                description = RiskDescription(
                    risk_register_id=risk.risk_register_id,
                    risk_id=risk.risk_id,
                    risk_description=desc_data.risk_description,
                    inherent_risk_likelihood_id=to_int(desc_data.inherent_risk_likelihood_id),
                    inherent_risk_impact_id=to_int(desc_data.inherent_risk_impact_id),
                    mitigation=desc_data.mitigation,
                    current_risk_likelihood_id=to_int(desc_data.current_risk_likelihood_id),
                    current_risk_impact_id=to_int(desc_data.current_risk_impact_id),
                    created_by=current_user["id"],
                    created_on=datetime.now(timezone.utc),
                    is_deleted=0
                )

                db.add(description)
                db.flush()

            else:

                description = db.query(RiskDescription).filter(
                    RiskDescription.risk_description_id == to_int(desc_data.risk_description_id)
                ).first()

                if not description:
                    raise ValueError("RiskDescription not found")

                description.risk_description = desc_data.risk_description
                description.inherent_risk_likelihood_id = to_int(desc_data.inherent_risk_likelihood_id)
                description.inherent_risk_impact_id = to_int(desc_data.inherent_risk_impact_id)
                description.mitigation = desc_data.mitigation
                description.current_risk_likelihood_id = to_int(desc_data.current_risk_likelihood_id)
                description.current_risk_impact_id = to_int(desc_data.current_risk_impact_id)

                description.modified_by = current_user["id"]
                description.modified_on = datetime.now(timezone.utc)

            # HISTORY DESCRIPTION

            hist_desc = RiskDescriptionHist(
                risk_description_id=description.risk_description_id,
                risk_register_id=description.risk_register_id,
                risk_id=description.risk_id,
                risk_description=description.risk_description,
                inherent_risk_likelihood_id=description.inherent_risk_likelihood_id,
                inherent_risk_impact_id=description.inherent_risk_impact_id,
                mitigation=description.mitigation,
                current_risk_likelihood_id=description.current_risk_likelihood_id,
                current_risk_impact_id=description.current_risk_impact_id,
                created_by=description.created_by,
                created_on=description.created_on,
                modified_by=description.modified_by,
                modified_on=description.modified_on,
                is_deleted=description.is_deleted
            )

            db.add(hist_desc)

        # -----------------------------
        # RISK TREATMENTS
        # -----------------------------

        saved_treatments = []

        if description is not None:

            if desc_data and to_int(desc_data.risk_description_id) > 0:
                db.query(RiskTreatment).filter(
                    RiskTreatment.risk_description_id == description.risk_description_id
                ).delete()

            for treatment in treatments:

                new_treatment = RiskTreatment(
                    risk_register_id=risk.risk_register_id,
                    risk_description_id=description.risk_description_id,
                    risk_id=risk.risk_id,
                    action_plan=treatment.action_plan,
                    action_owner_id=to_int(treatment.action_owner_id),
                    target_date=to_datetime(treatment.target_date),
                    progress=to_float(treatment.progress),
                    action_status_id=to_int(treatment.action_status_id),
                    next_followup_date=to_datetime(treatment.next_followup_date),
                    created_by=current_user["id"],
                    created_on=datetime.now(timezone.utc),
                    is_deleted=0
                )

                db.add(new_treatment)
                db.flush()

                saved_treatments.append(new_treatment)

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

        return {
            "risk_register": model_to_dict(risk),
            "risk_description": model_to_dict(description) if description else None,
            "risk_treatments": [model_to_dict(t) for t in saved_treatments]
        }

    except Exception as e:
        db.rollback()
        raise e


# Risk get by User
def get_risk_by_user(db, user_id):

    risks = db.query(RiskRegister).filter(
        RiskRegister.risk_owner_id == user_id,
        RiskRegister.is_deleted == 0
    ).all()

    result = []

    for risk in risks:

        description = db.query(RiskDescription).filter(
            RiskDescription.risk_register_id == risk.risk_register_id
        ).first()

        treatments = []

        if description:
            treatments = db.query(RiskTreatment).filter(
                RiskTreatment.risk_description_id == description.risk_description_id
            ).all()

        result.append({
            "risk_register_id": risk.risk_register_id,
            "risk_id": risk.risk_id,
            "risk_name": risk.risk_name,
            "financial_year": risk.financial_year,
            "risk_status": risk.risk_status,
            "risk_progress": risk.risk_progress,
            "description": description,
            "treatments": treatments
        })

    return result



# Risk LIST from Department id
def to_dict(obj):
    return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}

def get_color(score):
    
    if score <= 4:
        return "#4CAF50"
    elif score <= 9:
        return "#FFEB3B"
    elif score <= 16:
        return "#FF9800"
    else:
        return "#F44336"

def get_risk_by_dept(db, dept_id):
    impact_map = {1:"A",2:"B",3:"C",4:"D",5:"E"}
    try:
        query = db.query(
                    RiskRegister,
                    RiskDescription,
                    RiskTreatment
                ).join(
                    RiskDescription,
                    RiskRegister.risk_register_id == RiskDescription.risk_register_id
                ).join(
                    RiskTreatment,
                    RiskDescription.risk_description_id == RiskTreatment.risk_description_id
                )
        if dept_id:
            query = query.filter(
                RiskRegister.dept_id == dept_id,
                RiskRegister.is_deleted == 0
            )
        else:
            query = query.filter(
                RiskRegister.is_deleted == 0
            )

        records = query.order_by(
                RiskRegister.risk_register_id,
                RiskDescription.risk_description_id,
                RiskTreatment.risk_treatment_id
            ).all()    
        

        #result = [ {**to_dict(rr), **to_dict(rd), **to_dict(rt)} for rr, rd, rt in records ]
        result = []
        for rr, rd, rt in records:
            risk_owner_name = None
            if rr.risk_owner:
                risk_owner_name = rr.risk_owner.log_id
                
            risk_status_name = None
            if rt.status:
                risk_status_name = rt.status.status_name
            
            
            likelihood = rd.inherent_risk_likelihood_id
            impact = rd.inherent_risk_impact_id
            current_likelihood = rd.current_risk_likelihood_id
            current_impact = rd.current_risk_impact_id

            inherent_color_str = None
            inherent_color_code = None
            current_color_str = None
            current_color_code = None

            if likelihood and impact:
                inherent_color_str = get_color(likelihood*impact)
                inherent_color_code = f"{likelihood}{impact_map.get(impact)}"
                current_color_str = get_color(current_likelihood*current_impact)
                current_color_code = f"{current_likelihood}{impact_map.get(current_impact)}"

            result.append({
                **to_dict(rr),
                **to_dict(rd),
                **to_dict(rt),
                "inherent_color_str": inherent_color_str,
                "inherent_color_code" : inherent_color_code,
                "current_color_str": current_color_str,
                "current_color_code" : current_color_code,
                "risk_owner_name" : risk_owner_name,
                "risk_status_name": risk_status_name
            })

        return result
    except Exception as e:
        raise e


# Risk Register by risk_id
def get_risk_by_risk_id(db, risk_id):
    impact_map = {1:"A",2:"B",3:"C",4:"D",5:"E"}
    try:
        risks = (
            db.query(RiskRegister)
            .options(
                joinedload(RiskRegister.risk_descriptions)
                .joinedload(RiskDescription.treatments)
                .joinedload(RiskTreatment.action_owner),

                joinedload(RiskRegister.risk_descriptions)
                .joinedload(RiskDescription.treatments)
                .joinedload(RiskTreatment.status)
            )
            .filter(
                RiskRegister.risk_register_id == risk_id,
                RiskRegister.is_deleted == 0
            )
            .all()
        )

        result = []
        for rr in risks:
            risk_dict = to_dict(rr)
            risk_desc_list = []
            for rd in rr.risk_descriptions:
                likelihood = rd.inherent_risk_likelihood_id
                impact = rd.inherent_risk_impact_id
                current_likelihood = rd.current_risk_likelihood_id
                current_impact = rd.current_risk_impact_id

                inherent_color_str = None
                inherent_color_code = None
                current_color_str = None
                current_color_code = None

                if likelihood and impact:
                    inherent_color_str = get_color(likelihood*impact)
                    inherent_color_code = f"{likelihood}{impact_map.get(impact)}"
                if current_likelihood and current_impact:
                    current_color_str = get_color(current_likelihood*current_impact)
                    current_color_code = f"{current_likelihood}{impact_map.get(current_impact)}"


                # treatments array
                treatments_list = []
                for rt in rd.treatments:
                    treatments_list.append({
                        **to_dict(rt),
                        "action_owner_name": rt.action_owner.log_id if rt.action_owner else None,
                        "action_status_name": rt.status.status_name if rt.status else None
                    })
                
                rd_dict = {
                    **to_dict(rd),
                    "inherent_color_str": inherent_color_str,
                    "inherent_color_code": inherent_color_code,
                    "current_color_str": current_color_str,
                    "current_color_code": current_color_code,
                    "treatments": treatments_list
                }
                risk_desc_list.append(rd_dict)
            risk_dict["risk_descriptions"] = risk_desc_list    
            result.append(risk_dict)

        return result
    
    except Exception as e:
        raise e
    
    
# Risk Register by risk_description_id
def get_risk_by_description_id(db, description_id):
    try:

        risk_description = (
            db.query(RiskDescription)
            .options(
                
                joinedload(RiskDescription.treatments)
                .joinedload(RiskTreatment.status)
                .load_only(Status.status_name),

                joinedload(RiskDescription.treatments)
                .joinedload(RiskTreatment.action_owner)
                .load_only(User.log_id)
                )
            .filter(
                RiskDescription.risk_description_id == description_id,
                RiskDescription.is_deleted == 0
            )
            .first()
        )

        result = risk_description.__dict__.copy()

        treatments_list = []

        for t in risk_description.treatments:
            treatment_dict = t.__dict__.copy()

            # remove SQLAlchemy internal state
            treatment_dict.pop("_sa_instance_state", None)

            # add status_name
            treatment_dict["status_name"] = (
                t.status.status_name if t.status else None
            )
            treatment_dict["action_owner_name"] = (
                t.action_owner.log_id if t.action_owner else None
            )

            # remove nested status object
            treatment_dict.pop("status", None)
            treatment_dict.pop("action_owner", None)

            treatments_list.append(treatment_dict)

        result["treatments"] = treatments_list
        result.pop("_sa_instance_state", None)
        return result

    except Exception as e:
        raise e
    
    
    
# Download Risk data

def get_risk_data_excel(db):
    try:
        risks = (
            db.query(RiskRegister)
            .options(
                joinedload(RiskRegister.risk_descriptions)
                .joinedload(RiskDescription.treatments)
            )
            .filter(
                RiskRegister.is_deleted == 0
            )
            .all()
        )
        rows = []

        for risk in risks:

            first_risk = True

            for desc in risk.risk_descriptions:

                first_desc = True

                for treatment in desc.treatments:

                    rows.append({
                        "Risk ID": risk.risk_id if first_risk else "",
                        "Risk Description": desc.risk_description if first_desc else "",
                        "Mitigation": desc.mitigation if first_desc else "",
                        "Risk Treatment": treatment.action_plan
                    })

                    first_risk = False
                    first_desc = False

        df = pd.DataFrame(rows)

        output = io.BytesIO()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Risk Report")

        output.seek(0)

        return output
    except Exception as e:
        raise e
    


# Get Followups by reference_id
def get_followups_by_reference_id(db, reference_id):
    try:

        followups = (
            db.query(RiskActionFollowup)
            .options(
                joinedload(RiskActionFollowup.created_user)
                .load_only(User.log_id),
                
                joinedload(RiskActionFollowup.status_master)
                .load_only(Status.status_name)
            )
            .filter(
                RiskActionFollowup.reference_id == reference_id
            )
            .all()
        )

        result = []

        for followup in followups:

            followup_dict = followup.__dict__.copy()

            # remove SQLAlchemy internal state
            followup_dict.pop("_sa_instance_state", None)

            # add user name
            followup_dict["created_by_name"] = (
                followup.created_user.log_id if followup.created_user else None
            )
            
            # add status name
            followup_dict["status_name"] = (
                followup.status_master.status_name if followup.status_master else None
            )

            # remove relationship object
            followup_dict.pop("created_user", None)
            followup_dict.pop("status_master", None)

            result.append(followup_dict)

        return result

    except Exception as e:
        raise e