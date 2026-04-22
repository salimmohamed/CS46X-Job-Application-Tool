"""
Multi-page job application runner.

Uses page_analysis_service (forms + buttons) and FormInteractionEngine (profile-based
form filling). Navigates across pages by clicking Apply Now / Continue / Next;
stops at Submit or when no navigation is possible.

Profile-based form filling is handled by FormInteractionEngine.fill_form_from_profile
(rules + heuristic matcher + optional LLM for unknowns).

Run logs are written to backend/logs/application_runner_<timestamp>.log for parsing
between runs (sections: [RUN], [PAGE], [BUTTONS_DIRECT], [CLICK], [ANALYSIS], [FORM], [FILL], [RESULT]).
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv
    _backend_dir = Path(__file__).resolve().parent
    for _p in (_backend_dir / ".env", _backend_dir.parent / ".env"):
        if _p.exists():
            load_dotenv(_p)
            break
except ImportError:
    pass

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from page_analysis_service import analyze_page_structure
from llm_mapping_service import FormInteractionEngine


# ---------------------------------------------------------------------------
# Visible-only HTML (so LLM sees only what's on screen, not hidden SPA form)
# ---------------------------------------------------------------------------
def _get_visible_html(driver) -> Optional[str]:
    """
    Return HTML of only visible nodes (no cache). On SPAs the first page's
    full DOM often contains the application form (hidden); this marks
    visibility on the live DOM then clones and strips hidden nodes so the
    LLM only sees the current view.
    """
    script = """
    (function() {
        function setVisible(node) {
            if (node.nodeType !== 1) return;
            var style = window.getComputedStyle(node);
            var visible = style.display !== 'none' && style.visibility !== 'hidden';
            node.setAttribute('data-visible', visible ? '1' : '0');
            for (var i = 0; i < node.childNodes.length; i++) setVisible(node.childNodes[i]);
        }
        function stripHidden(node) {
            if (node.nodeType !== 1) return;
            var i = node.childNodes.length - 1;
            while (i >= 0) {
                var c = node.childNodes[i];
                stripHidden(c);
                if (c.nodeType === 1 && c.getAttribute('data-visible') === '0') node.removeChild(c);
                i--;
            }
        }
        try {
            setVisible(document.body);
            var clone = document.body.cloneNode(true);
            stripHidden(clone);
            return clone.innerHTML;
        } catch (e) { return null; }
    })();
    """
    try:
        out = driver.execute_script(script)
        if out and len(out.strip()) > 500:
            return "<body>" + out + "</body>"
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Run log file (parseable between runs)
# ---------------------------------------------------------------------------
def _run_log_path() -> Path:
    Path(Path(__file__).resolve().parent / "logs").mkdir(parents=True, exist_ok=True)
    return Path(__file__).resolve().parent / "logs" / f"application_runner_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"


def _make_logger(log_path: Optional[Path] = None):
    path = log_path or _run_log_path()
    file_handle = open(path, "w", encoding="utf-8")
    run_start = time.time()

    def log(msg: str, section: str = "") -> None:
        now = datetime.now()
        ts = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}"
        elapsed = time.time() - run_start
        prefix = f"{ts} +{elapsed:.2f}s"
        line = f"{prefix} [{section}] {msg}" if section else f"{prefix} {msg}"
        print(line)
        file_handle.write(line + "\n")
        file_handle.flush()

    return log, path, file_handle


# Same as llm_mapping_service for button clicks
def _selector_to_by(selector: str):
    if not selector or " " in selector.strip():
        return By.CSS_SELECTOR, selector or ""
    s = selector.strip()
    if s.startswith("#") and "." not in s[1:] and "[" not in s:
        return By.ID, s[1:]
    return By.CSS_SELECTOR, s


PROFILE_FIELD_NAMES = [
    "firstname", "lastname", "first_name", "last_name", "email", "phone",
    "address_line_1", "address_line_2", "city", "state", "postal", "zip", "resume", "cv",
]

# Generic button semantics: classify by visible text only (works for any ATS).
# Buttons are chosen from Selenium-found elements; no site-specific IDs or LLM action labels.
START_KEYWORDS = ("apply now", "apply for this job", "apply for job", "apply", "begin application", "start application", "get started", "begin", "start")
NEXT_KEYWORDS = ("next", "continue", "proceed", "save and continue", "save & continue")
SUBMIT_KEYWORDS = ("submit application", "submit")
SKIP_KEYWORDS = ("back", "previous", "cancel", "return to")  # Don't use for forward navigation


def _has_profile_form(page_structure: Dict[str, Any], driver) -> bool:
    """True if this page has at least one profile-style form with visible fields."""
    forms = page_structure.get("forms") or []
    for form in forms:
        category = (form.get("category") or "").lower()
        if category in ("demographic", "eeo", "optional"):
            continue
        # LLM sometimes returns "profile|demographic|eeo|optional|other" - treat as profile if profile is in the string
        if "profile" in category or category in ("profile", "candidate_profile"):
            if _form_has_visible_fields(form, driver):
                return True
        if category == "other":
            fields = form.get("fields") or []
            if any(
                any(pf in (f.get("name") or "").lower() or pf in (f.get("label") or "").lower() for pf in PROFILE_FIELD_NAMES)
                for f in fields
            ) and _form_has_visible_fields(form, driver):
                return True
    return False


def _page_has_visible_form_fields(driver) -> bool:
    """Quick check: any visible input/select/textarea (excluding hidden/submit/button). Used to skip LLM on page 1 when it's clearly a listing."""
    try:
        for tag in ("input", "select", "textarea"):
            for el in driver.find_elements(By.TAG_NAME, tag):
                if tag == "input":
                    t = (el.get_attribute("type") or "text").lower()
                    if t in ("hidden", "submit", "button"):
                        continue
                if el.is_displayed() and el.is_enabled():
                    return True
        return False
    except Exception:
        return False


