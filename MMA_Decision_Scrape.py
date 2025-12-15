from datetime import datetime
import requests
import pandas as pd
from bs4 import BeautifulSoup
import re
import UFC_Scrape_Library as LIB

events_path = 'datasets/MMA_Events.csv'
decisions_path = 'datasets/MMA_Decisions.csv'
scorecards_path = 'datasets/MMA_Scorecards.csv'


### Generate list of yearly event URLs
urls_yearly_events = []
currentyear = datetime.now().year

for year in range(1994, currentyear + 1):
    newurl = 'https://mmadecisions.com/decisions-by-event/' + str(year) + '/'
    urls_yearly_events.append(newurl)


df_event = pd.read_csv(events_path)
urls_events = df_event['url'].tolist()
    
for url in urls_yearly_events:

    if url in urls_events:
        continue

    df_event_new = LIB.scrape_event_data(url)

    df_event_all = pd.concat([df_event, df_event_new], ignore_index=True)

# Sort descending by date
df_event_all['Date'] = pd.to_datetime(df_event_all['Date']).dt.date
df_event_all = df_event_all.sort_values(by='Date', ascending=False)

# Save to MMA_Events csv
df_event_all.to_csv(events_path, index=False)

all_fight_data = []
df_decision = pd.read_csv(decisions_path)
urls_decisions = df_decision['url'].tolist()

for url in df_event_all['url']:

  if url in urls_decisions:
      continue

  try:
      df_decision_new = LIB.scrape_fight_data(url)
      df_decision = pd.concat([df_decision, df_decision_new], ignore_index=True)
  except Exception as e:
    continue
    
# Sort descending by date
df_decision = df_decision.sort_values(by='url', ascending=False)

# Save to MMA_Scorecards csv
df_decision.to_csv(decisions_path, index=False)

error_urls = []
df_scorecards = pd.read_csv(scorecards_path)
urls_scorecards = df_decision['url'].tolist()

for url in df_decision['url']:

    if url in urls_scorecards:
      continue

    try:
      df_scorecards_new = LIB.scrape_scorecard(url)
      df_scorecards = pd.concat([df_scorecards, df_scorecards_new], ignore_index=True)
    except Exception:
        error_urls.append(url)
    continue
    
# Sort descending by date
df_scorecards = df_scorecards.sort_values(by='url', ascending=False)

# Save to MMA_Scorecards csv
df_scorecards.to_csv(scorecards_path, index=False)