# Compare HTML snapshot to analysis result (form controls vs fields).
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Set, Tuple


def _normalize_selector_to_id_or_name(selector: str) -> str:
    if not selector or not isinstance(selector, str):
        return ""
    s = selector.strip()
    if s.startswith("#"):
        return s[1:].strip()
    m = re.match(r"\[name\s*=\s*['\"]([^'\"]+)['\"]\]", s, re.I)
    if m:
        return m.group(1).strip()
    return s


def parse_html_form_controls(html: str) -> List[Dict[str, Any]]:
    controls = []

    class FormControlParser(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag not in ("input", "select", "textarea"):
                return
            ad = dict(attrs)
            typ = (ad.get("type") or "text").lower()
            if tag == "input" and typ in ("hidden", "submit", "button", "image"):
                return
            name = ad.get("name") or ""
            id_ = ad.get("id") or ""
            controls.append({
                "tag": tag,
                "id": id_,
                "name": name,
                "type": typ,
            })

    try:
        parser = FormControlParser()
        parser.feed(html)
    except Exception:
        pass
    return controls


def get_analysis_field_identifiers(page_structure: Dict[str, Any]) -> Set[Tuple[str, str]]:
    out = set()
    for form in page_structure.get("forms") or []:
        for f in form.get("fields") or []:
            sel = f.get("selector") or f.get("name") or f.get("id") or ""
            key = _normalize_selector_to_id_or_name(sel)
            if key:
                out.add((key.lower(), sel))
    return out


def controls_to_identifiers(controls: List[Dict[str, Any]]) -> Set[Tuple[str, str]]:
    out = set()
    for c in controls:
        key = (c.get("id") or c.get("name") or "").strip()
        if not key:
            continue
        if c.get("id"):
            out.add((c["id"].lower(), f"#{c['id']}"))
        else:
            out.add((c["name"].lower(), f"[name='{c['name']}']"))
    return out


def compare_and_report(html_sent: str, page_structure: Dict[str, Any]) -> None:
    controls = parse_html_form_controls(html_sent)
    html_keys = controls_to_identifiers(controls)
    analysis_pairs = get_analysis_field_identifiers(page_structure)
    analysis_keys = {k for k, _ in analysis_pairs}

    html_key_set = {k for k, _ in html_keys}
    analysis_key_set = analysis_keys

    only_in_html = html_key_set - analysis_key_set
    only_in_analysis = analysis_key_set - html_key_set
    matched = html_key_set & analysis_key_set

    print("\n--- HTML vs analysis ---")
    print(f"HTML controls: {len(controls)}")
    print(f"Analysis fields: {sum(len(f.get('fields') or []) for f in (page_structure.get('forms') or []))}")
    print("Matched:", len(matched))
    if only_in_html:
        intentional = {k for k in only_in_html if "recaptcha" in k or "xml-value" in k or "resumetext" in k}
        missing = only_in_html - intentional
        print("HTML only:", len(only_in_html), sorted(missing)[:15] if missing else [], "(skip: captcha/hidden)" if intentional else "")
    else:
        print("HTML only: 0")
    if only_in_analysis:
        print("Analysis only:", len(only_in_analysis), sorted(only_in_analysis)[:10])
    else:
        print("Analysis only: 0")