def _form_has_visible_fields(form: Dict, driver) -> bool:
    """True if at least one field has a valid, visible selector. Check first 3 only, 1s timeout."""
    fields = (form.get("fields") or [])[:3]
    for f in fields:
        sel = f.get("selector") or f.get("id") or f.get("name")
        if not sel or not isinstance(sel, str):
            continue
        by, loc = _selector_to_by(sel)
        try:
            el = WebDriverWait(driver, 1).until(EC.presence_of_element_located((by, loc)))
            if el.is_displayed() and el.is_enabled():
                return True
        except Exception:
            continue
    return False


def _button_text(btn: Dict) -> str:
    """Normalized button label for semantic matching (text or aria-label)."""
    t = (btn.get("text") or btn.get("aria_label") or "").strip()
    return (t or "").lower()


def _pick_button_by_intent(buttons: List[Dict], intent: str) -> Optional[Dict]:
    """
    Pick one button from a list (from Selenium) by semantic intent.
    intent: "start" | "next" | "submit". Uses visible text only; no LLM or site-specific IDs.
    """
    if not buttons:
        return None
    skip = set(SKIP_KEYWORDS)
    if intent == "start":
        keywords = START_KEYWORDS
        # Prefer shortest matching text so we get the actual link/button, not a container
        candidates = []
        for btn in buttons:
            if not btn.get("is_enabled", True):
                continue
            text = _button_text(btn)
            if any(s in text for s in skip):
                continue
            if any(kw in text for kw in keywords):
                candidates.append((len(text), btn))
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]
    if intent == "next":
        keywords = NEXT_KEYWORDS
        for btn in buttons:
            if not btn.get("is_enabled", True):
                continue
            text = _button_text(btn)
            if any(s in text for s in skip):
                continue
            if any(kw in text for kw in keywords):
                return btn
        return None
    if intent == "submit":
        keywords = SUBMIT_KEYWORDS
        for btn in buttons:
            text = _button_text(btn)
            if any(kw in text for kw in keywords):
                return btn
        return None
    return None


def _should_stop_from_buttons(buttons: List[Dict]) -> bool:
    """True if a submit or captcha button is present (by text). Uses direct buttons only."""
    for btn in buttons:
        text = _button_text(btn)
        if "submit" in text or "captcha" in text:
            return True
    return False


def _find_next_button(buttons: List[Dict], is_first_page: bool) -> Optional[Dict]:
    """Choose navigation button: start on first page, else next. Uses direct buttons + text semantics."""
    if is_first_page:
        return _pick_button_by_intent(buttons, "start")
    return _pick_button_by_intent(buttons, "next")


def _find_continue_after_fill(buttons: List[Dict]) -> Optional[Dict]:
    """After filling a form, find Continue/Next. Uses direct buttons + text semantics."""
    return _pick_button_by_intent(buttons, "next")


