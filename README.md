# Jellyray

Python script which automatically creates Jellyfin placeholder files from your Blu-ray.com collection export.

TV Series and collections are filtered semi-automatically (with the option to filter out more entries manually by listing them in `collections.txt`). All filtered entries are logged to `filtered_entries.txt`.

When you own a movie on both DVD and Blu-Ray, it will prefer Blu-Ray.

Before it starts creating stuff, it checks for duplicates, and there's also a dry-run mode to be extra sure. There's also a feature to find orphaned folders (which would indicate things no longer in your collection).

## Why and how?

Adding my physical media to my Jellyfin server helps me de-duplicate, as more and more movies I had TV recordings of are getting proper releases. It's also great to find something to watch, and see fuller filmographies of actors and directors.

Jellyfin web doesn't seem to distinguish between placeholders and real movies all that much, which is why my workflow puts things in a separate physical media library, but the Android TV app does have a nice red banner to mark the difference.

## Setup

1. Save the script to your system
2. Make it executable: `chmod +x jellyray.py`

On Windows, you can probably run this through CMD, Git Bash, or Powershell terminal?

## Usage

### Getting Your Blu-ray.com Export

This part's a bit messy, but if you can run this script, I'm pretty sure you can manage to do this.

1. Log into Blu-ray.com
2. View your complete collection
3. Click "Printer Friendly View"
4. Inspect the table
5. Save the tbody tag and all the movies within it as an HTML file

You'll have to update this HTML file again if you get new movies on blu-ray.com. There are probably good ways to automate this, but I generally prefer to tackle this manually since I try to clean up my collection data and tend to add a lot of entries to `collections.txt`.

### Preview changes (dry-run)

```bash
python3 jellyray.py --dry-run your_export.html /path/to/jellyfin/library
```

If you find any entries that aren't movies or which you don't want to generate, you can add them to `collections.txt` (name followed by the year between parentheses).

It's also a good opportunity to check your Blu-ray.com collection for missing data. I've noticed that DVDs are sometimes not linked to a movie, which can lead to wrong or even missing dates.

### Basic sync (create new placeholders)

```bash
python3 jellyray.py your_export.html /path/to/jellyfin/library
```

### Check for orphaned folders

```bash
python3 jellyray.py --check-orphans your_export.html /path/to/jellyfin/library
```

## Example

If your collection has:

```
12 Monkeys (1995)              Blu-ray
*batteries not included (1987) Blu-ray, DVD
"G" Men (1935)                 DVD
```

The script creates:

- 12 Monkeys (1995)/12 Monkeys (1995).bluray.disc
- \*batteries not included (1987)/*batteries not included (1987).bluray.disc  (Blu-ray preferred)
- "G" Men (1935)/"G" Men (1935).dvd.disc
