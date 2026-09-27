from pydantic import BaseModel, Field


class FormulaRegionCreate(BaseModel):
    page_number: int = Field(ge=1)
    x_min: int = Field(ge=0)
    y_min: int = Field(ge=0)
    x_max: int = Field(ge=1)
    y_max: int = Field(ge=1)


class FormulaRegionUpdate(BaseModel):
    x_min: int = Field(ge=0)
    y_min: int = Field(ge=0)
    x_max: int = Field(ge=1)
    y_max: int = Field(ge=1)


class FormulaSubmit(BaseModel):
    latex_final: str = Field(max_length=100000)