def _should_stop(direct_buttons: List[Dict], page_analysis: Dict) -> bool:
    """True if we should stop (submit/captcha by text, or page_analysis flag). Prefer direct_buttons over LLM."""
    if direct_buttons and _should_stop_from_buttons(direct_buttons):
        return True
    if page_analysis.get("has_captcha"):
        return True
    return False


def _click_button(driver, button: Dict) -> bool:
    """Click the button by selector or by text. Returns True if click succeeded."""
    selector = (button.get("selector") or "").strip()
    text = (button.get("text") or "").strip()
    if selector and selector not in ("", "css_selector", "selector"):
        by, loc = _selector_to_by(selector)
        try:
            el = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((by, loc)))
            el.click()
            return True
        except Exception:
            try:
                el = driver.find_element(by, loc)
                driver.execute_script("arguments[0].click();", el)
                return True
            except Exception:
                pass
    if text:
        try:
            xpath = f"//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]"
            for el in driver.find_elements(By.XPATH, xpath)[:10]:
                if el.is_displayed() and el.is_enabled():
                    try:
                        el.click()
                        return True
                    except Exception:
                        try:
                            driver.execute_script("arguments[0].click();", el)
                            return True
                        except Exception:
                            continue
        except Exception:
            pass
    return False


# ---------------------------------------------------------------------------
# Button detection: generic, any-application design
# - Buttons come only from Selenium (visible elements). No site-specific IDs.
# - Choice is by visible text semantics (START_KEYWORDS / NEXT_KEYWORDS / SUBMIT_KEYWORDS).
# - Same flow for all ATS: find direct_buttons once per page, then pick by intent.
# ---------------------------------------------------------------------------
def _get_element_selector(el) -> Optional[str]:
    """Stable selector for an element: #id, [name='x'], or tag.class."""
    try:
        eid = el.get_attribute("id")
        if eid:
            return f"#{eid}"
        name = el.get_attribute("name")
        if name:
            return f"[name='{name}']"
        cls = (el.get_attribute("class") or "").strip()
        if cls:
            first = cls.split()[0]
            if first:
                return f"{el.tag_name}.{first}"
        return f"{el.tag_name}[type='{el.get_attribute('type') or ''}']" if el.get_attribute("type") else el.tag_name
    except Exception:
        return None


def _element_text(el) -> str:
    """Visible text of element (and descendants). Prefer innerText."""
    try:
        t = el.text or ""
        if not t.strip():
            t = (el.get_attribute("innerText") or el.get_attribute("textContent") or "").strip()
        return (t or "").strip()
    except Exception:
        return ""


def _find_apply_now_by_text(driver) -> Optional[Dict[str, Any]]:
    """
    Find Apply Now by visible text (XPath). Prefer the actual link/button (short text),
    not a container like html/body that contains "Apply" in a long blob of text.
    """
    apply_phrases = [
        "apply now",
        "apply for this job",
        "apply for job",
        "apply",
        "begin application",
        "start application",
        "get started",
    ]
    # Exclude root containers so we never match <html> or <body> (they contain all page text).
    not_root = "[not(self::html) and not(self::body)]"
    best = None
    best_len = 999999
    for phrase in apply_phrases:
        try:
            xpath = f"//*{not_root}[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{phrase}')]"
            candidates = driver.find_elements(By.XPATH, xpath)
            for el in candidates:
                try:
                    if not el.is_displayed():
                        continue
                    text = _element_text(el)
                    if phrase not in (text or "").lower():
                        continue
                    # Prefer smallest text: the real button is "Apply Now" (~10 chars), not the whole page.
                    if len(text) >= best_len:
                        continue
                    target = el
                    tag = (el.tag_name or "").lower()
                    if tag in ("span", "div", "p", "label"):
                        try:
                            parent = el.find_element(
                                By.XPATH,
                                "(./ancestor-or-self::a | ./ancestor-or-self::button | ./ancestor-or-self::*[@role='button'])[1]"
                            )
                            if parent and parent.is_displayed():
                                target = parent
                        except Exception:
                            pass
                    selector = _get_element_selector(target)
                    if not selector or selector in ("html", "body"):
                        continue
                    best_len = len(text)
                    best = {
                        "text": _element_text(target) or text,
                        "selector": selector,
                        "tag": target.tag_name,
                        "element": target,
                        "is_displayed": True,
                        "is_enabled": target.is_enabled(),
                    }
                except Exception:
                    continue
        except Exception:
            continue
    return best


