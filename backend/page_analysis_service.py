# Live page HTML -> forms, fields, buttons via OpenAI. Truncates form regions.
import json
import os
import re
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

DEFAULT_MODEL = "gpt-4o-mini"
MAX_HTML_CHARS = 80000
SAFE_DEFAULT = {
    "forms": [],
    "buttons": [],
    "is_account_page": False,
    "is_login_page": False,
    "has_captcha": False,
    "validation_errors": [],
}


def _extract_form_sections(html: str) -> str:
    try:
        out_parts = []
        pos = 0
        while True:
            start = html.find("<form", pos)
            if start == -1:
                break
            end_tag = html.find(">", start)
            if end_tag == -1:
                break
            depth = 1
            pos = end_tag + 1
            close = -1
            while depth > 0 and pos < len(html):
                next_open = html.find("<form", pos)
                next_close = html.find("</form>", pos)
                if next_close == -1:
                    break
                if next_open != -1 and next_open < next_close:
                    depth += 1
                    pos = next_open + 5
                else:
                    depth -= 1
                    if depth == 0:
                        close = next_close
                    pos = next_close + 7
            end = close + len("</form>") if close != -1 else min(start + 80000, len(html))
            section_start = max(0, start - 1500)
            section_end = min(end + 3000, len(html))
            chunk = html[section_start:section_end]
            if chunk and chunk not in str(out_parts):
                out_parts.append(chunk)
            pos = end if close != -1 else pos
            if pos >= len(html):
                break
        if out_parts:
            combined = "\n\n<!-- next form -->\n\n".join(out_parts)
            return combined[:MAX_HTML_CHARS] if len(combined) > MAX_HTML_CHARS else combined
        return None
    except Exception:
        return None


def _fallback_html(html: str) -> str:
    idx = html.find("<body")
    if idx != -1:
        return html[idx : idx + MAX_HTML_CHARS]
    return html[:MAX_HTML_CHARS]


def get_html_for_analysis(page_html: str) -> str:
    if not page_html:
        return ""
    html_content = _extract_form_sections(page_html)
    if not html_content:
        html_content = _fallback_html(page_html)
    return html_content


def analyze_page_structure(
    page_html: str, current_url: str, debug_snapshot: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    if not page_html or not current_url:
        return dict(SAFE_DEFAULT)

    html_content = _extract_form_sections(page_html)
    if not html_content:
        html_content = _fallback_html(page_html)
    if debug_snapshot is not None:
        debug_snapshot["html_sent"] = html_content
        debug_snapshot["html_len"] = len(html_content)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or not OpenAI:
        return dict(SAFE_DEFAULT)

    system = """You are a web automation expert. Analyze HTML and return ONLY valid JSON.
List EVERY input, select, and textarea. Do not skip or summarize; include every field you see.
Include EEOC/EEO fields: disability (radio or select), veteran (radio), disability date, disability signature, gender, race.
Forms: category profile = candidate info (name, email, phone, address, resume). category demographic|eeo|optional = still list their fields. category other = evaluate by field names.
Fields: real CSS selectors from HTML - #id, [name='x'], .class. For select/radio list all options. Types: text|email|tel|select|checkbox|radio|textarea|file|date|number.
Buttons: action apply_now|start = Apply/Begin/Apply Now; next = Continue/Next; previous = Back; submit = final Submit (should_click false); captcha = challenge.
Extract selector from actual id/name/class. No placeholder text."""

    user = f"""Job application page. URL: {current_url}

HTML:
{html_content}

Return JSON only (no markdown):
{{
  "forms": [{{ "id": "...", "category": "profile|demographic|eeo|optional|other", "fields": [{{ "name": "...", "label": "...", "type": "text|email|tel|select|checkbox|radio|textarea|file|date|number", "required": false, "selector": "css_selector", "options": [] }}] }}],
  "buttons": [{{ "text": "...", "selector": "css_selector", "action": "apply_now|next|previous|submit|captcha|other", "should_click": true }}],
  "is_account_page": false,
  "is_login_page": false,
  "has_captcha": false,
  "validation_errors": []
}}"""

    try:
        client = OpenAI(api_key=api_key)
        model = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=4000,
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            return dict(SAFE_DEFAULT)
        if "```" in text:
            match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text)
            if match:
                text = match.group(1)
        data = json.loads(text)
        for key in SAFE_DEFAULT:
            if key not in data:
                data[key] = SAFE_DEFAULT[key]
        nf = len(data.get("forms") or [])
        nb = len(data.get("buttons") or [])
        if nf == 0 and nb == 0:
            print("(Empty forms/buttons; len=%d)" % len(html_content))
        return data
    except json.JSONDecodeError as e:
        print("Analysis JSON error:", str(e)[:80])
        return dict(SAFE_DEFAULT)
    except Exception as e:
        print("Analysis error:", str(e)[:80])
        return dict(SAFE_DEFAULT)
