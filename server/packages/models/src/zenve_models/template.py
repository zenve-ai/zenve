from pydantic import BaseModel


class TemplateVariable(BaseModel):
    name: str
    type: str = "string"
    required: bool = False
    description: str = ""


class TemplateManifest(BaseModel):
    name: str
    description: str = ""
    variables: list[TemplateVariable] = []


class TemplateSummary(BaseModel):
    name: str
    description: str = ""