def _find_buttons_direct(driver) -> List[Dict[str, Any]]:
    """Find all clickable buttons (broad selectors, sample-style)."""
    buttons = []
    selectors = [
        "button",
        "input[type='submit']",
        "input[type='button']",
        "a[href]",
        "[role='button']",
        "[onclick]",
        "a.btn",
        "a.button",
        ".btn",
        ".button",
        "input.btn",
        "input.button",
        "[id*='apply']",
        "a[class*='apply']",
        "[class*='apply-now']",
    ]
    seen = set()
    for sel in selectors:
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                try:
                    if not el.is_displayed():
                        continue
                    selector = _get_element_selector(el)
                    if not selector or selector in seen:
                        continue
                    seen.add(selector)
                    text = _element_text(el)
                    aria = (el.get_attribute("aria-label") or "").strip()
                    buttons.append({
                        "text": text,
                        "aria_label": aria or None,
                        "selector": selector,
                        "tag": el.tag_name,
                        "element": el,
                        "is_displayed": True,
                        "is_enabled": el.is_enabled(),
                    })
                except Exception:
                    continue
        except Exception:
            continue
    return buttons


def _find_start_button(driver, direct_buttons: List[Dict]) -> Optional[Dict]:
    """
    Pick the button to start the application (Apply Now, Apply, Start, etc.).
    Generic: 1) semantic match on direct_buttons (text), 2) fallback XPath by text (shortest match).
    No site-specific IDs.
    """
    picked = _pick_button_by_intent(direct_buttons, "start")
    if picked:
        return picked
    # Fallback: find by visible text (XPath), preferring shortest so we get the link not a container
    return _find_apply_now_by_text(driver)


def _click_button_direct(driver, button: Dict) -> bool:
    """Scroll into view, then click (native, JS, or ActionChains)."""
    el = button.get("element")
    selector = button.get("selector")
    if not el and selector:
        by, loc = _selector_to_by(selector)
        try:
            el = WebDriverWait(driver, 8).until(EC.presence_of_element_located((by, loc)))
        except Exception:
            return False
    if not el:
        return False
    try:
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", el)
        time.sleep(0.15)
    except Exception:
        pass
    for attempt in range(2):
        try:
            if not el.is_displayed() or not el.is_enabled():
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                time.sleep(0.3)
            el.click()
            return True
        except Exception:
            try:
                driver.execute_script("arguments[0].click();", el)
                return True
            except Exception:
                try:
                    from selenium.webdriver.common.action_chains import ActionChains
                    ActionChains(driver).move_to_element(el).click().perform()
                    return True
                except Exception:
                    if selector and attempt == 0:
                        try:
                            by, loc = _selector_to_by(selector)
                            el = WebDriverWait(driver, 3).until(EC.presence_of_element_located((by, loc)))
                        except Exception:
                            break
                    else:
                        break
    return False


