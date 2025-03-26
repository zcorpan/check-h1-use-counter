import subprocess
import csv
import os

FIREFOX_PATH = "/Applications/Firefox Nightly.app/Contents/MacOS/firefox"
PROFILE_PATH = "/Users/simonpieters/Library/Application Support/Firefox/Profiles/6jgwlpvt.Test"

INPUT_CSV = "reports.csv"
OUTPUT_CSV = "matched_reports.csv"
CACHE_FILE = "checked_urls.txt"

TARGET_COUNTER = "sectioning_h1_with_no_font_size_or_margins"

def read_reports(csv_path):
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows

def load_cache(cache_path):
    if not os.path.exists(cache_path):
        return set()
    with open(cache_path) as f:
        return set(line.strip() for line in f)

def save_cache(cache_path, url_set):
    with open(cache_path, "w") as f:
        for url in sorted(url_set):
            f.write(url + "\n")

def deduplicate_and_filter(rows, already_checked):
    seen = set()
    fresh_rows = []
    for row in rows:
        url = row["url"]
        if url in seen or url in already_checked:
            continue
        seen.add(url)
        fresh_rows.append(row)
    return fresh_rows

def launch_firefox(urls):
    cmd = [
        FIREFOX_PATH,
        "--no-remote",
        "--profile", PROFILE_PATH,
    ] + urls

    print(f"Launching Firefox with {len(urls)} new tabs...")
    print("Close Firefox manually to complete analysis.\n")

    proc = subprocess.Popen(cmd, stderr=subprocess.PIPE)
    _, stderr = proc.communicate()
    return stderr.decode("utf-8")

def extract_matching_urls(log_text, counter_name):
    matched_urls = set()
    for line in log_text.splitlines():
        if f"USE_COUNTER_PAGE: {counter_name}" in line:
            parts = line.split(" - ")
            if len(parts) == 2:
                url = parts[1].strip()
                matched_urls.add(url)
    return matched_urls

def write_matched_rows(rows, matched_urls, output_path):
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        for row in rows:
            if row["url"] in matched_urls:
                writer.writerow(row)
    print(f"Saved {len(matched_urls)} matching reports to {output_path}")

def main():
    all_rows = read_reports(INPUT_CSV)
    cached_urls = load_cache(CACHE_FILE)
    fresh_rows = deduplicate_and_filter(all_rows, cached_urls)

    if not fresh_rows:
        print("✅ No new URLs to check. You're up to date.")
        return

    urls_to_check = [row["url"] for row in fresh_rows]
    log_output = launch_firefox(urls_to_check)
    matched_urls = extract_matching_urls(log_output, TARGET_COUNTER)
    write_matched_rows(fresh_rows, matched_urls, OUTPUT_CSV)

    # Update cache
    new_checked = cached_urls.union(urls_to_check)
    save_cache(CACHE_FILE, new_checked)
    print(f"🔁 Cache updated: {len(new_checked)} total URLs checked.")

if __name__ == "__main__":
    main()
