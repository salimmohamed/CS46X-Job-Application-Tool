# Page structure + profile -> Selenium fill. Heuristic then OpenAI for unknowns.
import json
import os
import re
from typing import Any, Dict, List, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

import encryption_service
from tests.test_heuristic_matcher import HeuristicMatcher

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def _selector_to_by(selector: str):
    if not selector or " " in selector.strip():
        return By.CSS_SELECTOR, selector or ""
    s = selector.strip()
    if s.startswith("#") and "." not in s[1:] and "[" not in s:
        return By.ID, s[1:]
    return By.CSS_SELECTOR, s


class FormInteractionEngine:
    def __init__(self, headless: bool = False):
        opts = webdriver.ChromeOptions()
        if headless:
            opts.add_argument("--headless")
        self.driver = webdriver.Chrome(options=opts)
        self.matcher = HeuristicMatcher()
        self.found_elements: List[Dict[str, Any]] = []
        self._last_profile: Optional[Dict] = None

    def getDecryptedData(self, encrypted_data: Dict) -> Optional[Dict]:
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            key_path = os.path.join(base_dir, "encryption.key")
            return encryption_service.decrypt_profile_simple(encrypted_data, key_path)
        except Exception as e:
            print(f"Decrypt failed: {e}")
            return None

    def set_page_structure(self, page_structure: Dict[str, Any]) -> None:
        self.found_elements = []
        forms = page_structure.get("forms") or []
        for form in forms:
            category = (form.get("category") or "").lower()
            if category in ("demographic", "eeo", "optional"):
                continue
            for f in form.get("fields") or []:
                sel = f.get("selector") or f.get("id") or f.get("name")
                if not sel:
                    continue
                ident = sel if isinstance(sel, str) else (
                    f.get("id") or f.get("name") or sel
                )
                self.found_elements.append({
                    "tag": "input",
                    "type": (f.get("type") or "text").lower(),
                    "id": ident,
                    "selector": sel,
                    "name": f.get("name"),
                    "placeholder": f.get("placeholder"),
                    "label_text": f.get("label") or "",
                    "aria_label": f.get("aria-label") or f.get("label") or "",
                    "options": f.get("options") or [],
                })

    def load_test_page(self, url: str) -> None:
        self.driver.get(url)

    def get_fields(self) -> List[Dict]:
        self.found_elements = []
        try:
            for tag in ("input", "select", "textarea"):
                for el in self.driver.find_elements(By.TAG_NAME, tag):
                    t = (el.get_attribute("type") or "text").lower()
                    if t in ("hidden", "submit", "button"):
                        continue
                    fid = (
                        el.get_attribute("id") or el.get_attribute("name")
                        or f"{tag}_{len(self.found_elements)}"
                    )
                    meta = {
                        "tag": tag,
                        "type": t,
                        "id": fid,
                        "selector": (
                            f"#{fid}" if el.get_attribute("id")
                            else f"[name='{el.get_attribute('name')}']"
                        ),
                        "name": el.get_attribute("name"),
                        "placeholder": el.get_attribute("placeholder"),
                        "label_text": self._find_label(el),
                        "aria_label": el.get_attribute("aria-label") or "",
                        "options": [],
                    }
                    if tag == "select":
                        try:
                            opts = Select(el).options
                            meta["options"] = [
                                o.text for o in opts
                                if o.text and "select" not in o.text.lower()
                            ]
                        except Exception:
                            pass
                    self.found_elements.append(meta)
            return self.found_elements
        except Exception as e:
            print(f"get_fields failed: {e}")
            return []

    def _find_label(self, element) -> str:
        eid = element.get_attribute("id")
        if eid:
            try:
                label = self.driver.find_element(By.XPATH, f"//label[@for='{eid}']")
                return (label.text or "").strip()
            except Exception:
                pass
        aria = element.get_attribute("aria-label")
        if aria:
            return aria.strip()
        try:
            return (element.find_element(By.XPATH, "..").text or "").split("\n")[0].strip()
        except Exception:
            return ""

    def _value_from_rules(self, meta: Dict, profile: Dict) -> Optional[str]:
        label = (meta.get("label_text") or "").lower()
        name = (meta.get("name") or "").lower()
        if "first" in name and "name" in name or "first name" in label:
            return (profile.get("first_name") or "").strip()
        if "last" in name and "name" in name or "last name" in label:
            return (profile.get("last_name") or "").strip()
        if "visa" in name and "sponsorship" in name or ("visa" in label and "sponsorship" in label):
            v = profile.get("requires_visa_sponsorship")
            return "Yes" if v and str(v).lower() in ("yes", "true", "1") else "No"
        if "referral" in name or "referred" in name or "referral" in label or "referred" in label:
            v = profile.get("referred_by_employee") or profile.get("referred_by_recruiting_agency")
            return "Yes" if v and str(v).lower() in ("yes", "true", "1") else "No"
        if "address" in name or label in ("address", "location"):
            return (profile.get("address") or "").strip()
        if "city" in name or "city" in label:
            return (profile.get("city") or "").strip()
        if "state" in name or "state" in label:
            return (profile.get("state") or "").strip()
        if "postal" in name or "zip" in name or "postal" in label or "zip" in label:
            return (profile.get("zip_code") or profile.get("postal_code") or "").strip()
        if "signature" in name and "disability" in name:
            fn = (profile.get("first_name") or "").strip()
            ln = (profile.get("last_name") or "").strip()
            return f"{fn} {ln}".strip() if fn or ln else None
        if "date" in name and "disability" in name and "signature" not in name:
            from datetime import datetime
            return datetime.now().strftime("%m-%d-%Y")
        return None

    def _verify_selector(self, selector: str) -> bool:
        if not selector:
            return False
        try:
            by, loc = _selector_to_by(selector)
            el = WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located((by, loc))
            )
            return el.is_displayed() and el.is_enabled()
        except Exception:
            return False

    def _select_radio_by_value(self, one_radio, value: str) -> None:
        name = one_radio.get_attribute("name")
        if not name:
            if not one_radio.is_selected():
                one_radio.click()
            return
        radios = self.driver.find_elements(By.CSS_SELECTOR, f"input[type='radio'][name='{name}']")
        val_lower = (value or "").lower().strip()
        for r in radios:
            if not r.is_displayed():
                continue
            v = (r.get_attribute("value") or "").strip().lower()
            if v == val_lower:
                if not r.is_selected():
                    r.click()
                return
            try:
                rid = r.get_attribute("id")
                if rid:
                    lab = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{rid}']")
                    if lab and val_lower in (lab.text or "").lower():
                        if not r.is_selected():
                            r.click()
                        return
            except Exception:
                pass
        if val_lower in ("yes", "true", "1") or (value and value.strip()):
            if not one_radio.is_selected():
                one_radio.click()

    def fill_form_from_profile(
        self, profile_data: Dict, page_structure: Optional[Dict] = None
    ) -> List[Dict]:
        self._last_profile = profile_data
        if page_structure is not None:
            self.set_page_structure(page_structure)
        elif not self.found_elements:
            self.get_fields()

        unknown = []
        results = []
        for meta in self.found_elements:
            sel = meta.get("selector") or meta.get("id")
            if not sel or not self._verify_selector(sel):
                continue
            val = self._value_from_rules(meta, profile_data)
            if val is not None:
                # logs print that it was a rule, and the ID with the rule
                real_id = meta.get("id") or "unnamed_rule_field"
                res = self.execute_fill(
                    val, sel, meta.get("type"), f"rule: {real_id}"
                    )
                if res:
                    results.append(res)
                continue
            key = self.matcher.get_best_match(meta)
            if key != "unknown":
                val = profile_data.get(key)
                if val:
                    field_id = meta.get("id") or "no_id"
                    # logs print that it was a key that was used, and prints the key
                    res = self.execute_fill(
                        val, sel, meta.get("type"), f"key: {key}"
                        )
                    if res:
                        results.append(res)
            else:
                unknown.append(meta)

        if unknown and OpenAI and os.environ.get("OPENAI_API_KEY"):
            try:
                llm_map = self._ai_map_fields(unknown, profile_data)
                for meta in unknown:
                    sel = meta.get("selector") or meta.get("id")
                    if not sel or not self._verify_selector(sel):
                        continue
                    val = llm_map.get(sel) or llm_map.get(meta.get("id"))
                    if val and str(val).strip().upper() != "N/A":
                        res = self.execute_fill(
                            # test logs say that key was gathered with the LLM, and prints the field with it
                            val, sel, meta.get("type"), f"llm: {sel}"
                        )
                        if res:
                            results.append(res)
            except Exception as e:
                print(f"Mapping failed: {e}")
        return results

    def _ai_map_fields(self, elements: List[Dict], profile: Dict) -> Dict[str, str]:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key or not OpenAI:
            return {}
        fields_json = json.dumps([
            {"id": e.get("id"), "selector": e.get("selector"),
             "label_text": e.get("label_text"), "type": e.get("type"),
             "options": e.get("options")}
            for e in elements
        ])[:3000]
        prompt = (
            "Match profile data to form fields. Return JSON: keys = field id/selector, "
            "values = string or N/A. For selects use option strings. "
            f"Profile: {json.dumps(profile)[:2000]} Fields: {fields_json} Return only JSON."
        )
        try:
            client = OpenAI(api_key=api_key)
            model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1500,
            )
            text = (resp.choices[0].message.content or "").strip()
            if "```" in text:
                m = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text)
                if m:
                    text = m.group(1)
            return json.loads(text)
        except Exception:
            return {}

    def execute_fill(
        self, value: str, element_id_or_selector: str,
        field_type: str, backend_key: str
    ) -> Optional[Dict]:
        if not element_id_or_selector:
            return None
        by, locator = _selector_to_by(element_id_or_selector)
        if not locator:
            return None
        try:
            wait = WebDriverWait(self.driver, 10)
            target = wait.until(EC.presence_of_element_located((by, locator)))
            wait.until(EC.visibility_of(target))
        except Exception as e:
            return {"field": backend_key, "status": "FAILED", "error": str(e)}

        try:
            ft = (field_type or "text").lower()
            if target.tag_name.lower() == "select":
                sel = Select(target)
                try:
                    sel.select_by_visible_text(str(value))
                except Exception:
                    try:
                        sel.select_by_value(str(value))
                    except Exception:
                        for opt in sel.options:
                            if (value or "").lower() in (opt.text or "").lower():
                                sel.select_by_visible_text(opt.text)
                                break
            elif ft == "checkbox":
                if str(value).lower() in ("yes", "true", "1", "on"):
                    if not target.is_selected():
                        target.click()
                else:
                    if target.is_selected():
                        target.click()
            elif ft == "radio":
                self._select_radio_by_value(target, str(value))
                return {"field": backend_key, "status": "SUCCESS"}
            elif ft == "file":
                path = getattr(self, "_last_profile", {}).get("resume_path")
                if path and os.path.isfile(os.path.abspath(path)):
                    target.send_keys(os.path.abspath(path))
                else:
                    return {
                        "field": backend_key, "status": "SKIPPED",
                        "note": "file upload (no resume_path)",
                    }
            else:
                target.clear()
                target.send_keys(str(value))
            return {"field": backend_key, "status": "SUCCESS"}
        except Exception as e:
            return {"field": backend_key, "status": "FAILED", "error": str(e)}


    def save_logs(self, results: List[Dict], filename: str = "interaction_log.json") -> None:
        with open(filename, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Logs saved to {filename}")


def main():
    import time
    job_url = os.environ.get("JOB_URL")
    if not job_url:
        print("Set JOB_URL to the live job application page (real-time autofill).")
        return
    engine = FormInteractionEngine(headless=False)
    encrypted_path = os.environ.get("ENCRYPTED_PROFILE", "backend/encrypted_profile.json")

    try:
        engine.driver.get(job_url)
        time.sleep(1.5)
        html = engine.driver.page_source
        url = engine.driver.current_url

        from page_analysis_service import analyze_page_structure  # noqa: E402
        page_structure = analyze_page_structure(html, url)

        if not os.path.exists(encrypted_path):
            engine.set_page_structure(page_structure)
            engine.save_logs([], "full_test_logs.json")
            print(f"No profile at {encrypted_path}; analyzed only.")
            time.sleep(2)
            return

        with open(encrypted_path) as f:
            decrypted = engine.getDecryptedData(json.load(f))
        if not decrypted:
            time.sleep(2)
            return

        profile = decrypted.get("applicant_info") or decrypted
        results = engine.fill_form_from_profile(profile, page_structure=page_structure)
        engine.save_logs({"results": results}, "full_test_logs.json")
        time.sleep(2)
    finally:
        engine.driver.quit()


if __name__ == "__main__":
    main()
