"""Demo script to host all 5 templates simultaneously."""

import sys
from pathlib import Path
import webbrowser
import time
import uvicorn
import threading

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.agent_testing.form_template import FormTemplate
from tests.agent_testing.form_server import FormServer


def load_all_templates():
    """Load all recorded templates."""
    templates_dir = Path(__file__).parent / "templates"
    
    # Find all template JSON files
    template_files = list(templates_dir.glob("*.json"))
    
    # Filter out batch results and other non-template files
    template_files = [f for f in template_files if "batch_results" not in f.name]
    
    templates = []
    loaded_ids = set()
    
    for template_file in template_files:
        try:
            template = FormTemplate.load_from_file(str(template_file))
            # Avoid duplicates
            if template.template_id not in loaded_ids:
                templates.append(template)
                loaded_ids.add(template.template_id)
                print(f"✓ Loaded: {template.name} ({template.template_id})")
        except Exception as e:
            print(f"⚠️  Failed to load {template_file.name}: {e}")
    
    return templates


def create_demo_page(server, templates):
    """Create a demo landing page showing all templates."""
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Job Application Forms Demo</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: white;
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        .subtitle {
            color: rgba(255,255,255,0.9);
            text-align: center;
            margin-bottom: 40px;
            font-size: 1.1em;
        }
        .templates-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .template-card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .template-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        }
        .template-card h2 {
            color: #333;
            margin-bottom: 10px;
            font-size: 1.3em;
        }
        .template-card .meta {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 15px;
        }
        .template-card .stats {
            display: flex;
            gap: 15px;
            margin-bottom: 15px;
            font-size: 0.85em;
            color: #555;
        }
        .template-card .stat {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .template-card .stat::before {
            content: "📊";
            font-size: 1.2em;
        }
        .btn {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 24px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 600;
            transition: opacity 0.3s;
            width: 100%;
            text-align: center;
        }
        .btn:hover {
            opacity: 0.9;
        }
        .footer {
            text-align: center;
            color: rgba(255,255,255,0.8);
            margin-top: 40px;
            font-size: 0.9em;
        }
        .badge {
            display: inline-block;
            background: #4CAF50;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.75em;
            margin-left: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Job Application Forms Demo</h1>
        <p class="subtitle">All 5 templates hosted and ready to test</p>
        
        <div class="templates-grid">
"""
    
    for template in templates:
        total_fields = sum(len(p.fields) for p in template.pages)
        html += f"""
            <div class="template-card">
                <h2>{template.name}<span class="badge">✓ Loaded</span></h2>
                <div class="meta">ID: {template.template_id}</div>
                <div class="stats">
                    <div class="stat">{len(template.pages)} page(s)</div>
                    <div class="stat">{total_fields} fields</div>
                </div>
                <a href="/apply/{template.template_id}" class="btn" target="_blank">
                    View & Test Form →
                </a>
            </div>
"""
    
    html += """
        </div>
        
        <div class="footer">
            <p>All forms are fully functional and ready for testing</p>
            <p>Click any form above to open it in a new tab</p>
        </div>
    </div>
</body>
</html>
"""
    return html


def main():
    """Main demo function."""
    print("\n" + "="*70)
    print("JOB APPLICATION FORMS DEMO")
    print("="*70)
    
    # Load all templates
    print("\nLoading templates...")
    templates = load_all_templates()
    
    if not templates:
        print("\n❌ No templates found!")
        print("   Make sure you've recorded some forms first.")
        print("   Run: python form_scraper_tool/record_all_5.py")
        print(f"   Templates directory: {templates_dir}")
        return
    
    print(f"\n✓ Loaded {len(templates)} template(s)")
    if len(templates) < 5:
        print(f"   ⚠️  Only {len(templates)} template(s) found. Record more forms to get all 5.")
        print("   Run: python form_scraper_tool/record_all_5.py")
    
    # Create server
    server = FormServer(port=8001)
    
    # Register all templates
    print("\nRegistering templates with server...")
    for template in templates:
        server.register_template(template)
        print(f"  ✓ Registered: {template.name}")
    
    # Add custom demo route
    from fastapi.responses import HTMLResponse
    
    @server.app.get("/demo")
    async def demo_page():
        return HTMLResponse(content=create_demo_page(server, templates))
    
    # Start server
    print("\n" + "="*70)
    print("Starting demo server...")
    print("="*70)
    print(f"\n🌐 Server URL: http://127.0.0.1:8001")
    print(f"📋 Demo Page: http://127.0.0.1:8001/demo")
    print(f"\nAvailable forms:")
    for i, template in enumerate(templates, 1):
        print(f"  {i}. {template.name}")
        print(f"     → http://127.0.0.1:8001/apply/{template.template_id}")
    
    print("\n" + "="*70)
    print("Opening demo page in browser...")
    print("Press Ctrl+C to stop the server")
    print("="*70 + "\n")
    
    # Wait a moment, then open browser
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:8001/demo")
    
    # Run server
    try:
        uvicorn.run(server.app, host="127.0.0.1", port=8001, log_level="info")
    except KeyboardInterrupt:
        print("\n\nStopping server...")


if __name__ == "__main__":
    main()
