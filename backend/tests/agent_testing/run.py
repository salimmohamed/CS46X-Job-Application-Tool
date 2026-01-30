import sys
from pathlib import Path
import uvicorn
import webbrowser
import time

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.agent_testing.form_template import FormTemplate
from tests.agent_testing.form_server import FormServer

template_path = Path(__file__).parent / "templates" / "mackay_sposito.json"
template = FormTemplate.load_from_file(str(template_path))

server = FormServer(port=8001)
server.register_template(template)

print(f"Server starting on http://127.0.0.1:8001")
print(f"Form: http://127.0.0.1:8001/apply/{template.template_id}")

time.sleep(1)
webbrowser.open(f"http://127.0.0.1:8001/apply/{template.template_id}")

uvicorn.run(server.app, host="127.0.0.1", port=8001)
