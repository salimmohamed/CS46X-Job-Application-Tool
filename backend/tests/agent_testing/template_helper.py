"""
Helper script to create form templates interactively.

Usage:
    python template_helper.py --url <job_application_url>
    python template_helper.py --create workday
"""

import argparse
import json
from pathlib import Path
try:
    from .form_template import (
        FormTemplate, FormPage, FormField, FieldType, FieldOption
    )
except ImportError:
    from form_template import (
        FormTemplate, FormPage, FormField, FieldType, FieldOption
    )


def create_workday_template() -> FormTemplate:
    """Create Workday-style multi-stage form."""
    return FormTemplate(
        template_id="workday_standard",
        name="Workday Standard Application",
        description="Standard Workday multi-stage application form",
        metadata={"source": "workday", "complexity": "medium"},
        pages=[
            FormPage(
                page_id="personal_info",
                title="Personal Information",
                css_theme="workday",
                fields=[
                    FormField(id="first_name", name="first_name", label="First Name", field_type=FieldType.TEXT, required=True, css_class="wd-input"),
                    FormField(id="last_name", name="last_name", label="Last Name", field_type=FieldType.TEXT, required=True, css_class="wd-input"),
                    FormField(id="email", name="email", label="Email Address", field_type=FieldType.EMAIL, required=True, css_class="wd-input"),
                    FormField(id="phone", name="phone", label="Phone Number", field_type=FieldType.TEL, required=True, css_class="wd-input"),
                ],
                submit_button_text="Continue"
            ),
            FormPage(
                page_id="address",
                title="Address Information",
                fields=[
                    FormField(id="address_line1", name="address_line1", label="Address Line 1", field_type=FieldType.TEXT, required=True),
                    FormField(id="city", name="city", label="City", field_type=FieldType.TEXT, required=True),
                    FormField(id="state", name="state", label="State", field_type=FieldType.SELECT, required=True,
                             options=[FieldOption(value="CA", label="California"), FieldOption(value="NY", label="New York"), FieldOption(value="TX", label="Texas")]),
                    FormField(id="zip_code", name="zip_code", label="ZIP Code", field_type=FieldType.TEXT, required=True),
                ],
                submit_button_text="Continue"
            ),
            FormPage(
                page_id="resume_upload",
                title="Resume & Documents",
                fields=[
                    FormField(id="resume", name="resume", label="Upload Resume", field_type=FieldType.FILE, required=True),
                    FormField(id="cover_letter", name="cover_letter", label="Cover Letter (Optional)", field_type=FieldType.FILE, required=False),
                ],
                submit_button_text="Continue"
            ),
            FormPage(
                page_id="eeoc",
                title="Equal Employment Opportunity",
                fields=[
                    FormField(id="veteran_status", name="veteran_status", label="Veteran Status", field_type=FieldType.RADIO, required=False,
                             options=[
                                 FieldOption(value="not_veteran", label="I AM NOT A PROTECTED VETERAN"),
                                 FieldOption(value="veteran", label="I IDENTIFY AS ONE OR MORE OF THE CLASSIFICATIONS"),
                                 FieldOption(value="decline", label="I DON'T WISH TO ANSWER")
                             ]),
                    FormField(id="disability_status", name="disability_status", label="Disability Status", field_type=FieldType.RADIO, required=False,
                             options=[
                                 FieldOption(value="no_disability", label="NO, I DO NOT HAVE A DISABILITY AND HAVE NOT HAD ONE IN THE PAST"),
                                 FieldOption(value="yes_disability", label="YES, I HAVE A DISABILITY"),
                                 FieldOption(value="decline", label="I DO NOT WANT TO ANSWER")
                             ]),
                ],
                submit_button_text="Submit Application"
            )
        ]
    )


def create_greenhouse_template() -> FormTemplate:
    """Create Greenhouse-style single-page form."""
    return FormTemplate(
        template_id="greenhouse_standard",
        name="Greenhouse Standard Application",
        description="Standard Greenhouse single-page application",
        metadata={"source": "greenhouse", "complexity": "low"},
        pages=[
            FormPage(
                page_id="application",
                title="Job Application",
                fields=[
                    FormField(id="first_name", name="first_name", label="First Name", field_type=FieldType.TEXT, required=True),
                    FormField(id="last_name", name="last_name", label="Last Name", field_type=FieldType.TEXT, required=True),
                    FormField(id="email", name="email", label="Email", field_type=FieldType.EMAIL, required=True),
                    FormField(id="phone", name="phone", label="Phone", field_type=FieldType.TEL, required=False),
                    FormField(id="resume", name="resume", label="Resume", field_type=FieldType.FILE, required=True),
                    FormField(id="cover_letter", name="cover_letter", label="Cover Letter", field_type=FieldType.TEXTAREA, required=False),
                    FormField(id="linkedin_url", name="linkedin_url", label="LinkedIn Profile", field_type=FieldType.TEXT, required=False),
                    FormField(id="website", name="website", label="Personal Website", field_type=FieldType.TEXT, required=False),
                ],
                submit_button_text="Submit Application"
            )
        ]
    )


def create_simple_template() -> FormTemplate:
    """Create minimal test form."""
    return FormTemplate(
        template_id="simple",
        name="Simple Test Form",
        description="Minimal form for basic testing",
        pages=[
            FormPage(
                page_id="main",
                title="Application",
                fields=[
                    FormField(id="name", name="name", label="Full Name", field_type=FieldType.TEXT, required=True),
                    FormField(id="email", name="email", label="Email", field_type=FieldType.EMAIL, required=True),
                ],
                submit_button_text="Submit"
            )
        ]
    )


def create_from_url(url: str) -> FormTemplate:
    """Create template by analyzing URL (placeholder - use scraper tool)."""
    print(f"To create template from URL, use the scraper tool:")
    print(f"  cd form_scraper_tool")
    print(f"  python scrape_forms.py --url {url}")
    return create_simple_template()


def main():
    parser = argparse.ArgumentParser(description="Create form templates")
    parser.add_argument("--create", choices=["workday", "greenhouse", "simple"], help="Create predefined template")
    parser.add_argument("--url", help="URL to analyze (use scraper tool instead)")
    parser.add_argument("--output", default="templates/", help="Output directory")
    
    args = parser.parse_args()
    
    templates_dir = Path(args.output)
    templates_dir.mkdir(parents=True, exist_ok=True)
    
    if args.create:
        if args.create == "workday":
            template = create_workday_template()
        elif args.create == "greenhouse":
            template = create_greenhouse_template()
        else:
            template = create_simple_template()
        
        output_path = templates_dir / f"{template.template_id}.json"
        template.save_to_file(str(output_path))
        print(f"✓ Created {template.name}")
        print(f"  Saved to: {output_path}")
        print(f"  Pages: {len(template.pages)}")
        print(f"  Fields: {sum(len(p.fields) for p in template.pages)}")
    elif args.url:
        template = create_from_url(args.url)
    else:
        print("Use --create <type> to create a template")
        print("Available types: workday, greenhouse, simple")


if __name__ == "__main__":
    main()
