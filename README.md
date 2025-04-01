# Compat analysis of removing h1 in article, aside, nav, section UA styles

1. Create a new profile in Firefox
2. Set `dom.use_counters.dump.page` to true in about:config
3. Update the paths in `check-h1-use-counter.py`
4. Run `get_reports.sql` in BigQuery (will get reports filed through Firefox broken website reporter where the pref is false)
5. Save result to `reports.csv`
6. Run `python3 check-h1-use-counter.py` (will open URLs and check if they hit the "sectioning_h1_with_no_font_size_or_margins" use counter)
7. Wait until all URLs are processed, or stop with Ctrl+C.
8. Manually check compat impact of URLs in `matched_reports.csv`
