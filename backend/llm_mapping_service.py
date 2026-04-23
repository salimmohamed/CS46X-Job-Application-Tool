# Page structure + candidate profile -> Selenium fill.
# Form filling is driven by the candidate profile: rules for common fields (name, address, visa, EEO),
# heuristic matcher for others, and optional OpenAI for unknowns.
import json
import os
import re
import time
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
        opts.add_argument("--log-level=3")
        opts.add_experimental_option("excludeSwitches", ["enable-logging"])
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
                    "option_pairs": f.get("option_pairs") or [],
                })

    def load_test_page(self, url: str) -> None:
        self.driver.get(url)

    def get_fields(self) -> List[Dict]:
        self.found_elements = []
        seen_radio_names = set()
        try:
            for tag in ("input", "select", "textarea"):
                for el in self.driver.find_elements(By.TAG_NAME, tag):
                    t = (el.get_attribute("type") or "text").lower()
                    if t in ("hidden", "submit", "button"):
                        continue
                    # Radio groups: one meta per group with options so veteran/disability get filled once.
                    if tag == "input" and t == "radio":
                        name = el.get_attribute("name")
                        if name and name not in seen_radio_names:
                            seen_radio_names.add(name)
                            try:
                                radios = self.driver.find_elements(
                                    By.CSS_SELECTOR,
                                    f"input[type='radio'][name='{name}']"
                                )
                                options = []
                                for r in radios:
                                    v = (r.get_attribute("value") or "").strip()
                                    lab = (self._find_label(r) or "").strip()
                                    if v or lab:
                                        options.append({"value": v or lab, "label": lab or v})
                                first = radios[0] if radios else el
                                fid = first.get_attribute("id") or name
                                sel = f"#{fid}" if first.get_attribute("id") else f"[name='{name}']"
                                meta = {
                                    "tag": tag,
                                    "type": "radio",
                                    "id": fid,
                                    "selector": sel,
                                    "name": name,
                                    "placeholder": first.get_attribute("placeholder"),
                                    "label_text": self._find_label(first),
                                    "aria_label": first.get_attribute("aria-label") or "",
                                    "options": options,
                                }
                                self.found_elements.append(meta)
                            except Exception:
                                pass
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
                            texts = []
                            option_pairs = []
                            for o in opts:
                                if not o.text or "select" in (o.text or "").lower():
                                    continue
                                t = (o.text or "").strip()
                                val = (o.get_attribute("value") or "").strip()
                                texts.append(t)
                                option_pairs.append({"value": val or t, "text": t})
                            meta["options"] = texts  # backward compat + LLM
                            meta["option_pairs"] = option_pairs  # for matching
                        except Exception:
                            pass
                    self.found_elements.append(meta)
            return self.found_elements
        except Exception as e:
            print(f"get_fields failed: {e}")
            return []

    def _options_for_log(self, meta: Dict) -> Optional[List]:
        """Return a serializable list of options for logging and LLM (labels/values)."""
        opts = meta.get("options")
        pairs = meta.get("option_pairs")
        if pairs:
            return [p.get("text") or p.get("value") for p in pairs]
        if opts and isinstance(opts[0], dict):
            return [o.get("label") or o.get("text") or str(o.get("value", "")) for o in opts]
        return opts if opts else None

    def _pick_eeoc_radio_option(self, meta: Dict, profile_value: str, kind: str) -> Optional[str]:
        """Return the exact option label for veteran or disability that matches profile value (e.g. Not a Veteran -> I AM NOT A PROTECTED VETERAN)."""
        opts = meta.get("options") or []
        if not opts:
            return None
        # options may be list of {value, label} (from get_fields) or list of strings (from page_structure)
        pairs = []
        if isinstance(opts[0], dict):
            for o in opts:
                lab = (o.get("label") or o.get("text") or str(o.get("value", "")) or "").strip()
                if lab:
                    pairs.append((o.get("value"), lab))
        else:
            pairs = [(t, t) for t in opts if isinstance(t, str) and t.strip()]
        if not pairs:
            return None
        val_lower = (profile_value or "").lower().strip()
        # Veteran: match "not a veteran" to "I AM NOT A PROTECTED VETERAN" (exclude "I IDENTIFY..." which has "protected" containing "not")
        if kind == "veteran":
            for _v, lab in pairs:
                lab_lower = lab.lower()
                if "don't wish" in lab_lower or "do not wish" in lab_lower:
                    continue
                if "not" in val_lower and "veteran" in val_lower:
                    if "identify" in lab_lower or "classifications" in lab_lower:
                        continue
                    if "veteran" in lab_lower and (" not " in lab_lower or lab_lower.startswith("not ") or "am not " in lab_lower or "not a " in lab_lower):
                        return lab
                if "veteran" in val_lower and "not" not in val_lower:
                    if "identify" in lab_lower or "classifications" in lab_lower:
                        return lab
        # Disability: match "no disability" to option like "NO, I DO NOT HAVE A DISABILITY"
        if kind == "disability":
            for _v, lab in pairs:
                lab_lower = lab.lower()
                if "don't wish" in lab_lower or "do not wish" in lab_lower or "want to answer" in lab_lower:
                    continue
                if "no" in val_lower and "disability" in val_lower:
                    if ("no" in lab_lower or "not" in lab_lower) and "disability" in lab_lower and ("do not" in lab_lower or "don't" in lab_lower):
                        return lab
                    if "do not have" in lab_lower and "disability" in lab_lower:
                        return lab
                if "yes" in val_lower and "disability" in val_lower:
                    if "yes" in lab_lower and "disability" in lab_lower:
                        return lab
        return None

    def _pick_option_yes_no(self, meta: Dict, want_yes: bool) -> Optional[str]:
        """Return the exact option text that matches Yes or No for dropdowns (visa, relocation, eligibility)."""
        pairs = meta.get("option_pairs") or []
        if not pairs and meta.get("options"):
            # options may be list of strings (from page_structure) or list of {value, label}
            opts = meta["options"]
            if opts and isinstance(opts[0], dict):
                pairs = [{"value": o.get("value", ""), "text": o.get("label") or o.get("text", "")} for o in opts]
            else:
                pairs = [{"value": t, "text": t} for t in opts if isinstance(t, str)]
        if not pairs:
            return None
        key_yes = ("yes", "require", "need", "authorized", "eligible")
        key_no = ("no", "not", "don't", "do not", "n't require", "decline")
        for p in pairs:
            text = (p.get("text") or p.get("label") or str(p.get("value", "")) or "").lower()
            if want_yes and any(k in text for k in key_yes) and not any(k in text for k in ("not", "don't", "do not", "n't")):
                return p.get("text") or p.get("label") or p.get("value")
            if not want_yes and any(k in text for k in key_no):
                return p.get("text") or p.get("label") or p.get("value")
        return None

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
            prev = element.find_element(By.XPATH, "preceding-sibling::label[1]")
            if prev:
                return (prev.text or "").strip()
        except Exception:
            pass
        try:
            prev = element.find_element(By.XPATH, "preceding-sibling::*[1]")
            if prev and prev.tag_name.lower() == "label":
                return (prev.text or "").strip()
        except Exception:
            pass
        # Preceding label in document (for select, question label often precedes the element)
        try:
            prev = element.find_element(By.XPATH, "preceding::label[1]")
            if prev:
                txt = (prev.text or "").strip()
                if txt and "no answer" not in txt.lower() and "select" not in txt.lower():
                    return txt
        except Exception:
            pass
        # Label inside preceding sibling (e.g. <div class="label-wrap"><label>Q</label></div><input>)
        try:
            prev = element.find_element(By.XPATH, "preceding-sibling::*[.//label][1]")
            lab = prev.find_element(By.XPATH, ".//label")
            if lab:
                txt = (lab.text or "").strip()
                if txt and "no answer" not in txt.lower() and len(txt) > 5:
                    return txt
        except Exception:
            pass
        # Label in preceding sibling block (e.g. <div><label>Q</label></div><select>)
        try:
            prev = element.find_element(By.XPATH, "preceding-sibling::*[1]")
            if prev:
                try:
                    lab = prev.find_element(By.XPATH, ".//label")
                    if lab:
                        txt = (lab.text or "").strip()
                        if txt and "no answer" not in txt.lower() and len(txt) > 3:
                            return txt
                except Exception:
                    pass
        except Exception:
            pass
        # First label within nearest ancestor (for wrapped structures)
        try:
            for anc in ("..", "../..", "../../.."):
                try:
                    parent = element.find_element(By.XPATH, anc)
                    lab = parent.find_element(By.XPATH, ".//label")
                    if lab:
                        txt = (lab.text or "").strip()
                        if txt and "no answer" not in txt.lower() and len(txt) > 3:
                            return txt
                except Exception:
                    continue
        except Exception:
            pass
        try:
            raw = (element.find_element(By.XPATH, "..").text or "").split("\n")[0].strip()
            if raw and "no answer" not in raw.lower():
                return raw
        except Exception:
            pass
        return ""

    def _refresh_label_if_empty(self, meta: Dict) -> str:
        """Re-query label from DOM when meta has empty label (e.g. select with placeholder as label)."""
        if (meta.get("label_text") or "").strip():
            return (meta.get("label_text") or "").strip()
        sel = meta.get("selector") or meta.get("id")
        if not sel:
            return ""
        try:
            by, loc = _selector_to_by(sel)
            el = self.driver.find_element(by, loc)
            return (self._find_label(el) or "").strip()
        except Exception:
            return ""

    def _value_from_rules(self, meta: Dict, profile: Dict) -> Optional[str]:
        label = (meta.get("label_text") or "").lower()
        name = (meta.get("name") or "").lower()
        id_attr = (meta.get("id") or "").lower()
        placeholder = (meta.get("placeholder") or "").lower()

        # Refresh label for any field with empty label (helps rules + LLM get question text)
        if not label:
            label = (self._refresh_label_if_empty(meta) or "").lower()
        # Known questionnaire IDs when label is empty (JazzHR/resumator)
        q_match = re.search(r"questionnaire\[?(\d+)\]?|q(\d+)", name or "")
        q_id = (q_match.group(1) or q_match.group(2) or "") if q_match else ""
        if q_id and not label:
            _known = {
                "730787": ("eligible", "work"),
                "730788": ("visa",),
                "730789": ("relocation",),
            }
            for kid, keywords in _known.items():
                if q_id == kid:
                    label = " ".join(keywords)
                    break
        if "first" in name and "name" in name or "first name" in label or "first" in placeholder and "name" in placeholder or "first" in id_attr and "name" in id_attr:
            print(f"!!!!!!!!!!!!!!!!!!!!! first in name and name in name or first name in label: {profile.get("first_name")}")
            return (profile.get("first_name") or "").strip()
        if "last" in name and "name" in name or "last name" in label or "last" in placeholder and "name" in placeholder or "last" in id_attr and "name" in id_attr:
            print(f"!!!!!!!!!!!!!!!!!!!!! last in name and name in name or last name in label: {profile.get("last_name")}")
            return (profile.get("last_name") or "").strip()
        # Work eligibility (eligible to work in the US) -> Yes when work_authorization present
        eligible_key = "eligible" in label or "eligible" in name or "eligibility" in label or "eligibility" in name
        work_key = "work" in label or "work" in name or "authorization" in label or "authorization" in name
        if eligible_key and work_key:
            wa = (profile.get("work_authorization") or "").strip()
            want_yes = bool(wa)
            return self._pick_option_yes_no(meta, want_yes) or ("Yes" if want_yes else "No")
        if "visa" in name or "visa" in label:
            v = profile.get("requires_visa_sponsorship")
            want_yes = v and str(v).lower() in ("yes", "true", "1")
            return self._pick_option_yes_no(meta, want_yes) or ("Yes" if want_yes else "No")
        # H1B/F status describe - leave to LLM or N/A
        if "h1b" in label or "f status" in label or ("visa" in label and "describe" in label):
            return None
        # Wage / salary / desired pay
        if "wage" in label or "salary" in label or "desired pay" in label or "compensation" in label or "pay" in label and "desired" in label:
            return (profile.get("salary_expectation") or profile.get("desired_salary") or "").strip() or None
        # Years of experience (generic or role-specific - use same key for simplicity)
        if "years" in label and "experience" in label:
            return (profile.get("years_of_experience") or profile.get("experience_years") or "").strip() or None
        # Relocation
        if "relocation" in label or "relocation" in name:
            v = profile.get("willing_to_relocate") or profile.get("relocation")
            want_yes = v and str(v).lower() in ("yes", "true", "1")
            return self._pick_option_yes_no(meta, want_yes) or ("Yes" if want_yes else "No")
        # Resume / CV file upload
        if "resume" in label or "resume" in name or "cv" in label or "cv" in name or "attach" in label and "resume" in label:
            return self.RESUME_FILE_SENTINEL
        # Referral: Yes/No only for the main question; "who referred" / "indicate who" get no rule -> LLM returns N/A
        if ("referral" in name or "referred" in name or "referral" in label or "referred" in label) and "who" not in label and "indicate" not in label:
            v = profile.get("referred_by_employee") or profile.get("referred_by_recruiting_agency")
            return "Yes" if v and str(v).lower() in ("yes", "true", "1") else "No"
        if "email" in name or "email" in label:
            return (profile.get("email") or "").strip()
        if "city" in name or "city" in label:
            return (profile.get("city") or "").strip()
        if "state" in name or "state" in label:
            return (profile.get("state") or "").strip()
        if "postal" in name or "zip" in name or "postal" in label or "zip" in label:
            return (profile.get("zip_code") or profile.get("postal_code") or "").strip()
        if "address" in name or label in ("address", "location"):
            # Check if address line 2, suite, apartment, or unit
            if any(x in name or x in label for x in ["2", "line2", "apt", "suite", "unit"]):
                return (profile.get("address_line_2") or "").strip()
            # otherwise return regular address
            return (profile.get("address_line_1") or profile.get("address") or "").strip()
        if "signature" in name and "disability" in name:
            fn = (profile.get("first_name") or "").strip()
            ln = (profile.get("last_name") or "").strip()
            return f"{fn} {ln}".strip() if fn or ln else None
        if "date" in name and "disability" in name and "signature" not in name:
            from datetime import datetime
            return datetime.now().strftime("%m-%d-%Y")
        # EEOC: do not fill unless profile has an explicit value (no defaults; leave blank if empty or decline)
        _decline = ("prefer not", "decline", "choose not", "rather not", "don't wish", "do not wish")
        def _is_decline(s: str) -> bool:
            return not s or any(d in (s or "").lower() for d in _decline)
        # Veteran status - only fill if profile has a value; prefer exact option label when we have options
        if "veteran" in name or "veteran" in label:
            v = (profile.get("veteran_status") or "").strip()
            if v and not _is_decline(v):
                return self._pick_eeoc_radio_option(meta, v, "veteran") or v
            return None
        # Disability status - only fill if profile has a value; prefer exact option label when we have options
        if ("disability" in name or "disability" in label) and "date" not in name and "signature" not in name:
            d = (profile.get("disability_status") or "").strip()
            if d and not _is_decline(d):
                return self._pick_eeoc_radio_option(meta, d, "disability") or d
            return None
        # Gender - only fill if profile has a value and not decline
        if "gender" in name or "eeo_gender" in name or "gender" in label or "sex" in name:
            g = (profile.get("gender") or "").strip()
            return g if g and not _is_decline(g) else None
        # Race / ethnicity - only fill if profile has a value and not decline
        if "race" in name or "ethnicity" in name or "eeo_race" in name or "race" in label or "ethnicity" in label:
            r = (profile.get("race_ethnicity") or profile.get("race") or profile.get("ethnicity") or "").strip()
            return r if r and not _is_decline(r) else None
        return None

    def _verify_selector(self, selector: str) -> bool:
        if not selector:
            return False
        relax = os.environ.get("RELAX_VERIFY", "").lower() in ("1", "true", "yes")
        try:
            by, loc = _selector_to_by(selector)
            el = WebDriverWait(self.driver, 1).until(
                EC.presence_of_element_located((by, loc))
            )
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
            except Exception:
                pass
            if relax:
                return True
            return el.is_displayed() and el.is_enabled()
        except Exception:
            return False

    def _select_radio_by_value(
        self, one_radio, value: str,
        option_index: Optional[int] = None,
        options_from_meta: Optional[List[Dict]] = None,
    ) -> None:
        name = one_radio.get_attribute("name")
        if not name:
            if not one_radio.is_selected():
                one_radio.click()
            return
        radios = self.driver.find_elements(By.CSS_SELECTOR, f"input[type='radio'][name='{name}']")
        # If we have option index from meta (same order as get_fields), click by index - most reliable
        if option_index is not None and 0 <= option_index < len(radios):
            r = radios[option_index]
            if r.is_displayed():
                if not r.is_selected():
                    r.click()
                return
        # Or match by options_from_meta: find index where option label/value matches
        if options_from_meta and isinstance(options_from_meta[0], dict):
            val_lower = (value or "").lower().strip()
            for i, opt in enumerate(options_from_meta):
                lab = (opt.get("label") or opt.get("text") or str(opt.get("value", "")) or "").lower().strip()
                v = (str(opt.get("value", "")) or "").lower().strip()
                # Never match decline options when user wants "not a veteran" or "no disability"
                if "don't wish" in lab or "do not wish" in lab or "want to answer" in lab:
                    continue
                if val_lower in (lab, v) or (val_lower in lab) or (val_lower in v):
                    if i < len(radios) and radios[i].is_displayed():
                        if not radios[i].is_selected():
                            radios[i].click()
                        return
            # Semantic match: "not a veteran" -> option with "not" as word (exclude "identify"/decline options)
            for i, opt in enumerate(options_from_meta):
                lab = (opt.get("label") or opt.get("text") or "").lower()
                if "don't wish" in lab or "do not wish" in lab or "want to answer" in lab:
                    continue
                if "not" in val_lower and "veteran" in val_lower:
                    if ("identify" in lab or "classifications" in lab):
                        continue
                    if "veteran" in lab and (" not " in lab or lab.startswith("not ") or "am not " in lab or "not a " in lab):
                        if i < len(radios) and radios[i].is_displayed():
                            if not radios[i].is_selected():
                                radios[i].click()
                            return
                if "no" in val_lower and "disability" in val_lower:
                    if ("no" in lab or "not" in lab) and "disability" in lab and ("do not" in lab or "don't" in lab):
                        if i < len(radios) and radios[i].is_displayed():
                            if not radios[i].is_selected():
                                radios[i].click()
                            return
            # Fallback: option 2 (index 1) is typically "No" / "I am not a protected veteran" / "No disability"
            if ("not" in val_lower and "veteran" in val_lower) or ("no" in val_lower and "disability" in val_lower):
                if len(radios) >= 2 and radios[1].is_displayed():
                    if not radios[1].is_selected():
                        radios[1].click()
                    return
        val_lower = (value or "").lower().strip()
        if "not" in val_lower and "veteran" in val_lower:
            val_lower = "not a veteran"
        if "no" in val_lower and "disability" in val_lower:
            val_lower = "no disability"
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
                    lab_text = (lab.text or "").lower().strip()
                    if lab and (val_lower == lab_text or val_lower in lab_text or (val_lower.replace(" ", "") in lab_text.replace(" ", ""))):
                        if not r.is_selected():
                            r.click()
                        return
            except Exception:
                pass
            try:
                parent = r.find_element(By.XPATH, "..")
                if parent.tag_name.lower() == "label":
                    pt = (parent.text or "").lower().strip()
                    if val_lower in pt or (len(val_lower) > 10 and val_lower[:20] in pt):
                        if not r.is_selected():
                            r.click()
                        return
            except Exception:
                pass
        for r in radios:
            if not r.is_displayed():
                continue
            v = (r.get_attribute("value") or "").lower()
            if ("veteran" in val_lower and "veteran" in v and "not" in val_lower and ("not" in v or "no" in v)) or \
               ("disability" in val_lower and "disability" in v and "no" in val_lower and ("no" in v or "not" in v)):
                if not r.is_selected():
                    r.click()
                return
        # Demo fallback: option 2 (index 1) is typically "No" for veteran/disability.
        # Set DEMO_EEO_SELECT_FIRST=1 to use option 1 (index 0) instead.
        if ("not" in val_lower and "veteran" in val_lower) or ("no" in val_lower and "disability" in val_lower):
            idx = 0 if os.environ.get("DEMO_EEO_SELECT_FIRST", "").lower() in ("1", "true", "yes") else 1
            if len(radios) > idx and radios[idx].is_displayed():
                if not radios[idx].is_selected():
                    radios[idx].click()
                return
        if val_lower in ("yes", "true", "1"):
            if not one_radio.is_selected():
                one_radio.click()

    def fill_form_from_profile(
        self, profile_data: Dict, page_structure: Optional[Dict] = None,
        log_timing: Optional[Any] = None,
    ) -> List[Dict]:
        """Fill form fields from candidate profile (rules + heuristic + optional LLM)."""
        self._last_profile = profile_data
        if page_structure is not None:
            self.set_page_structure(page_structure)
        elif not self.found_elements:
            self.get_fields()

        def _field_display_name(m: Dict, fallback: str = "field") -> str:
            raw = (m.get("label_text") or m.get("label") or m.get("name") or m.get("id") or m.get("selector") or fallback)
            s = (raw or "").strip()
            return s[:80] if s else fallback

        unknown = []
        results = []
        for meta in self.found_elements:
            sel = meta.get("selector") or meta.get("id")
            if not sel:
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
                # Refresh empty labels so LLM gets question text (wage vs referral etc.)
                for meta in unknown:
                    if not (meta.get("label_text") or "").strip():
                        refreshed = self._refresh_label_if_empty(meta)
                        if refreshed:
                            meta["label_text"] = refreshed
                if log_timing:
                    log_timing("llm_map_fields_start")
                t0 = time.time()
                llm_map = self._ai_map_fields(unknown, profile_data)
                duration = time.time() - t0
                if log_timing:
                    log_timing("llm_map_fields_done", duration_sec=round(duration, 2))
                # Reject LLM values that are clearly reused from wrong profile key (e.g. name in wage field)
                def _is_wrong_reuse(v: str, meta: Dict) -> bool:
                    v = (v or "").strip()
                    if not v:
                        return True
                    lab = (meta.get("label_text") or meta.get("name") or "").lower()
                    profile = getattr(self, "_last_profile", {}) or {}
                    first, last = (profile.get("first_name") or "").strip(), (profile.get("last_name") or "").strip()
                    email = (profile.get("email") or "").strip()
                    phone = (profile.get("phone") or "").strip()
                    addr = (profile.get("address") or "").strip()
                    salary = str(profile.get("salary_expectation") or profile.get("desired_salary") or "").strip()
                    if v == first and "first" not in lab and "name" not in lab:
                        return True
                    if v == last and "last" not in lab and "name" not in lab:
                        return True
                    if v == email and "email" not in lab and "e-mail" not in lab:
                        return True
                    if v == phone and "phone" not in lab and "tel" not in lab:
                        return True
                    if v == addr or (addr and v in addr):
                        if "address" not in lab and "location" not in lab and "street" not in lab:
                            return True
                    # Reject salary in referral fields (referral questions should get Yes/No, not wage)
                    if salary and v == salary:
                        if "refer" in lab or "referral" in lab or "referred" in lab:
                            return True
                    if v.isdigit() or (len(v) > 4 and v.replace(",", "").replace(".", "").isdigit()):
                        if "refer" in lab or "referral" in lab or "referred" in lab:
                            return True
                    return False

                for meta in unknown:
                    sel = meta.get("selector") or meta.get("id")
                    if not sel or not self._verify_selector(sel):
                        # print to test logs if selenium didn't know what to do here
                        results.append({
                            "field": f"skipped: {sel}",
                            "status": "SKIPPED",
                            "reason": "Element not available"
                        })
                        continue
                    val = llm_map.get(sel) or llm_map.get(meta.get("id"))
                    if val and str(val).strip().upper() != "N/A":
                        res = self.execute_fill(
                            # test logs say that key was gathered with the LLM, and prints the field with it
                            val, sel, meta.get("type"), f"llm: {sel}"
                        )
                        if res:
                            results.append(res)
                    else:
                        # print to test log if result was "N/A"
                        results.append({
                            "field": f"key: {sel}",
                            "status": "SKIPPED",
                            "reason": "result was N/A"
                        })

            except Exception as e:
                print(f"Mapping failed: {e}")
        return results

    # Sentinel for resume file upload (rules return this; execute_fill uses resume_path).
    RESUME_FILE_SENTINEL = "__RESUME_FILE__"

    def _ai_map_fields(self, elements: List[Dict], profile: Dict) -> Dict[str, str]:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key or not OpenAI:
            return {}
        def _serialize_options(e: Dict) -> List:
            opts = e.get("options") or []
            pairs = e.get("option_pairs") or []
            if pairs:
                return [{"value": p.get("value"), "label": p.get("label") or p.get("text")} for p in pairs]
            if opts and isinstance(opts[0], dict):
                return opts
            return opts if opts else []

        fields_json = json.dumps([
            {"id": e.get("id"), "selector": e.get("selector"),
             "label_text": e.get("label_text"), "type": e.get("type"),
             "options": _serialize_options(e)}
            for e in elements
        ])[:4000]
        prompt = (
            "Map form fields to profile ONLY when there is a clear semantic match. "
            "Return JSON: keys = field id or selector, values = string value or exactly 'N/A'. "
            "Rules: (1) Use salary_expectation ONLY for wage/salary/desired pay/compensation questions. "
            "NEVER put salary or numbers in referral questions. "
            "(2) Referral questions ('were you referred', 'who referred you') get Yes/No from referred_by_* or 'N/A'. "
            "NEVER put salary_expectation in a referral field. "
            "(3) Use years_of_experience ONLY for years of experience questions. "
            "(4) Do NOT use first_name, last_name, email, phone, address, linkedin_url, portfolio_url "
            "for any other question. (5) If the question has no matching profile key, return 'N/A'. "
            "(6) For follow-up questions (e.g. 'If yes, describe' or 'indicate who') with no specific "
            "profile data, return 'N/A'. "
            "(7) For SELECT and RADIO fields you MUST return one of the exact option labels or option values "
            "from the field's options list (e.g. for veteran_status use the option that means the same; for "
            "requires_visa_sponsorship use the option that matches Yes/No; for disability_status use the matching option; "
            "for relocation use Yes/No from willing_to_relocate). "
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

    def _js_fill_value(self, element, value: str) -> bool:
        """Set value via JavaScript and dispatch input/change (sample-style fallback)."""
        try:
            self.driver.execute_script(
                "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
                element, value
            )
            return True
        except Exception:
            return False

    def execute_fill(
        self, value: str, element_id_or_selector: str,
        field_type: str, backend_key: str, display_name: Optional[str] = None,
        options_available: Optional[List] = None,
        field_meta: Optional[Dict] = None,
    ) -> Optional[Dict]:
        def _fail(msg: str) -> Dict:
            out = {"field": field_label, "status": "FAILED", "error": msg, "source": backend_key}
            if options_available is not None:
                out["options_available"] = options_available
                out["value_tried"] = value
            return out

        def _skip(note: str) -> Dict:
            out = {"field": field_label, "status": "SKIPPED", "note": note, "source": backend_key}
            if options_available is not None:
                out["options_available"] = options_available
                out["value_tried"] = value
            return out

        if not element_id_or_selector:
            return None
        by, locator = _selector_to_by(element_id_or_selector)
        if not locator:
            return None
        field_label = (display_name or backend_key or "").strip() or "field"
        relax = os.environ.get("RELAX_VERIFY", "").lower() in ("1", "true", "yes")
        try:
            wait = WebDriverWait(self.driver, 2)
            target = wait.until(EC.presence_of_element_located((by, locator)))
            if not relax:
                wait.until(EC.visibility_of(target))
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target)
            except Exception:
                pass
        except Exception as e:
            return _fail(str(e) or repr(e))

        try:
            ft = (field_type or "text").lower()
            if target.tag_name.lower() == "select":
                sel = Select(target)
                val_str = (value or "").strip()
                val_lower = val_str.lower()
                try:
                    sel.select_by_visible_text(val_str)
                except Exception:
                    try:
                        sel.select_by_value(val_str)
                    except Exception:
                        matched = False
                        for opt in sel.options:
                            ot = (opt.text or "").strip()
                            ov = (opt.get_attribute("value") or "").strip()
                            if not ot and not ov:
                                continue
                            if val_str in (ot, ov) or val_lower in ot.lower() or val_lower in ov.lower():
                                sel.select_by_visible_text(ot) if ot else sel.select_by_value(ov)
                                matched = True
                                break
                        if not matched:
                            raise ValueError(f"no option matched {val_str!r}")
            elif ft == "checkbox":
                if str(value).lower() in ("yes", "true", "1", "on"):
                    if not target.is_selected():
                        target.click()
                else:
                    if target.is_selected():
                        target.click()
            elif ft == "radio":
                opts = (field_meta or {}).get("options") or []
                option_index = None
                if opts and isinstance(opts[0], dict):
                    val_str = (value or "").strip().lower()
                    for i, o in enumerate(opts):
                        lab = (o.get("label") or o.get("text") or str(o.get("value", "")) or "").lower()
                        v = (str(o.get("value", "")) or "").lower()
                        if val_str in (lab, v) or val_str in lab or val_str in v:
                            option_index = i
                            break
                    if option_index is None and ("not" in val_str and "veteran" in val_str):
                        for i, o in enumerate(opts):
                            lab = (o.get("label") or o.get("text") or "").lower()
                            if "don't wish" in lab or "do not wish" in lab:
                                continue
                            if "identify" in lab or "classifications" in lab:
                                continue
                            if "veteran" in lab and (" not " in lab or lab.startswith("not ") or "am not " in lab or "not a " in lab):
                                option_index = i
                                break
                    if option_index is None and ("no" in val_str and "disability" in val_str):
                        for i, o in enumerate(opts):
                            lab = (o.get("label") or o.get("text") or "").lower()
                            if "want to answer" in lab or "don't wish" in lab:
                                continue
                            if "do not have" in lab and "disability" in lab:
                                option_index = i
                                break
                self._select_radio_by_value(
                    target, str(value),
                    option_index=option_index,
                    options_from_meta=opts if (opts and isinstance(opts[0], dict)) else None,
                )
                out = {"field": field_label, "status": "SUCCESS", "source": backend_key}
                if option_index is not None:
                    out["option_index"] = option_index
                if options_available is not None:
                    out["value_tried"] = value
                return out
            elif ft == "file" or value == self.RESUME_FILE_SENTINEL:
                path = getattr(self, "_last_profile", {}).get("resume_path")
                if not path:
                    return _skip("file upload (no resume_path)")
                # Resolve path: absolute, or relative to backend/cwd
                resolved = os.path.abspath(path)
                if not os.path.isfile(resolved):
                    base = os.path.dirname(os.path.abspath(__file__))
                    resolved = os.path.normpath(os.path.join(base, path.lstrip("/")))
                if not os.path.isfile(resolved):
                    resolved = os.path.normpath(os.path.join(os.getcwd(), path.lstrip("/")))
                if not os.path.isfile(resolved):
                    return _skip(f"resume file not found: {path}")
                # If target is a link/button (e.g. "Attach resume"), find the actual file input
                file_input = target
                if target.tag_name.lower() != "input" or (target.get_attribute("type") or "").lower() != "file":
                    try:
                        file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                    except Exception:
                        return _skip("no file input found for resume (attach link/button only)")
                file_input.send_keys(resolved)
            elif ft in ("text", "email", "tel", "number", "date", "url", "textarea"):
                try:
                    target.clear()
                    target.send_keys(str(value))
                except Exception:
                    if self._js_fill_value(target, str(value)):
                        return {"field": field_label, "status": "SUCCESS", "source": backend_key}
                    raise
            else:
                try:
                    target.clear()
                    target.send_keys(str(value))
                except Exception:
                    if self._js_fill_value(target, str(value)):
                        return {"field": field_label, "status": "SUCCESS", "source": backend_key}
                    raise
            return {"field": field_label, "status": "SUCCESS", "source": backend_key}
        except Exception as e:
            err_msg = str(e) or repr(e)
            try:
                ft_lower = (field_type or "text").lower()
                if ft_lower in ("text", "email", "tel", "number", "date", "url", "textarea") and self._js_fill_value(target, str(value)):
                    return {"field": field_label, "status": "SUCCESS", "source": backend_key}
            except Exception:
                pass
            return _fail(err_msg)


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
