import requests
import pandas as pd
from bs4 import BeautifulSoup
import os 
import UFC_Scrape_Library as LIB  


# --- Configuration for scraping --- #
scrape_new_data_only = True # Set to True to only scrape new events, False to re-scrape all events
events_csv_path = 'datasets/UFC_Event_Stats.csv'
merged_stats_csv_path = 'datasets/UFC_Round_Stats.csv'
fights_csv_path = 'datasets/UFC_Fight_Stats.csv'

# --- Load existing data to check for new events --- #
existing_df_all_events = pd.DataFrame()
existing_event_urls = set() # Using a set for efficient lookup

if os.path.exists(events_csv_path):
    try:
        existing_df_all_events = pd.read_csv(events_csv_path)
        existing_event_urls = set(existing_df_all_events['event_url'])
        print(f"Loaded {len(existing_df_all_events)} existing events from {events_csv_path}")
    except Exception as e:
        print(f"Error loading existing events CSV: {e}. Starting with empty existing events.")
else:
    print("No existing events CSV found. Starting with empty existing events.")


all_page_url = "http://www.ufcstats.com/statistics/events/completed?page=all"

print(f"Fetching events from the 'all' page: {all_page_url}")

try:
    response_all_page = requests.get(all_page_url)
    response_all_page.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
    soup_all_page = BeautifulSoup(response_all_page.content, 'html.parser')

    scraped_events_data_from_all_page = LIB.scrape_events_from_page(soup_all_page)
    print(f"Successfully collected {len(scraped_events_data_from_all_page)} events from the 'all' page.")

    # Filter for new events if scrape_new_data_only is True
    if scrape_new_data_only:
        new_events_data = [event for event in scraped_events_data_from_all_page if event['event_url'] not in existing_event_urls]
        events_to_scrape_fights_from = pd.DataFrame(new_events_data)
        print(f"Found {len(events_to_scrape_fights_from)} new events to add.")
    else:
        events_to_scrape_fights_from = pd.DataFrame(scraped_events_data_from_all_page)
        print(f"All {len(events_to_scrape_fights_from)} events will be used.")

except requests.exceptions.RequestException as e:
    print(f"Error fetching the 'all' page ({all_page_url}): {e}")
    events_to_scrape_fights_from = pd.DataFrame() # Initialize as empty DataFrame in case of error

# Combine existing events with newly scraped events if applicable
if scrape_new_data_only and not existing_df_all_events.empty:
    # Concatenate new events with existing events, avoiding duplicates based on 'event_url'
    updated_df_all_events = pd.concat([existing_df_all_events, events_to_scrape_fights_from]).drop_duplicates(subset=['event_url']).reset_index(drop=True)
    print(f"Combined existing ({len(existing_df_all_events)}) and new events ({len(events_to_scrape_fights_from)}) into {len(updated_df_all_events)} events.")
else:
    updated_df_all_events = events_to_scrape_fights_from
    print(f"Created df_all_events with {len(updated_df_all_events)} events.")

df_all_events = updated_df_all_events

df_all_events['event_date'] = pd.to_datetime(df_all_events['event_date'], errors='coerce')
df_all_events = df_all_events.sort_values('event_date', ascending=False).reset_index(drop=True)

print("Successfully created/updated Pandas DataFrame for all events.")
print(f"Total events in df_all_events: {len(df_all_events)}")

df_all_events.to_csv(events_csv_path, index=False)

all_fights_data = [] # Initialize an empty list to store all fight details

# --- Load existing data to check for new events --- #
existing_df_fights = pd.DataFrame()
existing_fights_urls = set() # Using a set for efficient lookup

if os.path.exists(fights_csv_path):
    try:
        existing_df_fights = pd.read_csv(fights_csv_path)
        existing_fights_urls = set(existing_df_fights['fight_details_url'])
        print(f"Loaded {len(existing_df_fights)} existing fights from {fights_csv_path}")
    except Exception as e:
        print(f"Error loading existing fights CSV: {e}. Starting with empty existing fights.")
else:
    print("No existing fights CSV found. Starting with empty existing fights.")

# Determine which events need fights scraped
events_df_to_iterate = pd.DataFrame()
if scrape_new_data_only:
    events_df_to_iterate = events_to_scrape_fights_from
    print(f"Starting to scrape fight details for {len(events_df_to_iterate)} newly added events...")
