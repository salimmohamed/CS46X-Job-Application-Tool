from fastapi import FastAPI, Request, Form, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Dict, List, Optional, Any
import uvicorn
from pathlib import Path
import json
from datetime import datetime
import re

from .form_template import FormTemplate, FormPage, FormField, FieldType


class FormServer:
    def __init__(self, port: int = 8001):
        self.app = FastAPI(title="Job Application Test Forms")
        self.port = port
        self.templates: Dict[str, FormTemplate] = {}
        self.session_data: Dict[str, Dict[str, Any]] = {}
        self._setup_routes()
    
    def _setup_routes(self):
        @self.app.get("/")
        async def root():
            templates_list = [
                {
                    "id": template_id,
                    "name": template.name,
                    "pages": len(template.pages),
                    "start_url": f"/apply/{template_id}"
                }
                for template_id, template in self.templates.items()
            ]
            return {"status": "running", "templates": templates_list}
        
        @self.app.get("/apply/{template_id}")
        async def start_application(template_id: str, request: Request):
            if template_id not in self.templates:
                raise HTTPException(status_code=404, detail="Template not found")
            
            template = self.templates[template_id]
            session_id = f"{template_id}_{datetime.now().timestamp()}"
            self.session_data[session_id] = {}
            
            first_page = template.pages[0]
            return RedirectResponse(
                url=f"/apply/{template_id}/page/{first_page.page_id}?session={session_id}",
                status_code=302
            )
        
        @self.app.get("/apply/{template_id}/page/{page_id}")
        async def show_page(template_id: str, page_id: str, request: Request, session: Optional[str] = None):
            if template_id not in self.templates:
                raise HTTPException(status_code=404, detail="Template not found")
            
            template = self.templates[template_id]
            page = next((p for p in template.pages if p.page_id == page_id), None)
            
            if not page:
                raise HTTPException(status_code=404, detail="Page not found")
            
            html = self._generate_page_html(template, page, session)
            return HTMLResponse(content=html)
        
        @self.app.post("/apply/{template_id}/page/{page_id}")
        async def submit_page(template_id: str, page_id: str, request: Request, session: Optional[str] = None):
            if template_id not in self.templates:
                raise HTTPException(status_code=404, detail="Template not found")
            
            template = self.templates[template_id]
            page = next((p for p in template.pages if p.page_id == page_id), None)
            
            if not page:
                raise HTTPException(status_code=404, detail="Page not found")
            
            form_data = await request.form()
            files = await request.files()
            
            if session:
                if session not in self.session_data:
                    self.session_data[session] = {}
                
                page_data = {}
                for field in page.fields:
                    if field.field_type == FieldType.FILE:
                        file = files.get(field.name)
                        if file:
                            page_data[field.name] = {"filename": file.filename, "size": 0}
                    else:
                        value = form_data.get(field.name)
                        if value:
                            page_data[field.name] = value
                
                self.session_data[session][page_id] = page_data
            
            if page.validation_required:
                errors = self._validate_page(page, form_data, files)
                if errors:
                    html = self._generate_page_html(template, page, session, errors=errors)
                    return HTMLResponse(content=html)
            
            current_index = next((i for i, p in enumerate(template.pages) if p.page_id == page_id), -1)
            
            if current_index < len(template.pages) - 1:
                next_page = template.pages[current_index + 1]
                return RedirectResponse(
                    url=f"/apply/{template_id}/page/{next_page.page_id}?session={session}",
                    status_code=302
                )
            else:
                return RedirectResponse(url=f"/success?session={session}", status_code=302)
        
        @self.app.get("/success")
        async def success_page(session: Optional[str] = None):
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Application Submitted</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                    .success { color: green; font-size: 24px; }
                </style>
            </head>
            <body>
                <h1 class="success">Application Submitted Successfully!</h1>
            </body>
            </html>
            """
            return HTMLResponse(content=html)
        
    
    def _generate_page_html(self, template: FormTemplate, page: FormPage, session: Optional[str] = None, errors: Optional[Dict[str, str]] = None) -> str:
        errors = errors or {}
        fields_html = ""
        for field in page.fields:
            fields_html += self._generate_field_html(field, errors.get(field.name))
        
        buttons_html = ""
        if page.back_button_text:
            buttons_html += f'<button type="button" onclick="window.history.back()" class="btn-back">{page.back_button_text}</button>'
        buttons_html += f'<button type="submit" class="btn-submit">{page.submit_button_text}</button>'
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{page.title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                .form-container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                h1 {{ margin-top: 0; }}
                .field-group {{ margin-bottom: 20px; }}
                label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
                input, select, textarea {{ width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }}
                .error {{ color: red; font-size: 12px; margin-top: 5px; }}
                .required {{ color: red; }}
                .buttons {{ margin-top: 30px; display: flex; gap: 10px; }}
                .btn-submit, .btn-back {{ padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }}
                .btn-submit {{ background: #007bff; color: white; }}
                .btn-back {{ background: #6c757d; color: white; }}
            </style>
        </head>
        <body>
            <div class="form-container">
                <h1>{page.title}</h1>
                {f'<p>{page.description}</p>' if page.description else ''}
                <form method="post" enctype="multipart/form-data">
                    {fields_html}
                    <div class="buttons">
                        {buttons_html}
                    </div>
                </form>
            </div>
        </body>
        </html>
        """
        return html
    
    def _generate_field_html(self, field: FormField, error: Optional[str] = None) -> str:
        required_marker = '<span class="required">*</span>' if field.required else ''
        error_html = f'<div class="error">{error}</div>' if error else ''
        
        if field.field_type == FieldType.SELECT:
            options_html = "".join([f'<option value="{opt.value}">{opt.label}</option>' for opt in field.options])
            return f"""
            <div class="field-group">
                <label for="{field.id}">{field.label} {required_marker}</label>
                <select id="{field.id}" name="{field.name}" {'required' if field.required else ''}>
                    <option value="">-- Select --</option>
                    {options_html}
                </select>
                {error_html}
            </div>
            """
        
        elif field.field_type == FieldType.RADIO:
            radio_html = "".join([f"""
                <div>
                    <input type="radio" id="{field.id}_{opt.value}" name="{field.name}" value="{opt.value}" {'required' if field.required else ''}>
                    <label for="{field.id}_{opt.value}">{opt.label}</label>
                </div>
            """ for opt in field.options])
            return f"""
            <div class="field-group">
                <label>{field.label} {required_marker}</label>
                {radio_html}
                {error_html}
            </div>
            """
        
        elif field.field_type == FieldType.CHECKBOX:
            return f"""
            <div class="field-group">
                <input type="checkbox" id="{field.id}" name="{field.name}">
                <label for="{field.id}">{field.label} {required_marker}</label>
                {error_html}
            </div>
            """
        
        elif field.field_type == FieldType.TEXTAREA:
            return f"""
            <div class="field-group">
                <label for="{field.id}">{field.label} {required_marker}</label>
                <textarea id="{field.id}" name="{field.name}" placeholder="{field.placeholder or ''}" {'required' if field.required else ''}></textarea>
                {error_html}
            </div>
            """
        
        elif field.field_type == FieldType.FILE:
            return f"""
            <div class="field-group">
                <label for="{field.id}">{field.label} {required_marker}</label>
                <input type="file" id="{field.id}" name="{field.name}" {'required' if field.required else ''}>
                {error_html}
            </div>
            """
        
        else:
            input_type = field.field_type.value if field.field_type in [FieldType.EMAIL, FieldType.TEL, FieldType.NUMBER, FieldType.DATE] else "text"
            return f"""
            <div class="field-group">
                <label for="{field.id}">{field.label} {required_marker}</label>
                <input type="{input_type}" id="{field.id}" name="{field.name}" placeholder="{field.placeholder or ''}" {'required' if field.required else ''}>
                {error_html}
            </div>
            """
    
    def _validate_page(self, page: FormPage, form_data: Any, files: Any) -> Dict[str, str]:
        errors = {}
        for field in page.fields:
            if field.required:
                if field.field_type == FieldType.FILE:
                    if not files.get(field.name):
                        errors[field.name] = f"{field.label} is required"
                else:
                    value = form_data.get(field.name)
                    if not value or (isinstance(value, str) and not value.strip()):
                        errors[field.name] = f"{field.label} is required"
            
            if field.validation_pattern:
                value = form_data.get(field.name)
                if value and not re.match(field.validation_pattern, str(value)):
                    errors[field.name] = field.validation_message or f"{field.label} format is invalid"
        
        return errors
    
    def register_template(self, template: FormTemplate):
        self.templates[template.template_id] = template
    
    def run(self, host: str = "127.0.0.1"):
        uvicorn.run(self.app, host=host, port=self.port)
