import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pyttsx3
import speech_recognition as sr
import pytz

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
DAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
DAY_EXTENSIONS = ["rd", "th", "st", "nd"]

def speak(text):
    print(f"Speaking: {text}")
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

def get_audio():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        audio = r.listen(source)
        said = " "

        try:
            said = r.recognize_google(audio)
            print(f"Recognized: {said}")
        except Exception as e:
            print(f"Exception: {str(e)}")
    return said

def authenticate_google():
    creds = None
    if os.path.exists("token.json"):
        print("Loading credentials from file...")
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing access token...")
            creds.refresh(Request())
        else:
            print("Fetching new tokens...")
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open("token.json", "w") as token:
            print("Saving credentials for future use...")
            token.write(creds.to_json())

    try:
        print("Building the service...")
        service = build("calendar", "v3", credentials=creds)
        return service
    except Exception as e:
        print(f"An error occurred during authentication: {e}")

def get_events(start_time, end_time, service):
    print(f"Getting events from {start_time} to {end_time}")
    try:
        utc = pytz.UTC
        start_time = start_time.astimezone(utc)
        end_time = end_time.astimezone(utc)
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start_time.isoformat(), 
                timeMax=end_time.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return

        print("Upcoming events:")
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            print(start, event["summary"])
    except HttpError as error:
        print(f"An error occurred: {error}")

def get_data(text):
    text = text.lower()
    print(f"Processing text: {text}")
    today = datetime.date.today()
    now = datetime.datetime.now()

    if text.count("today") > 0:
        return today, now.time(), (now + datetime.timedelta(hours=1)).time()  # Default duration 1 hour

    day = -1
    day_of_week = -1
    month = -1
    year = today.year
    time_start = None
    time_end = None

    for word in text.split():
        if word in MONTHS:
            month = MONTHS.index(word) + 1
        elif word in DAYS:
            day_of_week = DAYS.index(word)
        elif word.isdigit():
            day = int(word)
        elif word.count(":") == 1:
            hour, minute = word.split(":")
            if hour.isdigit() and minute.isdigit():
                hour = int(hour)
                minute = int(minute)
                if time_start is None:
                    time_start = datetime.time(hour, minute)
                else:
                    time_end = datetime.time(hour, minute)
        else:
            for ext in DAY_EXTENSIONS:
                found = word.find(ext)
                if found > 0:
                    try:
                        day = int(word[:found])
                    except:
                        pass
    
    print(f"Parsed date - Day: {day}, Month: {month}, Day of Week: {day_of_week}, Year: {year}")
    
    if month < today.month and month != -1:
        year += 1
    if day < today.day and month == -1 and day != -1:
        month += 1
    if month == -1 and day == -1 and day_of_week != -1:
        current_day_of_week = today.weekday()
        dif = day_of_week - current_day_of_week
        if dif < 0:
            dif += 7
            if text.count("next") >= 1:
                dif += 7
        target_date = today + datetime.timedelta(dif)
    else:
        target_date = datetime.date(year=year, month=month, day=day)
    
    if time_start is None:
        time_start = datetime.time(0, 0)
    if time_end is None:
        time_end = datetime.time(23, 59)

    print(f"Returning date - {target_date}, Time Start: {time_start}, Time End: {time_end}")
    return target_date, time_start, time_end

SERVICE = authenticate_google()
text = get_audio()
date, start_time, end_time = get_data(text)
start_datetime = datetime.datetime.combine(date, start_time)
end_datetime = start_datetime + datetime.timedelta(seconds=5)
print(f"Retrieved date and time range: {start_datetime} to {end_datetime}")
get_events(start_datetime, end_datetime, SERVICE)
