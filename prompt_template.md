# Context:
Im developing "The Game of Life" web app for monitoring progress bars of life activities. 
# Codebase:
## Folder Contents:
### Folder structure:
```
_TheGameOfLife-github-version/
├── csv_files/
│   ├── nutrition_hydration.csv
│   ├── personal.csv
│   ├── social.csv
│   ├── bills_subscriptions.csv
│   ├── health_hygiene.csv
│   └── home.csv
├── start-game-of-life.bat
├── TheGameOfLife-concept-art.png
├── game-of-life-backend.py
├── game-of-life-frontend.html
└── README.md
```
## File Contents:
### `game-of-life-backend.py`:
```py
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
            'section': section,
            'frequency': frequency,
            'extra_interval': extra_interval,
            'last_datetime': last_datetime.strftime(DATETIME_FORMAT)
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
@app.route('/activities/feedback', methods=['GET'])
def get_feedback_activities():
    app.logger.debug("Fetching feedback activities")
    result = []
    for section in SECTIONS:
        file_name = f"{section}.csv"
        df = load_data(file_name)
        result.extend(process_activities(df, section))
    result.sort(key=lambda x: (x['progress'], x['last_datetime']))  # Sort by progress and then by last_datetime
    app.logger.debug(f"Returning {len(result)} sorted feedback activities")
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
```
### `game-of-life-frontend.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The Game of Life</title>
    <script src="https://cdn.jsdelivr.net/npm/vue@2.6.14/dist/vue.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css">
    <script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 5px;
        }
        h1 {
            text-align: center;
            margin: 0 0 10px 0;
            font-size: 24px;
        }
        .container {
            display: flex;
            justify-content: space-between;
            flex-wrap: nowrap;
            gap: 2px;
        }
        .column {
            flex: 1;
            min-width: 0;
        }
        .column h2 {
            margin: 0 0 2px 0;
            font-size: 14px;
            text-align: center;
        }
        .progress-bar {
            width: 100%;
            height: 18px;
            background-color: #f0f0f0;
            border-radius: 9px;
            margin-bottom: 1px;
            position: relative;
            overflow: hidden;
        }
        .progress {
            height: 100%;
            border-radius: 9px;
            transition: width 0.5s ease-in-out, background-color 0.5s ease-in-out;
            position: absolute;
            top: 0;
            left: 0;
        }
        .progress-text {
            position: absolute;
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: black;
            font-weight: bold;
            z-index: 2;
            font-size: 9px;
        }
        button {
            display: inline-block;
            width: 49%;
            margin: 0;
            padding: 1px 2px;
            font-size: 9px;
            cursor: pointer;
        }
        .activity-container {
            margin-bottom: 2px;
            padding: 2px;
            border: 1px solid #ddd;
            border-radius: 3px;
        }
        .activity-label {
            font-weight: bold;
            margin-bottom: 1px;
            font-size: 10px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .button-container {
            display: flex;
            justify-content: space-between;
        }
        .flatpickr-confirm {
            display: flex;
            justify-content: space-between;
            padding: 5px;
            background: #f0f0f0;
        }
        .flatpickr-confirm button {
            width: 45%;
            padding: 5px;
            border: none;
            background: #4CAF50;
            color: white;
            cursor: pointer;
        }
        .flatpickr-confirm button.exit {
            background: #f44336;
        }
        .datetime-input {
            display: none;
        }
        .navigation {
            display: flex;
            justify-content: center;
            margin-bottom: 10px;
        }
        .navigation button {
            width: auto;
            padding: 5px 10px;
            font-size: 14px;
            margin: 0 5px;
        }
        .page-number {
            text-align: center;
            font-size: 14px;
            margin-bottom: 10px;
        }
        .feedback-activity {
            background-color: #ffe6e6;
            padding: 5px;
            margin-bottom: 5px;
            border-radius: 5px;
        }
        .feedback-activity p {
            margin: 2px 0;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div id="app">
        <h1>The Game of Life</h1>
        <div class="navigation">
            <button @click="showFeedback">Feedback</button>
            <button @click="showOverview">Overview</button>
            <button @click="showSections">Sections</button>
        </div>
        <div v-if="currentView === 'overview'">
            <div class="container">
                <div v-for="section in sections" :key="section" class="column">
                    <h2>{{ formatSectionTitle(section) }}</h2>
                    <div v-for="activity in activitiesBySection[section]" :key="activity.activity" class="activity-container">
                        <div class="activity-label" :title="activity.activity">{{ activity.activity }}</div>
                        <div class="progress-bar">
                            <div class="progress" :style="getProgressStyle(activity)"></div>
                            <div class="progress-text">{{ formatTime(activity.text) }}</div>
                        </div>
                        <div class="button-container">
                            <button @click="completeActivity(section, activity.activity)">Complete</button>
                            <button @click="openDateTimePicker(section, activity.activity)">Select datetime</button>
                        </div>
                        <input :ref="'datetime-' + section + '-' + activity.activity" type="text" class="datetime-input">
                    </div>
                </div>
            </div>
        </div>
        <div v-else-if="currentView === 'sections'">
            <div class="navigation">
                <button @click="previousPage" :disabled="currentPage === 1">Previous</button>
                <button @click="nextPage" :disabled="currentPage === 2">Next</button>
            </div>
            <div class="page-number">
                Page {{ currentPage }} of 2
            </div>
            <div class="container">
                <div v-for="section in currentSections" :key="section" class="column">
                    <h2>{{ formatSectionTitle(section) }}</h2>
                    <div v-for="activity in activities[section]" :key="activity.activity" class="activity-container">
                        <div class="activity-label" :title="activity.activity">{{ activity.activity }}</div>
                        <div class="progress-bar">
                            <div class="progress" :style="getProgressStyle(activity)"></div>
                            <div class="progress-text">{{ formatTime(activity.text) }}</div>
                        </div>
                        <div class="button-container">
							<button @click="completeActivity(section, activity.activity)">Complete</button>
                            <button @click="openDateTimePicker(section, activity.activity)">Select datetime</button>
                        </div>
                        <input :ref="'datetime-' + section + '-' + activity.activity" type="text" class="datetime-input">
                    </div>
                </div>
            </div>
        </div>
        <div v-else-if="currentView === 'feedback'">
            <div class="container">
                <div v-for="section in sections" :key="section" class="column">
                    <h2>{{ formatSectionTitle(section) }}</h2>
                    <div v-for="activity in getFeedbackActivitiesForSection(section)" :key="activity.activity" class="activity-container feedback-activity">
                        <div class="activity-label" :title="activity.activity">{{ activity.activity }}</div>
                        <p><strong>Progress:</strong> {{ (activity.progress * 100).toFixed(2) }}%</p>
                        <p><strong>Frequency:</strong> {{ activity.frequency }} days</p>
                        <p><strong>Extra Interval:</strong> {{ activity.extra_interval }} hours</p>
                        <p><strong>Last Completed:</strong> {{ formatDateTime(activity.last_datetime) }}</p>
                        <div class="progress-bar">
                            <div class="progress" :style="getProgressStyle(activity)"></div>
                            <div class="progress-text">{{ formatTime(activity.text) }}</div>
                        </div>
                        <div class="button-container">
                            <button @click="completeActivity(activity.section, activity.activity)">Complete</button>
                            <button @click="openDateTimePicker(activity.section, activity.activity)">Select datetime</button>
                        </div>
                        <input :ref="'datetime-' + activity.section + '-' + activity.activity" type="text" class="datetime-input">
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script>
        new Vue({
            el: '#app',
            data: {
                currentView: 'sections',
                currentPage: 1,
                sections: ['health_hygiene', 'personal', 'nutrition_hydration', 'home', 'social', 'bills_subscriptions'],
                pages: [
                    ['health_hygiene', 'personal', 'nutrition_hydration'],
                    ['home', 'social', 'bills_subscriptions']
                ],
                activities: {
                    home: [],
                    health_hygiene: [],
                    personal: [],
                    nutrition_hydration: [],
                    social: [],
                    bills_subscriptions: []
                },
                activitiesBySection: {},
                feedbackActivities: [],
                flatpickrInstances: {}
            },
            computed: {
                currentSections() {
                    return this.pages[this.currentPage - 1];
                }
            },
            methods: {
                showOverview() {
                    this.currentView = 'overview';
                    this.fetchAllActivities();
                },
                showSections() {
                    this.currentView = 'sections';
                    this.refreshData();
                },
                showFeedback() {
                    this.currentView = 'feedback';
                    this.fetchFeedbackActivities();
                },
                fetchActivities(section) {
                    console.log(`Fetching activities for section: ${section}`);
                    axios.get(`http://localhost:5000/activities/${section}`)
                        .then(response => {
                            console.log(`Received data for ${section}:`, response.data);
                            this.activities[section] = response.data;
                        })
                        .catch(error => {
                            console.error(`Error fetching activities for ${section}:`, error);
                        });
                },
                fetchAllActivities() {
                    console.log('Fetching all activities');
                    axios.get('http://localhost:5000/activities/all')
                        .then(response => {
                            console.log('Received data for all sections:', response.data);
                            this.activitiesBySection = this.sections.reduce((acc, section) => {
                                acc[section] = response.data.filter(activity => activity.section === section);
                                return acc;
                            }, {});
                        })
                        .catch(error => {
                            console.error('Error fetching all activities:', error);
                        });
                },
                fetchFeedbackActivities() {
                    console.log('Fetching feedback activities');
                    axios.get('http://localhost:5000/activities/feedback')
                        .then(response => {
                            console.log('Received feedback activities:', response.data);
                            this.feedbackActivities = response.data;
                        })
                        .catch(error => {
                            console.error('Error fetching feedback activities:', error);
                        });
                },
                getFeedbackActivitiesForSection(section) {
                    return this.feedbackActivities.filter(activity => activity.section === section);
                },
                completeActivity(section, activity) {
                    axios.post(`http://localhost:5000/complete/${section}/${encodeURIComponent(activity)}`, {}, {
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    })
                    .then(() => {
                        if (this.currentView === 'overview') {
                            this.fetchAllActivities();
                        } else if (this.currentView === 'sections') {
                            this.fetchActivities(section);
                        } else if (this.currentView === 'feedback') {
                            this.fetchFeedbackActivities();
                        }
                    })
                    .catch(error => console.error(error));
                },
                refreshData() {
                    console.log('Refreshing data for current page');
                    if (this.currentView === 'overview') {
                        this.fetchAllActivities();
                    } else if (this.currentView === 'sections') {
                        this.currentSections.forEach(section => this.fetchActivities(section));
                    } else if (this.currentView === 'feedback') {
                        this.fetchFeedbackActivities();
                    }
                },
                formatTime(timeString) {
                    const [current, total] = timeString.split('/').map(Number);
                    const currentHours = Math.floor(current / 60);
                    const currentMinutes = current % 60;
                    const totalHours = Math.floor(total / 60);
                    const totalMinutes = total % 60;
                    return `${currentHours}h ${currentMinutes}m / ${totalHours}h ${totalMinutes}m`;
                },
                getProgressStyle(activity) {
                    return {
                        width: activity.is_zero ? '100%' : `${activity.progress * 100}%`,
                        backgroundColor: activity.color
                    };
                },
                formatSectionTitle(section) {
                    return section.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
                },
                formatDateTime(dateTimeString) {
                    const date = new Date(dateTimeString.replace(/_/g, ' '));
                    return date.toLocaleString();
                },
                openDateTimePicker(section, activity) {
                    const key = `${section}-${activity}`;
                    const inputRef = this.$refs[`datetime-${section}-${activity}`][0];
                    if (!this.flatpickrInstances[key]) {
                        this.flatpickrInstances[key] = flatpickr(inputRef, {
                            enableTime: true,
                            dateFormat: "Y-m-d H:i:S",
                            time_24hr: true,
                            defaultDate: new Date(),
                            appendTo: document.body,
                            static: true,
                            allowInput: true,
                            weekNumbers: true,
                            locale: {
                                firstDayOfWeek: 1 // Monday as first day of week
                            },
                            onChange: (selectedDates, dateStr, instance) => {
                                console.log('Selected date changed:', dateStr);
                            },
                            onReady: (selectedDates, dateStr, instance) => {
                                const customButtons = document.createElement('div');
                                customButtons.className = 'flatpickr-confirm';
                                const enterButton = document.createElement('button');
                                enterButton.textContent = `Enter: ${activity}`;
                                enterButton.className = 'enter-button';
                                enterButton.addEventListener('click', () => {
                                    if (instance.selectedDates.length > 0) {
                                        this.completeActivityWithCustomDate(section, activity, instance.selectedDates[0]);
                                    }
                                    instance.close();
                                });
                                const exitButton = document.createElement('button');
                                exitButton.textContent = 'Exit';
                                exitButton.className = 'exit';
                                exitButton.addEventListener('click', () => {
                                    instance.close();
                                });
                                customButtons.appendChild(enterButton);
                                customButtons.appendChild(exitButton);
                                instance.calendarContainer.appendChild(customButtons);
                            }
                        });
                    }
                    this.flatpickrInstances[key].open();
                },
                completeActivityWithCustomDate(section, activity, date) {
                    const formattedDate = this.formatDate(date);
                    console.log('Sending date to server:', formattedDate);
                    axios.post(`http://localhost:5000/complete/${section}/${encodeURIComponent(activity)}`, {
                        datetime: formattedDate
                    }, {
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    })
                    .then(() => {
                        if (this.currentView === 'overview') {
                            this.fetchAllActivities();
                        } else if (this.currentView === 'sections') {
                            this.fetchActivities(section);
                        } else if (this.currentView === 'feedback') {
                            this.fetchFeedbackActivities();
                        }
                    })
                    .catch(error => console.error(error));
                },
                formatDate(date) {
                    const pad = (num) => num.toString().padStart(2, '0');
                    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
                },
                previousPage() {
                    if (this.currentPage > 1) {
                        this.currentPage--;
                        this.refreshData();
                    }
                },
                nextPage() {
                    if (this.currentPage < 2) {
                        this.currentPage++;
                        this.refreshData();
                    }
                }
            },
            mounted() {
                this.refreshData();
                setInterval(this.refreshData, 60000); // Refresh every minute
            }
        });
    </script>
</body>
</html>
```
# Problem:
I want `Overview` to be the main default page instead of `Sections`
# Task:
Modify code to implement changes. Lets 1. understand task and mental contrast potential issues, 2. make detailed to-do list, 3. devise detailed plan to complete task. Then lets take deep breath, carry out plan, and do task step-by-step. Write full code but replace unchanged parts with comments