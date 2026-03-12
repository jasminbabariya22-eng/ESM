from sqlalchemy.orm import Session
from datetime import datetime, timezone
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import joinedload

from app.models.department import Department
from app.models.risk_register import RiskRegister
from app.models.risk_description import RiskDescription
from app.models.risk_treatment import RiskTreatment

from app.models.risk_register_hist import RiskRegisterHist
from app.models.risk_description_hist import RiskDescriptionHist
from app.models.risk_treatment_hist import RiskTreatmentHist


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

# Type Convertion
def to_int(val):
    return int(val) if val not in [None, ""] else None


def to_float(val):
    return float(val) if val not in [None, ""] else None


def to_datetime(val):
    from datetime import datetime
    return datetime.fromisoformat(val) if val not in [None, ""] else None


# CREATE OR UPDATE RISK
def create_update_risk(db: Session, data, current_user):

    try:

        register_data = data.risk_register
        desc_data = data.risk_description
        treatments = data.risk_treatments or []

        
        # RISK REGISTER
       
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

            risk.risk_name = register_data.risk_name
            risk.dept_id = to_int(register_data.dept_id)
            risk.risk_owner_id = to_int(register_data.risk_owner_id)
            risk.risk_co_owner_id = to_int(register_data.risk_co_owner_id)
            risk.financial_year = register_data.financial_year
            risk.risk_status = to_int(register_data.risk_status)
            risk.risk_progress = to_float(register_data.risk_progress)

            risk.modified_by = current_user["id"]
            risk.modified_on = datetime.now(timezone.utc)

        
        # HISTORY ENTRY - REGISTER
       
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

       
        # RISK DESCRIPTION
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

            description.risk_description = desc_data.risk_description
            description.inherent_risk_likelihood_id = to_int(desc_data.inherent_risk_likelihood_id)
            description.inherent_risk_impact_id = to_int(desc_data.inherent_risk_impact_id)
            description.mitigation = desc_data.mitigation
            description.current_risk_likelihood_id = to_int(desc_data.current_risk_likelihood_id)
            description.current_risk_impact_id = to_int(desc_data.current_risk_impact_id)

            description.modified_by = current_user["id"]
            description.modified_on = datetime.now(timezone.utc)

        
        # HISTORY ENTRY - DESCRIPTION
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

        # RISK TREATMENT
        if to_int(desc_data.risk_description_id) > 0:

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



# Risk LIST fromDepartment id
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
                "current_color_code" : current_color_code
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
                .joinedload(RiskTreatment.action_status)
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
                        "action_status_name": rt.action_status.status_name if rt.action_status else None
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
                .joinedload(RiskTreatment.action_owner),

                joinedload(RiskDescription.treatments)
                .joinedload(RiskTreatment.action_status)
            )
            .filter(
                RiskDescription.risk_description_id == description_id,
                RiskDescription.is_deleted == 0
            )
            .first()
        )

        return risk_description

    except Exception as e:
        raise e