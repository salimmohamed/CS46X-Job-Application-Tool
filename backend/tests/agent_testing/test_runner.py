"""Test runner that executes agent tests and collects metrics."""

from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import time
from datetime import datetime
import threading
import subprocess
import sys

from .form_template import FormTemplate
from .form_server import FormServer
from .interaction_tracker import InteractionTracker


class TestRunner:
    """Runs agent tests against mock forms."""
    
    def __init__(self, server_port: int = 8001):
        """Initialize test runner."""
        self.server_port = server_port
        self.server: Optional[FormServer] = None
        self.server_thread: Optional[threading.Thread] = None
    
    def start_server(self):
        """Start the form server in a background thread."""
        self.server = FormServer(port=self.server_port)
        
        def run_server():
            self.server.run(host="127.0.0.1")
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        # Wait for server to start
        import requests
        max_retries = 10
        for i in range(max_retries):
            try:
                response = requests.get(f"http://127.0.0.1:{self.server_port}/")
                if response.status_code == 200:
                    print(f"Test server started on port {self.server_port}")
                    return
            except:
                time.sleep(0.5)
        
        raise RuntimeError("Failed to start test server")
    
    def stop_server(self):
        """Stop the form server."""
        # Server will stop when process exits
        pass
    
    def register_template(self, template: FormTemplate):
        """Register a form template with the server."""
        if not self.server:
            raise RuntimeError("Server not started. Call start_server() first.")
        self.server.register_template(template)
    
    def run_test(
        self,
        template_id: str,
        agent_module_path: str,
        applicant_info: Dict[str, Any],
        headless: bool = True
    ) -> Dict[str, Any]:
        """
        Run a test against a form template.
        
        Args:
            template_id: ID of the template to test
            agent_module_path: Path to the agent module (e.g., "job_application_automation.main")
            applicant_info: Applicant information dictionary
            headless: Whether to run browser in headless mode
        
        Returns:
            Test results dictionary with metrics
        """
        if not self.server:
            raise RuntimeError("Server not started. Call start_server() first.")
        
        if template_id not in self.server.templates:
            raise ValueError(f"Template '{template_id}' not found")
        
        template = self.server.templates[template_id]
        test_url = f"http://127.0.0.1:{self.server_port}/apply/{template_id}"
        
        print(f"\n{'='*60}")
        print(f"Running test: {template.name}")
        print(f"Template ID: {template_id}")
        print(f"URL: {test_url}")
        print(f"{'='*60}\n")
        
        # Import and run agent
        try:
            # Import agent module
            import importlib
            module_parts = agent_module_path.split('.')
            module = importlib.import_module('.'.join(module_parts[:-1]))
            agent_class = getattr(module, module_parts[-1])
            
            # Create agent instance
            agent = agent_class(headless=headless)
            
            # Run agent
            start_time = time.time()
            success = agent.run(test_url, applicant_info, headless=headless)
            end_time = time.time()
            
            # Get session ID (we'll need to track this)
            # For now, get the most recent session
            session_id = None
            if self.server.trackers:
                session_id = max(self.server.trackers.keys(), key=lambda k: self.server.trackers[k].start_time)
            
            # Get metrics
            results = {
                "test_id": f"{template_id}_{datetime.now().timestamp()}",
                "template_id": template_id,
                "template_name": template.name,
                "test_url": test_url,
                "success": success,
                "duration_seconds": end_time - start_time,
                "session_id": session_id
            }
            
            if session_id and session_id in self.server.trackers:
                tracker = self.server.trackers[session_id]
                tracker.finalize_session(success=success)
                metrics = tracker.get_metrics()
                
                results.update({
                    "metrics": {
                        "total_interactions": metrics.total_interactions,
                        "successful_interactions": metrics.successful_interactions,
                        "failed_interactions": metrics.failed_interactions,
                        "fields_filled": metrics.fields_filled,
                        "fields_filled_correctly": metrics.fields_filled_correctly,
                        "fields_missed": metrics.fields_missed,
                        "fields_incorrect": metrics.fields_incorrect,
                        "buttons_clicked": metrics.buttons_clicked,
                        "buttons_failed": metrics.buttons_failed,
                        "validation_errors": metrics.validation_errors,
                        "completion_percentage": metrics.completion_percentage,
                        "pages_visited": len(metrics.pages_visited),
                        "total_pages": len(template.pages)
                    },
                    "pages": {
                        page_id: {
                            "fields_total": pm.fields_total,
                            "fields_filled": pm.fields_filled,
                            "fields_filled_correctly": pm.fields_filled_correctly,
                            "buttons_clicked": pm.buttons_clicked,
                            "validation_errors": pm.validation_errors
                        }
                        for page_id, pm in metrics.pages_metrics.items()
                    }
                })
            
            return results
            
        except Exception as e:
            return {
                "test_id": f"{template_id}_{datetime.now().timestamp()}",
                "template_id": template_id,
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def run_test_suite(
        self,
        templates: List[FormTemplate],
        agent_module_path: str,
        applicant_info: Dict[str, Any],
        headless: bool = True
    ) -> Dict[str, Any]:
        """Run multiple tests and return aggregated results."""
        # Register all templates
        for template in templates:
            self.register_template(template)
        
        results = []
        for template in templates:
            result = self.run_test(
                template_id=template.template_id,
                agent_module_path=agent_module_path,
                applicant_info=applicant_info,
                headless=headless
            )
            results.append(result)
        
        # Aggregate results
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.get("success", False))
        total_interactions = sum(r.get("metrics", {}).get("total_interactions", 0) for r in results)
        avg_completion = sum(r.get("metrics", {}).get("completion_percentage", 0) for r in results) / total_tests if total_tests > 0 else 0
        
        return {
            "suite_summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": total_tests - successful_tests,
                "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
                "total_interactions": total_interactions,
                "average_completion_percentage": avg_completion
            },
            "test_results": results
        }
    
    def export_results(self, results: Dict[str, Any], filepath: str):
        """Export test results to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Results exported to: {filepath}")


def main():
    """Example usage of the test runner."""
    from .form_template import create_workday_like_template
    
    # Create test template
    template = create_workday_like_template()
    
    # Initialize runner
    runner = TestRunner()
    runner.start_server()
    
    # Register template
    runner.register_template(template)
    
    # Sample applicant info
    applicant_info = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "(555) 123-4567",
        "address": "123 Main St",
        "city": "New York",
        "state": "NY",
        "zip_code": "10001",
        "resume_path": "path/to/resume.pdf"
    }
    
    # Run test
    results = runner.run_test(
        template_id=template.template_id,
        agent_module_path="job_application_automation.main.JobApplicationAutomator",
        applicant_info=applicant_info,
        headless=True
    )
    
    # Export results
    runner.export_results(results, "test_results.json")
    
    print("\nTest Results:")
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
