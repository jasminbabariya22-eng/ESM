from pydantic import BaseModel
from typing import List


class RoleMenuCreate(BaseModel):
    role_id: int
    menu_ids: List[int]