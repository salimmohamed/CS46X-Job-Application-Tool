"""Visualize a form template."""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.agent_testing.form_template import FormTemplate
from tests.agent_testing.form_server import FormServer
import uvicorn
import threading
import time
import webbrowser


def print_template_info(template: FormTemplate):
    """Print template information."""
    print("\n" + "="*70)
    print(f"Template: {template.name}")
    print("="*70)
    print(f"ID: {template.template_id}")
    print(f"Description: {template.description}")
    print(f"Pages: {len(template.pages)}")
    print(f"Total Fields: {sum(len(p.fields) for p in template.pages)}")
    print("\n" + "-"*70)
    
    for i, page in enumerate(template.pages, 1):
        print(f"\nPage {i}: {page.title}")
        print(f"  Page ID: {page.page_id}")
        print(f"  Fields: {len(page.fields)}")
        print(f"  Submit Button: {page.submit_button_text}")
        print("\n  Fields:")
        
        for j, field in enumerate(page.fields, 1):
            req = " [REQUIRED]" if field.required else ""
            print(f"    {j}. {field.label}{req}")
            print(f"       Type: {field.field_type.value}")
            print(f"       ID: {field.id}")
            print(f"       Name: {field.name}")
            if field.options:
                print(f"       Options: {len(field.options)}")
                for opt in field.options[:3]:
                    print(f"         - {opt.label} ({opt.value})")
                if len(field.options) > 3:
                    print(f"         ... and {len(field.options) - 3} more")
            if field.placeholder:
                print(f"       Placeholder: {field.placeholder}")
            if field.css_selector:
                print(f"       Selector: {field.css_selector}")
            print()


def start_server_and_view(template: FormTemplate, port: int = 8001):
    """Start server and open browser."""
    server = FormServer(port=port)
    server.register_template(template)
    
    def run():
        uvicorn.run(server.app, host="127.0.0.1", port=port, log_level="warning")
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    
    # Wait for server
    import requests
    for _ in range(10):
        try:
            response = requests.get(f"http://127.0.0.1:{port}/")
            if response.status_code == 200:
                break
        except:
            time.sleep(0.5)
    
    url = f"http://127.0.0.1:{port}/apply/{template.template_id}"
    print(f"\n{'='*70}")
    print(f"Server started on port {port}")
    print(f"Opening form in browser: {url}")
    print(f"{'='*70}\n")
    print("Press Ctrl+C to stop the server")
    
    webbrowser.open(url)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping server...")


def main():
    # Find template path relative to project root
    script_dir = Path(__file__).parent
    template_path = script_dir / "templates" / "mackay_sposito.json"
    
    if not template_path.exists():
        # Try alternative path
        template_path = Path(__file__).parent.parent.parent.parent / "backend" / "tests" / "agent_testing" / "templates" / "mackay_sposito.json"
    
    if not template_path.exists():
        print(f"Template not found: {template_path}")
        print(f"Current dir: {Path.cwd()}")
        print(f"Script dir: {Path(__file__).parent}")
        return
    
    template = FormTemplate.load_from_file(str(template_path))
    
    # Print template info
    print_template_info(template)
    
    # Ask if user wants to view in browser
    print("\n" + "="*70)
    response = input("Start server and view in browser? (y/n): ").strip().lower()
    
    if response == 'y':
        start_server_and_view(template)
    else:
        print("\nTo view the form, run:")
        print(f"  python {__file__}")
        print("And answer 'y' when prompted.")


if __name__ == "__main__":
    main()
