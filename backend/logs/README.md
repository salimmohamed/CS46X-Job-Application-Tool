# Application runner logs

Each run writes a timestamped log file: `application_runner_YYYYMMDD_HHMMSS.log`.

## Line format

Every line starts with:

- **Timestamp**: `YYYY-MM-DDTHH:MM:SS.mmm` (ISO-style)
- **Elapsed**: `+XX.XXs` (seconds since run start)

Example: `2025-03-09T14:30:01.234 +5.67s [PAGE] url=...` means the event occurred at 14:30:01.234 and 5.67 seconds after the run started. Use elapsed to analyze where time is spent and to correlate with `[TIMING]` LLM response times.

## Sections (for parsing between runs)

| Section | Content |
|--------|--------|
| `[RUN]` | job_url, headless, max_pages, log file path; KEEP_BROWSER_OPEN message if set |
| `[TIMING]` | LLM calls: `LLM page_analysis start` / `LLM page_analysis done duration_sec=X.XX`; `llm_map_fields_start` / `llm_map_fields_done duration_sec=X.XX` |
| `[PAGE]` | url, page_num |
| `[ANALYSIS]` | forms_count, buttons_llm_count, then `llm_button_N text=... action=... selector=...` |
| `[BUTTONS_DIRECT]` | count=..., then `direct_N text=... selector=...` |
| `[CLICK]` | text=..., selector=..., success=True/False |
| `[FORM]` | has_profile=True/False |
| `[FIELDS]` | field_N name=... label=... type=... (all detected fields before fill; use to verify eligibility/visa/relocation are detected) |
| `[FILL]` | success=..., failed=..., per-field status; source=rules/heuristic/llm; option_index for radios; value_tried=... and options=[...] for FAILED/SKIPPED |
| `[RESULT]` | status=..., pages_processed=..., fields_filled=... |

## Example (with timestamps)

```
2025-03-09T14:30:00.000 +0.00s [RUN] job_url=https://... headless=False max_pages=50
2025-03-09T14:30:01.100 +1.10s [RUN] C:\...\application_runner_20250309_143000.log
2025-03-09T14:30:01.102 +1.10s [PAGE] url=https://... page_num=1
2025-03-09T14:30:01.105 +1.11s [TIMING] LLM page_analysis start
2025-03-09T14:30:08.234 +7.13s [TIMING] LLM page_analysis done duration_sec=7.13
2025-03-09T14:30:08.235 +7.13s [ANALYSIS] forms_count=1 buttons_llm_count=3
...
2025-03-09T14:30:45.000 +43.90s [RESULT] status=submit pages_processed=2 fields_filled=20
```

## Keep browser open

Set `KEEP_BROWSER_OPEN=1` (or `true`/`yes`) to leave the browser window open after the run so you can inspect the page. The log will note that the browser was left open. Close it manually or run again without the variable.

## First-page button

If the first page has no application form, the runner uses **direct Selenium button detection** (like the `job_application_automation` sample): finds buttons by `button`, `input[type=submit]`, `a[href]`, `[role=button]`, then picks one with "apply" / "start" / "begin" in the text and clicks it. Check `[BUTTONS_DIRECT]` and `[CLICK]` to see what was found and whether the click succeeded.
