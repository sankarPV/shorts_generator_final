from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pickle

creds = pickle.load(open("youtube_token.pickle", "rb"))
youtube = build("youtube", "v3", credentials=creds)
channel = youtube.channels().list(part="snippet", mine=True).execute()
print(channel["items"][0]["snippet"]["title"])
