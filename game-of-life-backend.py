import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import os
import urllib.parse
import logging

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.DEBUG)

CSV_FOLDER = 'csv_files'
DATETIME_FORMAT = '%Y-%m-%d_%H:%M:%S'
SECTIONS = ['health_hygiene', 'personal', 'nutrition_hydration', 'home', 'social', 'bills_subscriptions']

def load_data(file_name):
    try:
        file_path = os.path.join(CSV_FOLDER, file_name)
        app.logger.debug(f"Attempting to load file: {file_path}")
        df = pd.read_csv(file_path)
        df['last_datetime'] = pd.to_datetime(df['last_datetime'], format=DATETIME_FORMAT)
        app.logger.debug(f"Successfully loaded file: {file_path}")
        return df
    except FileNotFoundError:
        app.logger.warning(f"File not found: {file_name}")
        return pd.DataFrame(columns=['activity', 'frequency', 'extra_interval', 'last_datetime'])
    except Exception as e:
        app.logger.error(f"Error loading file {file_name}: {str(e)}")
        return pd.DataFrame(columns=['activity', 'frequency', 'extra_interval', 'last_datetime'])

def save_data(df, file_name):
    file_path = os.path.join(CSV_FOLDER, file_name)
    df['last_datetime'] = df['last_datetime'].dt.strftime(DATETIME_FORMAT)
    df.to_csv(file_path, index=False)
    df['last_datetime'] = pd.to_datetime(df['last_datetime'], format=DATETIME_FORMAT)

def calculate_progress(last_datetime, frequency, extra_interval):
    now = datetime.now()
    time_passed = now - last_datetime
    total_minutes = frequency * 1440 + extra_interval * 60
    progress = max(0, 1 - (time_passed.total_seconds() / (total_minutes * 60)))
    current_minutes = int(progress * total_minutes)
    return progress, current_minutes, total_minutes

def generate_color(progress):
    if (progress <= 0):
        return "rgb(255,0,0)"
    elif (progress >= 0.9):
        return "rgb(0,255,0)"
    else:
        red = min(255, max(0, int(255 * (1 - progress) * 2)))
        green = min(255, max(0, int(255 * progress * 2)))
        return f"rgb({red},{green},0)"

def process_activities(df, section):
    result = []
    for _, row in df.iterrows():
        activity = row['activity']
        frequency = row['frequency']
        extra_interval = row['extra_interval']
        last_datetime = row['last_datetime']
        progress, current_minutes, total_minutes = calculate_progress(last_datetime, frequency, extra_interval)
        color = generate_color(progress)
        result.append({
            'activity': activity,
            'progress': progress,
            'color': color,
            'text': f"{current_minutes}/{total_minutes}",
            'is_zero': progress <= 0,
            'section': section
        })
    return result

@app.route('/activities/<section>', methods=['GET'])
def get_activities(section):
    app.logger.debug(f"Fetching activities for section: {section}")
    file_name = f"{section}.csv"
    df = load_data(file_name)
    result = process_activities(df, section)
    app.logger.debug(f"Returning {len(result)} activities for section: {section}")
    return jsonify(result)

@app.route('/activities/all', methods=['GET'])
def get_all_activities():
    app.logger.debug("Fetching all activities")
    result = []
    for section in SECTIONS:
        file_name = f"{section}.csv"
        df = load_data(file_name)
        result.extend(process_activities(df, section))
    app.logger.debug(f"Returning {len(result)} activities for all sections")
    return jsonify(result)

@app.route('/complete/<section>/<path:activity>', methods=['POST'])
def complete_activity(section, activity):
    app.logger.debug(f"Completing activity: {activity} in section: {section}")
    file_name = f"{section}.csv"
    df = load_data(file_name)
    data = request.json
    app.logger.debug(f"Received data: {data}")
    
    if data and 'datetime' in data:
        app.logger.debug(f"Received datetime string: {data['datetime']}")
        try:
            now = datetime.strptime(data['datetime'], '%Y-%m-%d %H:%M:%S')
            app.logger.debug(f"Parsed datetime: {now}")
        except ValueError as e:
            app.logger.error(f"Error parsing datetime: {e}")
            now = datetime.now()
            app.logger.warning(f"Using current datetime: {now}")
    else:
        now = datetime.now()
        app.logger.warning(f"No datetime provided, using current datetime: {now}")
    
    activity = urllib.parse.unquote(activity)
    app.logger.debug(f"Decoded activity: {activity}")
    
    if activity in df['activity'].values:
        df.loc[df['activity'] == activity, 'last_datetime'] = now
        app.logger.debug(f"Updated existing activity: {activity} with datetime: {now}")
    else:
        frequency = 1
        extra_interval = 0
        new_row = pd.DataFrame({'activity': [activity], 'frequency': [frequency], 'extra_interval': [extra_interval], 'last_datetime': [now]})
        df = pd.concat([df, new_row], ignore_index=True)
        app.logger.debug(f"Added new activity: {activity} with datetime: {now}")
    
    save_data(df, file_name)
    return jsonify({'status': 'success', 'datetime': now.strftime('%Y-%m-%d %H:%M:%S')})

if __name__ == '__main__':
    app.run(debug=True)