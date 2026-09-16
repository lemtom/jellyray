#!/usr/bin/env python3

import sys
from pathlib import Path
from html.parser import HTMLParser
import argparse
import re

class BluRayTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.movies = []
        self.current_row = []
        self.in_tbody = False
        self.in_td = False
        self.current_cell = ""
    
    def handle_starttag(self, tag, attrs):
        if tag == "tbody":
            self.in_tbody = True
        elif tag == "td" and self.in_tbody:
            self.in_td = True
            self.current_cell = ""
    
    def handle_endtag(self, tag):
        if tag == "td" and self.in_td:
            self.in_td = False
            self.current_cell = self.current_cell.strip()
            self.current_row.append(self.current_cell)
        elif tag == "tr" and self.in_tbody and self.current_row:
            if len(self.current_row) >= 2:
                title = self.current_row[0].strip()
                media = self.current_row[1].strip()
                if title and media:
                    self.movies.append((title, media))
            self.current_row = []
    
    def handle_data(self, data):
        if self.in_td:
            self.current_cell += data
    
    def get_movies(self):
        """Return list of (title, media) tuples."""
        return self.movies


def is_tv_series(media_string):
    return "Season" in media_string or "TV Series" in media_string

def load_manual_exclusions(script_dir):
    exclusion_file = Path(script_dir) / "collections.txt"
    excluded = set()
    
    if not exclusion_file.exists():
        return excluded
    
    try:
        with open(exclusion_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    excluded.add(line)
        return excluded
    except Exception as e:
        print(f"Warning: Could not read collections.txt: {e}", file=sys.stderr)
        return excluded


def is_collection(title):
    """
    Check for multi-year date range.
    """
    return bool(re.search(r'\(\d{4}-(\d{4})?\)\s*$', title))

def get_preferred_format(media_string):
    media_string = media_string.strip()
    
    # Check for multiple entries
    formats = [fmt.strip() for fmt in media_string.split(",")]
    
    # Remove anything with Season in it (= TV)
    formats = [fmt for fmt in formats if "Season" not in fmt]
    
    if not formats:
        return None
    
    for fmt in formats:
        if "Blu-ray" in fmt or "Blu-Ray" in fmt:
            return "bluray"
    
    for fmt in formats:
        if "DVD" in fmt:
            return "dvd"
    
    # Return first available
    first = formats[0]
    if "blu" in first.lower():
        return "bluray"
    elif "dvd" in first.lower():
        return "dvd"
    
    return None

def parse_html_file(html_content, manual_exclusions=None):
    """
    Parse HTML tbody
    Returns tuple: (valid_movies, filtered_entries)
    """
    if manual_exclusions is None:
        manual_exclusions = set()
    
    parser = BluRayTableParser()
    parser.feed(html_content)
    
    valid_movies = []
    filtered_entries = []
    
    for title, media in parser.get_movies():
        if not title or not media:
            filtered_entries.append((title or "[empty]", "Empty entry"))
            continue
        
        if title in manual_exclusions:
            filtered_entries.append((title, "Manual exclusion (collections.txt)"))
            continue
        
        if is_tv_series(media):
            filtered_entries.append((title, "TV Series"))
            continue
        
        if is_collection(title):
            filtered_entries.append((title, "Collection (date range detected)"))
            continue
        
        fmt = get_preferred_format(media)
        if fmt:
            valid_movies.append((title, fmt))
        else:
            filtered_entries.append((title, "No valid media format"))
    
    return valid_movies, filtered_entries


def sanitize_filename(filename):
    filename = filename.replace("/", "-")

    # Remove dots at start (makes files hidden on Linux)
    filename = filename.lstrip('.')

    return filename.strip() or "Untitled"


def create_placeholder_structure(base_path, title, format_type):
    """
    Returns True if created, False if it already exists.
    """
    base_path = Path(base_path)
    safe_title = sanitize_filename(title)
    movie_folder = base_path / safe_title
    placeholder_file = movie_folder / f"{safe_title}.{format_type}.disc"
    
    if movie_folder.exists():
        return False
    
    try:
        movie_folder.mkdir(parents=True, exist_ok=True)
        placeholder_file.touch()
        return True
    except Exception as e:
        print(f"Error creating {placeholder_file}: {e}", file=sys.stderr)
        return False


def find_orphaned_folders(base_path, existing_titles):
    """
    Returns list of folder names (accounting for filename sanitization)
    """
    base_path = Path(base_path)
    
    if not base_path.exists():
        return []
    
    # Create sanitized versions for comparison
    sanitized_existing = {sanitize_filename(title): title for title in existing_titles}
    
    orphaned = []
    for item in base_path.iterdir():
        if item.is_dir() and item.name not in sanitized_existing:
            orphaned.append(item.name)
    
    return orphaned

def process_movies(movies, library_path, dry_run=False):
    """Handle dry-run and actual file/folder creation logic."""
    created_count = 0
    skipped_count = 0
    existing_titles = set()

    for title, format_type in movies:
        existing_titles.add(title)
        safe_title = sanitize_filename(title)
        movie_folder = library_path / safe_title

        if dry_run:
            if movie_folder.exists():
                print(f"- Skipped (exists): {safe_title}")
                skipped_count += 1
            else:
                print(f"[DRY RUN] Would create: {safe_title}/{safe_title}.{format_type}.disc")
                created_count += 1
        else:
            if create_placeholder_structure(library_path, title, format_type):
                print(f"Created: {safe_title}/{safe_title}.{format_type}.disc")
                created_count += 1
            else:
                print(f"- Skipped (exists): {safe_title}")
                skipped_count += 1

    return existing_titles, created_count, skipped_count


def write_filtered_report(library_path, source_file, filtered_entries):
    """Write the summary report for skipped items using Path methods."""
    library_path.mkdir(parents=True, exist_ok=True)
    report_path = library_path / "filtered_entries.txt"

    lines = [
        "Filtered Entries Report",
        "=" * 80 + "\n",
        f"Total filtered: {len(filtered_entries)}",
        f"Generated from: {Path(source_file).name}\n",
        "-" * 80 + "\n"
    ]

    for title, reason in sorted(filtered_entries):
        lines.append(f"{title}\n  Reason: {reason}\n")

    try:
        report_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Filtered entries report written to: {report_path.name}")
    except Exception as e:
        print(f"Could not write filtered entries report: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(
        prog="jellyray",
        description="Jellyray: Sync Jellyfin placeholder library with Blu-Ray.com collection"
    )
    parser.add_argument("html_file", help="HTML file containing your Blu-Ray.com collection tbody")
    parser.add_argument("library_path", help="Path to your Jellyfin placeholder library folder")
    parser.add_argument("--check-orphans", action="store_true", help="Check for folders no longer in the collection")
    parser.add_argument("--dry-run", action="store_true", help="Preview without actually creating files")

    args = parser.parse_args()
    script_dir = Path(__file__).parent

    manual_exclusions = load_manual_exclusions(script_dir)
    if manual_exclusions:
        print(f"Loaded {len(manual_exclusions)} manual exclusions from collections.txt")

    try:
        html_content = Path(args.html_file).read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: HTML file not found: {args.html_file}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    movies, filtered_entries = parse_html_file(html_content, manual_exclusions)

    if not movies and not filtered_entries:
        print("No entries found in the HTML file")
        sys.exit(0)

    print(f"Found {len(movies)} movies in collection")
    if filtered_entries:
        print(f"Filtered out {len(filtered_entries)} entries (TV series, collections, etc.)")
    print()

    library_path = Path(args.library_path)
    existing_titles, created_count, skipped_count = process_movies(movies, library_path, args.dry_run)

    print(f"\nCreated: {created_count}, Skipped (already exist): {skipped_count}")

    if args.check_orphans:
        print()
        orphaned = find_orphaned_folders(library_path, existing_titles)
        if orphaned:
            print(f"⚠ Found {len(orphaned)} folder(s) no longer in collection:")
            for folder in sorted(orphaned):
                print(f"  - {folder}")
        else:
            print("No orphaned folders found")

    if filtered_entries:
        print()
        write_filtered_report(library_path, args.html_file, filtered_entries)

if __name__ == "__main__":
    main()
