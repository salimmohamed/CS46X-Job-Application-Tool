"""Test script for MacKay Sposito form template."""

from test_runner import TestRunner
from form_template import FormTemplate

# Load template
template = FormTemplate.load_from_file("templates/mackay_sposito.json")

# Initialize runner
runner = TestRunner(server_port=8001)
runner.start_server()
runner.register_template(template)

# Sample applicant info
applicant_info = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone": "(555) 123-4567",
    "address": "123 Main St",
    "city": "Seattle",
    "state": "WA",
    "zip_code": "98101",
    "resume_path": "path/to/resume.pdf",
    "requires_visa_sponsorship": False
}

# Run test
print("Running test against MacKay Sposito form...")
results = runner.run_test(
    template_id=template.template_id,
    agent_module_path="job_application_automation.main.JobApplicationAutomator",
    applicant_info=applicant_info,
    headless=True
)

# Print results
print("\n" + "="*60)
print("Test Results")
print("="*60)
print(f"Success: {results.get('success', False)}")
if 'metrics' in results:
    m = results['metrics']
    print(f"Completion: {m.get('completion_percentage', 0):.1f}%")
    print(f"Fields Filled: {m.get('fields_filled', 0)}")
    print(f"Fields Filled Correctly: {m.get('fields_filled_correctly', 0)}")
    print(f"Fields Missed: {m.get('fields_missed', [])}")
    print(f"Buttons Clicked: {m.get('buttons_clicked', 0)}")
    print(f"Validation Errors: {m.get('validation_errors', 0)}")

# Export results
runner.export_results(results, "test_results_mackay_sposito.json")
print("\nResults exported to test_results_mackay_sposito.json")
