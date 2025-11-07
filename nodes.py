import os
import pandas as pd
import difflib
import csv

from datetime import datetime

def extract_actual_start_time(csv_path):
    with open(csv_path, 'r', encoding='utf-8') as f:
        lines = []
        for i in range(4):
            lines.append(f.readline())
        if len(lines) >= 4:
            parts = lines[3].strip().split(",")
            actual_start_time = parts[2].strip().strip('"')
            return actual_start_time
    return None

def extract_attendee_details(csv_path):
    attendees = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    # Find the "Attendee Details" section
    for i, line in enumerate(lines):
        if line.strip().startswith("Attendee Details"):
            header_idx = i + 1
            break
    else:
        return attendees  # No attendee section found

    # Collect all lines for the attendee section (header + data rows)
    attendee_lines = []
    for row in lines[header_idx:]:
        if row.strip() == "" or "Details" in row:
            break
        attendee_lines.append(row)
    if not attendee_lines:
        return attendees

    # Use csv.reader to handle quoted fields (e.g., names with commas)
    reader = csv.reader(attendee_lines)
    header = next(reader)
    try:
        name_idx = header.index("User Name (Original Name)")
        email_idx = header.index("Email")
        minutes_idx = header.index("Time in Session (minutes)")
    except ValueError:
        return attendees  # Columns not found

    for cols in reader:
        if len(cols) < max(name_idx, email_idx, minutes_idx) + 1:
            continue
        name = cols[name_idx].strip()
        email = cols[email_idx].strip()
        minutes = cols[minutes_idx].strip()
        attendees.append({"name": name, "email": email, "minutes": minutes})
    return attendees

def collect_attendance(folder="attendee_reports"):
    data = []
    for fname in os.listdir(folder):
        if fname.endswith(".csv"):
            fpath = os.path.join(folder, fname)
            actual_start_time = extract_actual_start_time(fpath)
            # Parse date from actual_start_time
            try:
                dt = datetime.strptime(actual_start_time, "%m/%d/%Y %I:%M:%S %p")
                date_str = dt.strftime("%Y-%m-%d")
                time_str = dt.strftime("%H:%M:%S")
            except Exception:
                date_str = ""
                time_str = ""
            attendees = extract_attendee_details(fpath)
            for attendee in attendees:
                data.append({
                    "name": attendee["name"],
                    "email": attendee["email"],
                    "minutes": attendee["minutes"],
                    "time": time_str,
                    "date": date_str,
                    "attended": "yes" if int(attendee["minutes"]) > 0 else "no"
                })
    df = pd.DataFrame(data)
    return df

def collect_attendance_from_bunny(folder_path='suprasidati-2025',storage_zone='zoom-attendee-reports-suprasidati', api_key_env="BUNNY_API_KEY"):
    """
    Downloads all CSV files from a Bunny CDN storage zone folder and returns the attendance DataFrame.
    - folder_path: path within the storage zone (e.g. "attendee_reports/")
    - storage_zone: name of the Bunny storage zone
    - api_key_env: environment variable name for the Bunny API key
    """
    import os
    import requests
    import tempfile

    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise ValueError(f"Bunny API key not found in environment variable {api_key_env}")

    # List files in the folder
    api_url = f"https://suprasidati.b-cdn.net/{folder_path}/"
    headers = {"AccessKey": api_key}
    list_url = f"https://storage.bunnycdn.com/{storage_zone}/{folder_path}/"
    resp = requests.get(list_url, headers=headers)
    resp.raise_for_status()
    files = resp.json()

    data = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for file in files:
            if not file["ObjectName"].endswith(".csv"):
                continue
            file_url = api_url + file["ObjectName"]
            local_path = os.path.join(tmpdir, file["ObjectName"])
            r = requests.get(file_url, headers=headers)
            r.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(r.content)
            actual_start_time = extract_actual_start_time(local_path)
            try:
                dt = datetime.strptime(actual_start_time, "%m/%d/%Y %I:%M:%S %p")
                date_str = dt.strftime("%Y-%m-%d")
                time_str = dt.strftime("%H:%M:%S")
            except Exception:
                date_str = ""
                time_str = ""
            attendees = extract_attendee_details(local_path)
            for attendee in attendees:
                data.append({
                    "name": attendee["name"],
                    "email": attendee["email"],
                    "minutes": attendee["minutes"],
                    "time": time_str,
                    "date": date_str,
                    "attended": "yes" if int(attendee["minutes"]) > 0 else "no"
                })
    df = pd.DataFrame(data)
    return df



def get_participant_meeting_stats(df, query):
    """
    Given the attendance DataFrame and a query (name or email), returns:
    - For email: number of meetings attended, total number of meetings
    - For name: fuzzy search, top 5 closest names and their meeting counts
    """
    # Each meeting is uniquely identified by (date, time)
    total_meetings = df[["date", "time"]].drop_duplicates().shape[0]

    if "@" in query:
        # Treat as email
        attended_meetings = df[df["email"].str.lower() == query.lower()][["date", "time"]].drop_duplicates().shape[0]
        return {
            "type": "email",
            "query": query,
            "meetings_attended": attended_meetings,
            "total_meetings": total_meetings
        }
    else:
        # Fuzzy search on names
        all_names = df["name"].dropna().unique()
        matches = difflib.get_close_matches(query, all_names, n=5, cutoff=0.5)
        results = []
        for name in matches:
            subdf = df[df["name"] == name]
            attended_meetings = subdf[["date", "time"]].drop_duplicates().shape[0]
            # Get the most common email for this name (or all unique emails)
            emails = subdf["email"].dropna().unique()
            email = emails[0] if len(emails) == 1 else list(emails)
            results.append({
                "name": name,
                "email": email,
                "meetings_attended": attended_meetings,
                "total_meetings": total_meetings
            })
        return {
            "type": "name",
            "query": query,
            "matches": results
        }

# Example usage:
if __name__ == "__main__":
    df = collect_attendance_from_bunny()
    stats = get_participant_meeting_stats(df, 'samiksha')
    print(stats)
