from typing import Dict, Optional
import attr
from stac_fastapi.extensions.core.fields.fields import FieldsExtension
from stac_fastapi.extensions.core.fields.request import PostFieldsExtension, FieldsExtensionPostRequest
from overrides import override
from pydantic import Field


class FixedPostFieldsExtension(PostFieldsExtension):    
    @override
    def filter_fields(self) -> Dict:
        return {**super().filter_fields, "exclude_unset": True}


class FixedFieldsExtensionPostRequest(FieldsExtensionPostRequest):
     fields: Optional[PostFieldsExtension] = Field(FixedPostFieldsExtension())
    

@attr.s
class FixedFieldsExtension(FieldsExtension):
    POST = FixedFieldsExtensionPostRequest