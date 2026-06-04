from pydantic import BaseModel
import math

class M(BaseModel):
    val: float

m = M(val=math.nan)
print(m.model_dump_json())
