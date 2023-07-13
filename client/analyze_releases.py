import re
from datetime import datetime
import argparse
import os

# Parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("--changelog", default=".", help="Directory or full path of your changelog")
parser.add_argument("--detailed", action="store_true", help="Print detailed information for each release")
args = parser.parse_args()

# If changelog is a directory, look for changelog.md inside it
if os.path.isdir(args.changelog):
    args.changelog = os.path.join(args.changelog, "changelog.md")

# Read changelog
with open(args.changelog, 'r') as f:
    changelog = f.read()

# Extract product name
product_name = changelog.split('\n')[0]
print(f"Product Name: {product_name}")

# Regular expressions for different sections
version_pattern = r'## Version (\d+\.\d+\.\d+): ([A-Za-z]+\s+\d+(?:st|nd|rd|th)?\,\s+\d{4})'  # Fixed regex

feature_pattern = r'### New Features\n((?:- .+\n)*)'
bugfix_pattern = r'### Bug Fixes\n((?:- .+\n)*)'
enhancement_pattern = r'### Enhancements\n((?:- .+\n)*)'

# Find all version info
versions = re.findall(version_pattern, changelog)
features = re.findall(feature_pattern, changelog)
bugfixes = re.findall(bugfix_pattern, changelog)
enhancements = re.findall(enhancement_pattern, changelog)

# Reversed versions and their corresponding data
versions = versions[::-1]
features = features[::-1]
bugfixes = bugfixes[::-1]
enhancements = enhancements[::-1]

# Initialize metrics
num_releases = len(versions)
total_days_between_releases = 0
total_features = 0
total_bugfixes = 0
total_enhancements = 0
major_releases = 0
minor_releases = 0
patch_releases = 0
last_major_release = None
last_minor_release = None
last_patch_release = None
pending_release = None
longest_days_between_releases = 0
longest_release_version = None

# Get the release dates in datetime format
release_dates = []
today = datetime.now()
for version in versions:
    date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', version[1])
    date_str = date_str.strip()  # remove leading/trailing spaces
    date = datetime.strptime(date_str, "%B %d, %Y")
    if date > today:
        pending_release = version
        continue
    release_dates.append(date)

# If there is a pending release, remove it from the version list
if pending_release:
    versions.remove(pending_release)

# Get the first and last release dates
first_release_date = min(release_dates)
last_release_date = max(release_dates)


# Initialize the first release's "days between releases" as 0
days_between_releases_list = [0]

for i in range(1, len(versions)):
    days_between_releases = (release_dates[i] - release_dates[i - 1]).days
    days_between_releases_list.append(days_between_releases)
    total_days_between_releases += days_between_releases

    num_features = sum(1 for line in features[i].splitlines() if line.strip() != "- N/A") if i < len(features) else 0
    total_features += num_features

    num_bugfixes = sum(1 for line in bugfixes[i].splitlines() if line.strip() != "- N/A") if i < len(bugfixes) else 0
    total_bugfixes += num_bugfixes

    num_enhancements = sum(1 for line in enhancements[i].splitlines() if line.strip() != "- N/A") if i < len(enhancements) else 0
    total_enhancements += num_enhancements

    current_version = [int(x) for x in versions[i - 1][0].split('.')]
    next_version = [int(x) for x in versions[i][0].split('.')]
    if current_version[0] != next_version[0]:
        major_releases += 1
        last_major_release = (versions[i][0], versions[i][1])
        release_type = "Major"
    elif current_version[1] != next_version[1]:
        minor_releases += 1
        last_minor_release = (versions[i][0], versions[i][1])
        release_type = "Minor"
    elif current_version[2] != next_version[2]:
        patch_releases += 1
        last_patch_release = (versions[i][0], versions[i][1])
        release_type = "Patch"

    if days_between_releases > longest_days_between_releases:
        longest_days_between_releases = days_between_releases
        longest_release_version = f"{versions[i][0]} ({release_type}) {versions[i][1]}"

    if args.detailed:
        print(f"\nRelease: {versions[i][0]} ({release_type})")
        print(f"Date: {versions[i][1]}")
        print(f"Days Since Previous Release: {days_between_releases}")
        if num_features > 0:
            print(f"New Features: {num_features}")
        if num_enhancements > 0:
            print(f"Enhancements: {num_enhancements}")
        if num_bugfixes > 0:
            print(f"Bug Fixes: {num_bugfixes}")


avg_days_between_releases = round(total_days_between_releases / max(1, (len(versions) - 1)), 1)
avg_features_per_release = round(total_features / num_releases, 1) if num_releases > 0 else 0
avg_bugfixes_per_release = round(total_bugfixes / num_releases, 1) if num_releases > 0 else 0
avg_enhancements_per_release = round(total_enhancements / num_releases, 1) if num_releases > 0 else 0

months_since_first_release = round(total_days_between_releases / 30.44, 1)

# Print summary
print(f"\nTotal: {num_releases} releases over {months_since_first_release} months\n")

print(f"First Release Date: {first_release_date.strftime('%B %d, %Y')}")
print(f"Last Release Date: {last_release_date.strftime('%B %d, %Y')}\n")

print(f"Major releases: {major_releases}")
if last_major_release:
    print(f"   Last Major: {last_major_release[0]}, Date: {last_major_release[1]}")
else:
    print("   Last Major: None")
print(f"Minor releases: {minor_releases}")
if last_minor_release:
    print(f"   Last Minor: {last_minor_release[0]}, Date: {last_minor_release[1]}")
else:
    print("   Last Minor: None")
print(f"Patch releases: {patch_releases}")
if last_patch_release:
    print(f"   Last Patch: {last_patch_release[0]}, Date: {last_patch_release[1]}\n")
else:
    print("   Last Patch: None")

print(f"Days between releases: {avg_days_between_releases}")
print(f"Longest Release: {longest_days_between_releases} days for {longest_release_version}\n")

print(f"Features per release: {avg_features_per_release}")
print(f"Enhancements per release: {avg_enhancements_per_release}")
print(f"Bug fixes per release: {avg_bugfixes_per_release}")

if pending_release:
    pending_features = sum(1 for line in features[-1].splitlines() if line.strip() != "- N/A")
    pending_enhancements = sum(1 for line in enhancements[-1].splitlines() if line.strip() != "- N/A")
    pending_bugfixes = sum(1 for line in bugfixes[-1].splitlines() if line.strip() != "- N/A")

    current_version = [int(x) for x in versions[-1][0].split('.')]
    next_version = [int(x) for x in pending_release[0].split('.')]
    if current_version[0] != next_version[0]:
        pending_release_type = "Major"
    elif current_version[1] != next_version[1]:
        pending_release_type = "Minor"
    elif current_version[2] != next_version[2]:
        pending_release_type = "Patch"

    print(f"\nPending Release: {pending_release[0]} {pending_release[1]} ({pending_release_type} Release)")
    print(f"   Features: {pending_features}")
    print(f"   Enhancements: {pending_enhancements}")
    print(f"   Bug Fixes: {pending_bugfixes}")