else:
    events_df_to_iterate = df_all_events
    print(f"Starting to scrape fight details for {len(events_df_to_iterate)} all events...")

# Iterate through each event_url in the selected DataFrame
for index, row in events_df_to_iterate.iterrows():
    event_name = row['event_name']
    event_url = row['event_url']

    try:
        # Make an HTTP GET request to the event_url
        response = requests.get(event_url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        # Parse the response content using BeautifulSoup
        soup_event_detail = BeautifulSoup(response.content, 'html.parser')

        # Call the scrape_fight_details() function
        current_event_fights = LIB.scrape_fight_details(soup_event_detail)

        # Add event_name and event_url to each fight detail for context
        for fight in current_event_fights:
            fight['event_name'] = event_name
            fight['event_url'] = event_url

            # Filter for new fights if scrape_new_data_only is True
            if scrape_new_data_only and fight['fight_details_url'] in existing_fights_urls:
                continue # Skip existing fight

            all_fights_data.append(fight)

    except requests.exceptions.RequestException as e:
        # print(f"Error fetching event details for '{event_name}' ({event_url}): {e}") # Debug print removed
        continue # Continue to the next URL if an error occurs

newly_scraped_df_fights = pd.DataFrame(all_fights_data)

# Combine existing events with newly scraped events if applicable
if scrape_new_data_only and not existing_df_fights.empty:
    # Concatenate new events with existing events, avoiding duplicates based on 'event_url'
    updated_df_fights = pd.concat([existing_df_fights, newly_scraped_df_fights]).drop_duplicates(subset=['fight_details_url']).reset_index(drop=True)
    print(f"Combined existing ({len(existing_df_fights)}) and new fights ({len(newly_scraped_df_fights)}) into {len(updated_df_fights)} fights.")
else:
    updated_df_fights = newly_scraped_df_fights
    print(f"Created df_fights with {len(updated_df_fights)} fights.")

df_fights = updated_df_fights

print(f"\nFinished scraping all events. Total fights collected: {len(df_fights)}.")

print("Number of fights: ", len(df_fights))

df_fights.to_csv(fights_csv_path, index=False)

all_detailed_fight_stats = [] # Initialize an empty list to store all general fight details
all_detailed_strike_stats = [] # Initialize an empty list to store detailed strike stats

# --- Load existing data to check for new events --- #
existing_df_merged_fight_stats = pd.DataFrame()
existing_merged_fight_urls = set() # Using a set for efficient lookup

if os.path.exists(merged_stats_csv_path):
    try:
        existing_df_merged_fight_stats = pd.read_csv(merged_stats_csv_path)
        existing_merged_fight_urls = set(existing_df_merged_fight_stats['fight_details_url'])
        print(f"Loaded {len(existing_df_merged_fight_stats)} existing merged fight stats from {merged_stats_csv_path}")
    except Exception as e:
        print(f"Error loading existing merged fight stats CSV: {e}. Starting with empty existing merged fight stats.")
else:
    print("No existing merged fight stats CSV found. Starting with empty existing merged fight stats.")

# Determine which fights need stats scraped
fights_to_scrape_stats_for = pd.DataFrame()
if scrape_new_data_only:
    # Filter the newly scraped fights (from the previous section) against existing merged stats
    # Ensure newly_scraped_df_fights is not empty before attempting iteration
    if not newly_scraped_df_fights.empty:
        new_stats_fights = [fight for index, fight in newly_scraped_df_fights.iterrows() if fight['fight_details_url'] not in existing_merged_fight_urls]
        fights_to_scrape_stats_for = pd.DataFrame(new_stats_fights)
    print(f"Found {len(fights_to_scrape_stats_for)} newly scraped fights (from previous section) to scrape stats for.")
else:
    fights_to_scrape_stats_for = df_fights
    print(f"All {len(fights_to_scrape_stats_for)} fights will be scraped for stats.")

print(f"Starting to scrape round-by-round and detailed strike stats for {len(fights_to_scrape_stats_for)} fights...")

# Iterate through each fight_details_url in the df_fights DataFrame
for index, row in fights_to_scrape_stats_for.iterrows():
    fight_details_url = row['fight_details_url']
    fighter1_name = row['fighter1_name']
    fighter2_name = row['fighter2_name']

    try:
        # Make an HTTP GET request to the fight_details_url
        response = requests.get(fight_details_url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        # Parse the response content using BeautifulSoup
        soup_event_detail = BeautifulSoup(response.content, 'html.parser')

        # Call the scrape_round_by_round_stats() function for general stats
        current_general_stats = LIB.scrape_round_by_round_stats(soup_event_detail)
        # Add fight context to each general fight detail for consistency
        for fight_stat in current_general_stats:
            fight_stat['fight_details_url'] = fight_details_url
            if fight_stat['fighter_name'] == fighter1_name:
                fight_stat['opponent_name'] = fighter2_name
            elif fight_stat['fighter_name'] == fighter2_name:
                fight_stat['opponent_name'] = fighter1_name
            else:
                fight_stat['opponent_name'] = 'Unknown'
        all_detailed_fight_stats.extend(current_general_stats)

        # Call the new scrape_detailed_strike_stats() function for detailed strike stats
        current_strike_details = LIB.scrape_detailed_strike_stats(soup_event_detail)
        # Add fight context to each detailed strike stat for consistency
        for strike_stat in current_strike_details:
            strike_stat['fight_details_url'] = fight_details_url
            if strike_stat['fighter_name'] == fighter1_name:
                strike_stat['opponent_name'] = fighter2_name
            elif strike_stat['fighter_name'] == fighter2_name:
                strike_stat['opponent_name'] = fighter1_name
            else:
                strike_stat['opponent_name'] = 'Unknown'
        all_detailed_strike_stats.extend(current_strike_details)

    except requests.exceptions.RequestException as e:
        # print(f"Error fetching fight details for '{fight_details_url}': {e}") # Debug print removed
        continue # Continue to the next URL if an error occurs

newly_scraped_df_fight_details = pd.DataFrame(all_detailed_fight_stats)
newly_scraped_df_strike_details = pd.DataFrame(all_detailed_strike_stats)

# Merge the two DataFrames on common keys, handling empty DataFrames
if not newly_scraped_df_fight_details.empty and not newly_scraped_df_strike_details.empty:
    newly_merged_fight_stats = pd.merge(newly_scraped_df_fight_details, newly_scraped_df_strike_details,
                                     on=['fight_details_url', 'round', 'fighter_name', 'opponent_name'],
                                     how='left')
elif not newly_scraped_df_fight_details.empty:
    # If only general fight details were scraped (e.g., strike details table was missing)
    newly_merged_fight_stats = newly_scraped_df_fight_details
elif not newly_scraped_df_strike_details.empty:
    # This case is less likely if general stats are always present, but included for completeness
    newly_merged_fight_stats = newly_scraped_df_strike_details
else:
    # Both are empty, create an empty DataFrame with expected columns to avoid merge errors later
    # Define columns that would be present after a successful merge
    columns_if_merged = ['fight_details_url', 'round', 'fighter_name', 'opponent_name',
                         'kd', 'sig_str_landed', 'sig_str_attempted', 'sig_str_percent',
                         'total_str_landed', 'total_str_attempted', 'td_landed', 'td_attempted',
                         'td_percent', 'sub_att', 'rev', 'control_time_seconds',
                         'sig_str_head_landed', 'sig_str_head_attempted',
                         'sig_str_body_landed', 'sig_str_body_attempted',
                         'sig_str_leg_landed', 'sig_str_leg_attempted',
                         'sig_str_distance_landed', 'sig_str_distance_attempted',
                         'sig_str_clinch_landed', 'sig_str_clinch_attempted',
                         'sig_str_ground_landed', 'sig_str_ground_attempted']
    newly_merged_fight_stats = pd.DataFrame(columns=columns_if_merged)

# Combine existing events with newly scraped events if applicable
if scrape_new_data_only and not existing_df_merged_fight_stats.empty:
    # Concatenate new events with existing events, avoiding duplicates based on 'fight_details_url'
    updated_df_merged_fight_stats = pd.concat([existing_df_merged_fight_stats, newly_merged_fight_stats]).drop_duplicates(subset=['fight_details_url', 'round', 'fighter_name']).reset_index(drop=True)
    print(f"Combined existing ({len(existing_df_merged_fight_stats)}) and new merged fight stats ({len(newly_merged_fight_stats)}) into {len(updated_df_merged_fight_stats)} entries.")
else:
    updated_df_merged_fight_stats = newly_merged_fight_stats
    print(f"Created df_merged_fight_stats with {len(updated_df_merged_fight_stats)} entries.")

df_merged_fight_stats = updated_df_merged_fight_stats

print(f"\nFinished scraping all fight details. Total general round stats collected: {len(df_merged_fight_stats)}.")

print("\nSuccessfully converted collected detailed fight stats into a Pandas DataFrame.")
print(f"Number of merged fight stats entries: {len(df_merged_fight_stats)}")

df_merged_fight_stats.to_csv(merged_stats_csv_path, index=False)

all_general_fight_details = []

for index, row in newly_scraped_df_fights.iterrows():
    fight_details_url = row['fight_details_url']

    try:
        # Make an HTTP GET request to the fight_details_url
        response = requests.get(fight_details_url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        # Parse the response content using BeautifulSoup
        soup_fight_detail = BeautifulSoup(response.content, 'html.parser')

        # Call the scrape_general_fight_details() function
        current_general_details = LIB.scrape_general_fight_details(soup_fight_detail)

        # Add the fight_details_url to the dictionary for context
        current_general_details['fight_details_url'] = fight_details_url

        all_general_fight_details.append(current_general_details)

    except requests.exceptions.RequestException as e:
        # print(f"Error fetching fight general details for '{fight_details_url}': {e}") # Debug print removed
        continue # Continue to the next URL if an error occurs

print(f"Finished scraping general fight details for {len(all_general_fight_details)} entries.")

# --- Load existing general fight details to check for new entries ---
existing_general_details_csv_path = 'datasets/UFC_Fight_Stats.csv'
existing_df_general_fight_details = pd.DataFrame()
if os.path.exists(existing_general_details_csv_path):
    try:
        existing_df_general_fight_details = pd.read_csv(existing_general_details_csv_path)
        print(f"Loaded {len(existing_df_general_fight_details)} existing general fight details from {existing_general_details_csv_path}")
    except Exception as e:
        print(f"Error loading existing general fight details CSV: {e}. Starting with empty existing general fight details.")
else:
    print("No existing general fight details CSV found. Starting with empty existing general fight details.")

newly_scraped_df_general_fight_details = pd.DataFrame(all_general_fight_details)

# Combine existing events with newly scraped events if applicable
if scrape_new_data_only and not existing_df_general_fight_details.empty:
    updated_df_general_fight_details = pd.concat([existing_df_general_fight_details, newly_scraped_df_general_fight_details]).drop_duplicates(subset=['fight_details_url']).reset_index(drop=True)
    print(f"Combined existing ({len(existing_df_general_fight_details)}) and new general fight details ({len(newly_scraped_df_general_fight_details)}) into {len(updated_df_general_fight_details)} entries.")
else:
    updated_df_general_fight_details = newly_scraped_df_general_fight_details
    print(f"Created df_general_fight_details with {len(updated_df_general_fight_details)} entries.")

df_general_fight_details = updated_df_general_fight_details

print("\nSuccessfully converted collected general fight details into a Pandas DataFrame.")
print(f"Number of general fight details entries: {len(df_general_fight_details)}")

# 0. Clean up existing columns from df_fights that will be replaced or clarified.
columns_to_drop_if_exist = [
    'event_name', 'method', 'event_date', 'event_location', 'referee',
    'event_date_x', 'event_date_y', 'decision_method_x', 'decision_method_y',
    'referee_x', 'referee_y'
]
for col in columns_to_drop_if_exist:
    if col in df_fights.columns:
        df_fights = df_fights.drop(columns=[col])

# Ensure df_general_fight_details has required columns even if empty
required_general_cols = ['fight_details_url', 'decision_method', 'referee']
for col in required_general_cols:
    if col not in df_general_fight_details.columns:
        df_general_fight_details[col] = ''

# 1. Merge df_fights with df_general_fight_details to get decision_method and referee.
#    These columns should be new to df_fights after dropping old ones.
df_fights = pd.merge(
    df_fights,
    df_general_fight_details[required_general_cols],
    on='fight_details_url',
    how='left'
)

# 2. Merge df_fights with df_all_events to obtain the correct event_name and event_date.
#    'event_location' is NOT available from df_all_events and is handled separately.
df_fights = pd.merge(
    df_fights,
    df_all_events[['event_url', 'event_name', 'event_date']],
    on='event_url',
    how='left'
)

# 3. Add an empty 'event_location' column as it's not available from current scraping sources.
df_fights['event_location'] = ''

df_fights.to_csv(fights_csv_path, index=False)
print(f"Updated df_fights saved to {fights_csv_path}")
