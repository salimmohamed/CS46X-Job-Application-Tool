from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json


class FieldType(str, Enum):
    TEXT = "text"
    EMAIL = "email"
    TEL = "tel"
    NUMBER = "number"
    DATE = "date"
    SELECT = "select"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    TEXTAREA = "textarea"
    FILE = "file"
    HIDDEN = "hidden"


@dataclass
class FieldOption:
    value: str
    label: str
    is_default: bool = False


@dataclass
class FormField:
    id: str
    name: str
    label: str
    field_type: FieldType
    required: bool = False
    placeholder: Optional[str] = None
    validation_pattern: Optional[str] = None
    validation_message: Optional[str] = None
    options: List[FieldOption] = field(default_factory=list)
    expected_value_type: Optional[str] = None
    css_selector: Optional[str] = None
    css_class: Optional[str] = None
    help_text: Optional[str] = None


@dataclass
class FormPage:
    page_id: str
    title: str
    description: Optional[str] = None
    fields: List[FormField] = field(default_factory=list)
    submit_button_text: str = "Continue"
    submit_button_selector: Optional[str] = None
    back_button_text: Optional[str] = None
    back_button_selector: Optional[str] = None
    validation_required: bool = True
    css_theme: Optional[str] = None


@dataclass
class FormTemplate:
    template_id: str
    name: str
    description: str
    pages: List[FormPage] = field(default_factory=list)
    start_url: str = "/"
    success_url: str = "/success"
    failure_url: str = "/error"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "pages": [
                {
                    "page_id": page.page_id,
                    "title": page.title,
                    "description": page.description,
                    "fields": [
                        {
                            "id": field.id,
                            "name": field.name,
                            "label": field.label,
                            "field_type": field.field_type.value,
                            "required": field.required,
                            "placeholder": field.placeholder,
                            "validation_pattern": field.validation_pattern,
                            "validation_message": field.validation_message,
                            "options": [
                                {"value": opt.value, "label": opt.label, "is_default": opt.is_default}
                                for opt in field.options
                            ],
                            "expected_value_type": field.expected_value_type,
                            "css_selector": field.css_selector,
                            "css_class": field.css_class,
                            "help_text": field.help_text
                        }
                        for field in page.fields
                    ],
                    "submit_button_text": page.submit_button_text,
                    "submit_button_selector": page.submit_button_selector,
                    "back_button_text": page.back_button_text,
                    "back_button_selector": page.back_button_selector,
                    "validation_required": page.validation_required,
                    "css_theme": page.css_theme
                }
                for page in self.pages
            ],
            "start_url": self.start_url,
            "success_url": self.success_url,
            "failure_url": self.failure_url,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FormTemplate":
        pages = []
        for page_data in data.get("pages", []):
            fields = []
            for field_data in page_data.get("fields", []):
                options = [
                    FieldOption(value=opt["value"], label=opt["label"], is_default=opt.get("is_default", False))
                    for opt in field_data.get("options", [])
                ]
                fields.append(FormField(
                    id=field_data["id"],
                    name=field_data["name"],
                    label=field_data["label"],
                    field_type=FieldType(field_data["field_type"]),
                    required=field_data.get("required", False),
                    placeholder=field_data.get("placeholder"),
                    validation_pattern=field_data.get("validation_pattern"),
                    validation_message=field_data.get("validation_message"),
                    options=options,
                    expected_value_type=field_data.get("expected_value_type"),
                    css_selector=field_data.get("css_selector"),
                    css_class=field_data.get("css_class"),
                    help_text=field_data.get("help_text")
                ))
            pages.append(FormPage(
                page_id=page_data["page_id"],
                title=page_data["title"],
                description=page_data.get("description"),
                fields=fields,
                submit_button_text=page_data.get("submit_button_text", "Continue"),
                submit_button_selector=page_data.get("submit_button_selector"),
                back_button_text=page_data.get("back_button_text"),
                back_button_selector=page_data.get("back_button_selector"),
                validation_required=page_data.get("validation_required", True),
                css_theme=page_data.get("css_theme")
            ))
        
        return cls(
            template_id=data["template_id"],
            name=data["name"],
            description=data["description"],
            pages=pages,
            start_url=data.get("start_url", "/"),
            success_url=data.get("success_url", "/success"),
            failure_url=data.get("failure_url", "/error"),
            metadata=data.get("metadata", {})
        )
    
    def save_to_file(self, filepath: str):
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> "FormTemplate":
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
