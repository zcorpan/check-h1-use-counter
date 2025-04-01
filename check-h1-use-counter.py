import subprocess
import csv
import os
import sys
import psutil
import time
import signal

FIREFOX_PATH = "/Applications/Firefox Nightly.app/Contents/MacOS/firefox"
PROFILE_PATH = "/Users/simonpieters/Library/Caches/Firefox/Profiles/atk2s0ma.Test-1743498816747"

INPUT_CSV = "reports.csv"
OUTPUT_CSV = "matched_reports.csv"
CACHE_FILE = "checked_urls.txt"

TARGET_COUNTER = "sectioning_h1_with_no_font_size_or_margins"
BATCH_SIZE = 10
LOAD_WAIT = 20
KILL_WAIT = 20
PAUSE_BETWEEN_BATCHES = 5


def firefox_is_running():
    for proc in psutil.process_iter(attrs=["name", "cmdline"]):
        name = proc.info["name"]
        if name and "firefox" in name.lower():
            return True
        cmdline = " ".join(proc.info.get("cmdline") or [])
        if "firefox" in cmdline.lower():
            return True
    return False


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


def launch_firefox_batch(urls):
    cmd = [
        FIREFOX_PATH,
        "--no-remote",
        "--new-instance",
        "--profile", PROFILE_PATH,
    ] + urls

    print(f"🚀 Launching Firefox with {len(urls)} URLs...")
    proc = subprocess.Popen(cmd, stderr=subprocess.PIPE)
    return proc


def wait_and_terminate(proc):
    print(f"⏳ Waiting {LOAD_WAIT} seconds for pages to load...")
    time.sleep(LOAD_WAIT)

    print(f"🔔 Attempting graceful shutdown (SIGTERM)...")
    proc.terminate()

    try:
        proc.wait(timeout=KILL_WAIT)
        print("✅ Firefox closed gracefully.")
    except subprocess.TimeoutExpired:
        print("⚠️  Graceful shutdown failed. Forcing close...")
        proc.kill()
        proc.wait()

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
    with open(output_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        if f.tell() == 0:
            writer.writeheader()
        for row in rows:
            if row["url"] in matched_urls:
                writer.writerow(row)
    print(f"✅ Appended {len(matched_urls)} matching reports to {output_path}")


def main():
    if firefox_is_running():
        print("🚫 Firefox is already running. Please close it before running this script.")
        sys.exit(1)

    all_rows = read_reports(INPUT_CSV)
    cached_urls = load_cache(CACHE_FILE)
    fresh_rows = deduplicate_and_filter(all_rows, cached_urls)

    if not fresh_rows:
        print("✅ No new URLs to check. You're up to date.")
        return

    print(f"🔍 {len(fresh_rows)} fresh URLs to process in batches of {BATCH_SIZE}...\n")

    try:
        for i in range(0, len(fresh_rows), BATCH_SIZE):
            batch_rows = fresh_rows[i:i + BATCH_SIZE]
            urls = [row["url"] for row in batch_rows]

            proc = launch_firefox_batch(urls)
            log_output = wait_and_terminate(proc)
            matched_urls = extract_matching_urls(log_output, TARGET_COUNTER)

            write_matched_rows(batch_rows, matched_urls, OUTPUT_CSV)

            # Save cache after every batch
            cached_urls.update(urls)
            save_cache(CACHE_FILE, cached_urls)
            print(f"🧠 Cache saved after batch of {len(urls)} URLs\n")

            # Wait before starting next batch
            if i + BATCH_SIZE < len(fresh_rows):
                print(f"⏸ Waiting {PAUSE_BETWEEN_BATCHES} seconds before next batch...\n")
                time.sleep(PAUSE_BETWEEN_BATCHES)

    except KeyboardInterrupt:
        print("\n🛑 Script interrupted by user. Exiting cleanly.")
        save_cache(CACHE_FILE, cached_urls)
        print("💾 Final cache saved.")


if __name__ == "__main__":
    main()