def run(
    job_url: str,
    profile_data: Dict[str, Any],
    *,
    encrypted_path: Optional[str] = None,
    headless: bool = False,
    max_pages: int = 50,
    log_fn=None,
    log_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Run multi-page application flow: navigate and fill using candidate profile.

    Args:
        job_url: Starting URL (job posting or application start).
        profile_data: Applicant dict (applicant_info or full profile). Ignored if encrypted_path is set.
        encrypted_path: If set, load and decrypt profile from this path (overrides profile_data).
        headless: Run browser headless.
        max_pages: Maximum number of pages to process.
        log_fn: Optional callback(message: str) for logging.

    Returns:
        Dict with keys: success, pages_processed, fields_filled, status (completed|submit|manual_review|error),
        error (if status==error), results (last fill results).
    """
    log_file_handle = None
    if log_fn is not None:
        log = log_fn
    else:
        _log, _log_path, log_file_handle = _make_logger(log_path)
        def log(msg: str, section: str = "") -> None:
            _log(msg, section) if section else _log(msg)
        log(f"job_url={job_url} headless={headless} max_pages={max_pages}", "RUN")
        log(str(_log_path), "RUN")

    visited_urls: List[str] = []
    total_filled = 0
    last_fill_results: List[Dict] = []
    status = "completed"
    profile = profile_data

    # In headless, elements are often not considered "displayed"; allow presence-only verify
    if headless and not os.environ.get("RELAX_VERIFY"):
        os.environ["RELAX_VERIFY"] = "1"
        log("RELAX_VERIFY=1 (headless)", "RUN")

    engine = FormInteractionEngine(headless=headless)
    try:
        if encrypted_path:
            with open(encrypted_path) as f:
                enc = json.load(f)
            dec = engine.getDecryptedData(enc)
            if not dec:
                return {"success": False, "status": "error", "error": "Failed to decrypt profile", "pages_processed": 0, "fields_filled": 0, "results": []}
            profile = dec.get("applicant_info") or dec

        log(f"Navigating to {job_url}", "RUN")
        engine.driver.get(job_url)
        time.sleep(1)

        for page_num in range(1, max_pages + 1):
            current_url = engine.driver.current_url
            if current_url not in visited_urls:
                visited_urls.append(current_url)
            elif page_num > 1 and current_url != visited_urls[-1]:
                log("Navigated back to a previous URL (loop); stopping.", "PAGE")
                status = "manual_review"
                break

            log(f"url={current_url}", "PAGE")
            log(f"page_num={page_num}", "PAGE")

            # Wait for page content (generic: form, inputs, or links)
            try:
                WebDriverWait(engine.driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "form, input, select, textarea, button, a[href]"))
                )
            except Exception:
                pass
            time.sleep(0.2)
            html = engine.driver.page_source
            page_structure = None
            skip_llm_page_1 = False
            skip_llm_page_2_plus = False
            page_live_fields = None  # Reuse when we skipped LLM on page 2+ to avoid second get_fields()

            # Page 1: if no visible form fields (job listing), skip LLM and go straight to button detection.
            if page_num == 1:
                visible_html = _get_visible_html(engine.driver)
                if visible_html:
                    html = visible_html
                    log("Using visible-only HTML for analysis (page 1).", "ANALYSIS")
                if not _page_has_visible_form_fields(engine.driver):
                    skip_llm_page_1 = True
                    log("No visible form fields on page 1; skipping LLM (use button flow).", "ANALYSIS")
                    page_structure = {"forms": [], "buttons": [], "has_captcha": False, "is_login_page": False}

            # Page 2+: if we have live fields (form page), skip LLM and use get_fields() only.
            if page_num > 1 and not skip_llm_page_1:
                page_live_fields = engine.get_fields()
                if page_live_fields:
                    skip_llm_page_2_plus = True
                    log(f"Skipping LLM on page {page_num}; using {len(page_live_fields)} live field(s).", "ANALYSIS")
                    page_structure = {
                        "forms": [{"id": "live", "category": "profile", "fields": [
                            {"selector": f.get("selector") or f.get("id"), "name": f.get("name"), "label": f.get("label_text"), "type": f.get("type") or "text", "options": f.get("options") or [], "option_pairs": f.get("option_pairs") or []}
                            for f in page_live_fields if (f.get("selector") or f.get("id"))
                        ]}],
                        "buttons": [],
                        "has_captcha": False,
                        "is_login_page": False,
                    }

            if page_structure is None:
                log("LLM page_analysis start", "TIMING")
                t0 = time.time()
                page_structure = analyze_page_structure(html, current_url)
                page_analysis_sec = time.time() - t0
                log(f"LLM page_analysis done duration_sec={page_analysis_sec:.2f}", "TIMING")

            forms = page_structure.get("forms") or []
            buttons = page_structure.get("buttons") or []
            log(f"forms_count={len(forms)} buttons_llm_count={len(buttons)}", "ANALYSIS")
            for i, b in enumerate(buttons[:10]):
                log(f"  llm_button_{i+1} text={b.get('text')!r} action={b.get('action')} selector={b.get('selector')!r}", "ANALYSIS")

            # Fallback: if LLM returned no forms but page has inputs (e.g. JazzHR), use live DOM.
            # Skip on page 1 when we already skipped LLM (listing page) to avoid slow get_fields().
            if not forms and not skip_llm_page_1:
                live_fields = engine.get_fields()
                if live_fields:
                    log(f"LLM returned 0 forms; using {len(live_fields)} live field(s) from page.")
                    page_structure = {
                        "forms": [{"id": "live", "category": "profile", "fields": [
                            {"selector": f.get("selector") or f.get("id"), "name": f.get("name"), "label": f.get("label_text"), "type": f.get("type") or "text", "options": f.get("options") or [], "option_pairs": f.get("option_pairs") or []}
                            for f in live_fields if (f.get("selector") or f.get("id"))
                        ]}],
                        "buttons": page_structure.get("buttons") or [],
                        "has_captcha": False,
                        "is_login_page": False,
                    }
                    forms = page_structure.get("forms") or []

            # Only treat as profile form if at least one form has *visible* fields (no name-only fallback:
            # on first page the form may be in the DOM but not visible; we must click Apply first).
            has_profile = _has_profile_form(page_structure, engine.driver)
            if not has_profile and forms:
                has_profile = any(_form_has_visible_fields(f, engine.driver) for f in forms)

            # Single source of truth for buttons: Selenium (visible only). Used for all navigation decisions.
            direct_buttons = _find_buttons_direct(engine.driver)
            log(f"count={len(direct_buttons)}", "BUTTONS_DIRECT")
            for i, b in enumerate(direct_buttons[:15]):
                log(f"  direct_{i+1} text={b.get('text')!r} selector={b.get('selector')!r} tag={b.get('tag')}", "BUTTONS_DIRECT")

            # On first page without visible form: click Start/Apply (generic text semantics).
            if page_num == 1 and not has_profile:
                apply_btn = _find_start_button(engine.driver, direct_buttons)
                if apply_btn:
                    btn_text = apply_btn.get("text") or ""
                    btn_sel = apply_btn.get("selector") or ""
                    ok = _click_button_direct(engine.driver, apply_btn)
                    log(f"text={btn_text!r} selector={btn_sel!r} success={ok}", "CLICK")
                    if ok:
                        time.sleep(1)
                        continue
                else:
                    log("no_apply_button_found", "CLICK")
                log("No profile form and could not click Apply; stopping.", "PAGE")
                status = "manual_review"
                break

            # Stop for captcha/login only when we're not on the first-page landing (we already tried Apply above)
            if not has_profile and (page_structure.get("has_captcha") or page_structure.get("is_login_page")):
                log("Captcha or login page; stopping for manual review.", "PAGE")
                status = "manual_review"
                break

            log(f"has_profile={has_profile}", "FORM")
            if has_profile:
                n_fields = sum(len(f.get("fields") or []) for f in forms)
                log(f"Profile form detected ({n_fields} field(s)); filling from candidate profile.")
                # Reuse page_live_fields when we skipped LLM on this page (avoid second get_fields()).
                live_fields = page_live_fields if page_live_fields is not None else engine.get_fields()
                if live_fields:
                    for i, f in enumerate(live_fields[:35]):
                        nm = f.get("name") or f.get("id") or "?"
                        lb = (f.get("label_text") or "")[:60]
                        log(f"  field_{i+1} name={nm!r} label={lb!r} type={f.get('type','')}", "FIELDS")
                if live_fields:
                    if page_live_fields is None:
                        live_structure = {
                            "forms": [{
                                "id": "live",
                                "category": "profile",
                                "fields": [
                                    {"selector": f.get("selector") or f.get("id"), "name": f.get("name"), "label": f.get("label_text"), "type": f.get("type") or "text", "options": f.get("options") or [], "option_pairs": f.get("option_pairs") or []}
                                    for f in live_fields if (f.get("selector") or f.get("id"))
                                ]
                            }]
                        }
                        engine.set_page_structure(live_structure)
                    # else: engine already has found_elements from get_fields() in skip block
                else:
                    engine.set_page_structure(page_structure)
                def _log_timing(ev: str, **kw):
                    parts = [ev] + [f"{k}={v}" for k, v in kw.items()]
                    log(" ".join(parts), "TIMING")
                results = engine.fill_form_from_profile(profile, page_structure=None, log_timing=_log_timing)
                last_fill_results = results
                n_ok = sum(1 for r in results if r.get("status") == "SUCCESS")
                n_fail = sum(1 for r in results if r.get("status") == "FAILED")
                total_filled += n_ok
                log(f"success={n_ok} failed={n_fail} total_results={len(results)}", "FILL")
                log(f"Filled {n_ok} field(s) on this page.")
                if results:
                    for r in results[:20]:
                        line = (
                            f"  {r.get('field', '?')}: {r.get('status', '')} "
                            f"{r.get('error', r.get('note', ''))}"
                        )
                        if r.get("source"):
                            line += f" source={r.get('source')!r}"
                        if r.get("option_index") is not None:
                            line += f" option_index={r.get('option_index')}"
                        if r.get("value_tried") is not None:
                            line += f" value_tried={r.get('value_tried')!r}"
                        if r.get("options_available") is not None:
                            opts = r.get("options_available")
                            short = opts[:5] if len(opts) > 5 else opts
                            line += f" options=[{', '.join(str(x) for x in short)}]"
                        log(line, "FILL")
                if n_ok == 0 and live_fields:
                    log(f"(no fill results; engine had {len(live_fields)} live fields)", "FILL")

                cont_btn = _find_continue_after_fill(direct_buttons)
                if cont_btn:
                    log(f"Clicking continue: {cont_btn.get('text', '')}")
                    if _click_button_direct(engine.driver, cont_btn):
                        time.sleep(0.5)
                        continue
                if _should_stop(direct_buttons, page_structure):
                    log("Submit button present; stopping before final submit.")
                    status = "submit"
                    break
                log("No continue button found after fill; stopping for manual review.")
                status = "manual_review"
                break

            is_first = page_num == 1
            if _should_stop(direct_buttons, page_structure):
                log("Submit/captcha detected; stopping.")
                status = "submit"
                break

            next_btn = _find_next_button(direct_buttons, is_first_page=is_first)
            if not next_btn:
                log("No navigation button found; stopping for manual review.")
                status = "manual_review"
                break

            log(f"Clicking: {next_btn.get('text', '')}")
            if not _click_button_direct(engine.driver, next_btn):
                log("Click failed; stopping.")
                status = "error"
                break
            time.sleep(0.5)

        out = {
            "success": status in ("completed", "submit", "manual_review"),
            "status": status,
            "pages_processed": len(visited_urls),
            "fields_filled": total_filled,
            "results": last_fill_results,
        }
        log(f"status={status} pages_processed={len(visited_urls)} fields_filled={total_filled}", "RESULT")
        return out
    except Exception as e:
        log(f"Error: {e}", "RESULT")
        return {
            "success": False,
            "status": "error",
            "error": str(e),
            "pages_processed": len(visited_urls),
            "fields_filled": total_filled,
            "results": last_fill_results,
        }
    finally:
        # Log and decide browser before closing the log file (log() writes to it).
        keep_open_env = os.environ.get("KEEP_BROWSER_OPEN", "").lower()
        keep_open = keep_open_env in ("1", "true", "yes") or (keep_open_env == "" and not headless)
        if keep_open:
            log("Browser left open. Close manually or set KEEP_BROWSER_OPEN=0 to close on exit.", "RUN")
            if log_file_handle:
                try:
                    log_file_handle.close()
                except Exception:
                    pass
                log_file_handle = None
            try:
                input("Press Enter to close the browser and exit...")
            except (EOFError, KeyboardInterrupt):
                pass
            try:
                engine.driver.quit()
            except Exception:
                pass
        else:
            engine.driver.quit()
        if log_file_handle:
            try:
                log_file_handle.close()
            except Exception:
                pass


def main():
    """CLI entry: JOB_URL and optional ENCRYPTED_PROFILE."""
    import os
    import json
    job_url = os.environ.get("JOB_URL")
    if not job_url:
        print("Set JOB_URL to the job application URL.")
        return
    encrypted = os.environ.get("ENCRYPTED_PROFILE", "backend/encrypted_profile.json")
    profile_data = {}
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(encrypted):
        encrypted = None
        # Fallback 1: backend/profile.json (saved by web app POST /profile)
        profile_json = os.path.join(backend_dir, "profile.json")
        if os.path.exists(profile_json):
            try:
                with open(profile_json) as f:
                    data = json.load(f)
                profile_data = data.get("applicant_info", data)
            except Exception:
                profile_data = {}
        # Fallback 2: sample fixture
        if not profile_data:
            sample = os.path.join(backend_dir, "tests", "fixtures", "sample.json")
            if os.path.exists(sample):
                with open(sample) as f:
                    data = json.load(f)
                profile_data = data.get("applicant_info", data)
    headless = os.environ.get("HEADLESS", "").lower() in ("1", "true", "yes")
    result = run(job_url, profile_data, encrypted_path=encrypted, headless=headless)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
