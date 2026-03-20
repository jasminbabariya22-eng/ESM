from pydantic import BaseModel

class RiskDashboardSummaryResponse(BaseModel):
    year: int
    total: int
    New: int
    opened: int  
    in_progress: int
    Closed: int
    Pending: int
    completed: int  
    approved: int   
    rejected: int   
    
    
class DepartmentWiseRiskResponse(BaseModel):
    department: str
    total: int
    
class EmployeeWiseRiskResponse(BaseModel):
    employee_name: str
    total: int
    
class StatusWisePieResponse(BaseModel):
    status: str
    total: int
    
class DeptartmentwiseprogressResponse(BaseModel):
    department: int
    progress: float