# Live autofill: JOB_URL -> open page, analyze, fill. No template server.
import json
import os
import sys
import time
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
_root = _backend.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))
os.chdir(_root)

try:
    from dotenv import load_dotenv
    for p in (_backend / ".env", _root / ".env"):
        if p.exists():
            load_dotenv(p)
            break
except ImportError:
    pass

from llm_mapping_service import FormInteractionEngine
from page_analysis_service import analyze_page_structure
from compare_analysis_to_html import compare_and_report


def main():
    job_url = os.environ.get("JOB_URL")
    if not job_url:
        print("Set JOB_URL to the live job page.")
        return

    encrypted_path = os.environ.get("ENCRYPTED_PROFILE")
    if not encrypted_path:
        for p in ("backend/encrypted_profile.json", "encrypted_profile.json"):
            if os.path.exists(p):
                encrypted_path = p
                break

    engine = FormInteractionEngine(headless=False)
    try:
        print(f"Opening live page: {job_url}")
        engine.driver.get(job_url)
        time.sleep(2)
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            for text in ("Apply Now", "Apply", "Begin Application"):
                els = engine.driver.find_elements(By.XPATH, f"//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]")
                for el in els[:5]:
                    try:
                        if el.is_displayed() and el.is_enabled():
                            el.click()
                            time.sleep(2.5)
                            break
                    except Exception:
                        continue
                else:
                    continue
                break
        except Exception:
            pass
        try:
            wait = WebDriverWait(engine.driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "form, input[type='text'], input[name]")))
        except Exception:
            pass
        time.sleep(1)
        html = engine.driver.page_source
        url = engine.driver.current_url

        print("Analyzing...", "(API key set)" if os.environ.get("OPENAI_API_KEY") else "(no key)")
        debug_snapshot = {}
        page_structure = analyze_page_structure(html, url, debug_snapshot=debug_snapshot)
        html_sent = debug_snapshot.get("html_sent") or ""

        if os.environ.get("SAVE_ANALYSIS_DEBUG"):
            html_path = _backend / "debug_html_snapshot.html"
            result_path = _backend / "debug_analysis_result.json"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_sent)
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(page_structure, f, indent=2)
            compare_and_report(html_sent, page_structure)

        forms = page_structure.get("forms") or []
        buttons = page_structure.get("buttons") or []
        n_forms = len(forms)
        n_buttons = len(buttons)
        print(f"Found {n_forms} form(s), {n_buttons} button(s)")
        total_fields = 0
        for i, form in enumerate(forms):
            cat = form.get("category") or "other"
            fields = form.get("fields") or []
            total_fields += len(fields)
            print(f"\n--- Form {i + 1} (category={cat}) ---")
            for j, f in enumerate(fields):
                name = f.get("name") or f.get("label") or "(no name)"
                typ = f.get("type") or "text"
                sel = (f.get("selector") or "")[:70]
                req = " required" if f.get("required") else ""
                print(f"  {j + 1}. {name} [{typ}]{req}  selector: {sel}")
        if buttons:
            print("\n--- Buttons ---")
            for b in buttons:
                print(f"  \"{b.get('text')}\"  action={b.get('action')}  selector: {(b.get('selector') or '')[:60]}")
        print(f"\nTotal fields across forms: {total_fields}")

        if encrypted_path and os.path.exists(encrypted_path):
            with open(encrypted_path) as f:
                decrypted = engine.getDecryptedData(json.load(f))
            if decrypted:
                profile = decrypted.get("applicant_info") or decrypted
                results = engine.fill_form_from_profile(
                    profile, page_structure=page_structure
                )
                n_ok = len([r for r in results if r.get("status") == "SUCCESS"])
                print(f"Filled {n_ok} field(s)")
                engine.save_logs({"results": results}, "full_test_logs.json")
            else:
                print("Decrypt failed; no fill")
        else:
            engine.set_page_structure(page_structure)
            print(f"Fields: {len(engine.found_elements)} (no profile)")
        time.sleep(2)
    finally:
        engine.driver.quit()


if __name__ == "__main__":
    main()
