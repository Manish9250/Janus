import os
import json
import sqlite3
import time
from datetime import datetime, timedelta
from strategist import ACTIVITY_DATA_DIR, DB_PATH

def get_recent_activity_data(minutes=60):
    """Queries the DB for the last 'minutes' of activity for today."""
    print(f"Querying database for recent activity in the last {minutes} minutes...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    time_now = datetime.now()
    time_x_mins_ago = time_now - timedelta(minutes=minutes)

    start_time_str = time_x_mins_ago.strftime('%Y-%m-%dT%H:%M:%S')

    query = """
    SELECT timestamp, activity_analysis FROM activity_log 
    WHERE timestamp >= ?
    """
    
    cursor.execute(query, (start_time_str,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("No new activity found in the last 15 minutes.")
        return None

    aggregated_data = []
    for row in rows:
        timestamp, analysis_json_str = row
        try:
            analysis_data = json.loads(analysis_json_str)
            analysis_data['timestamp'] = timestamp # Add timestamp to the JSON object
            aggregated_data.append(analysis_data)
        except (json.JSONDecodeError, TypeError):
            # Skip malformed JSON data
            continue
            
    return aggregated_data

print("Recent activity data retrieval function loaded.")    
data = get_recent_activity_data(1440) # last 24 hours
print(data)