import requests
from bs4 import BeautifulSoup
import pandas as pd
import re



def scrape_event_data(url):

    """
    Scrape event data from the given URL.
    Args:
        url (str): The URL to scrape data from.
    Returns:
        list: A list of lists containing the scraped data.
    """

    # Check if the URL is valid
    url_pattern = re.compile(r'^https://mmadecisions\.com/decisions-by-event/\d{4}/$')
    if not url_pattern.match(url):
        raise ValueError(f"Invalid URL format: {url}")

    #Create empty list for scraped data
    all_event_data = []

    #Scrape url and get soup
    response = requests.get(url, timeout=20)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the table rows with class 'decision'
    decision_rows = soup.find_all('tr', class_='decision')

    for row in decision_rows:
        row_data = [cell.text.strip() for cell in row.find_all('td')]

        # Find the <a> tag (if it exists) within the row
        a_tag = row.find('a')

        # Extract the href if found, otherwise set to None
        href = a_tag['href'] if a_tag else None

        # Append the href to the row data
        row_data.append('https://mmadecisions.com/' + href)

        all_event_data.append(row_data)
        # Convert the list of lists to a DataFrame

        # Create DataFrame with an extra column for the href
        df_event = pd.DataFrame(all_event_data, columns=['Date', 'Event', 'NumFights', 'url'])

        # Change date column to date format
        df_event['Date'] = pd.to_datetime(df_event['Date']).dt.date

        # Sort descending by date
        df_event = df_event.sort_values(by='Date', ascending=False)

        return df_event
    

def scrape_fight_data(url):

    """
    Scrape fight data from the given URL.
    Args:
        url (str): The URL to scrape data from.
    Returns: 
        pd.DataFrame: A DataFrame containing the scraped fight data.
    """
    # Check if the URL is valid
    url_pattern = re.compile(r'^https://mmadecisions\.com/event/\d+/.+$')
    if not url_pattern.match(url):
        raise ValueError(f"Invalid URL format: {url}")

    response = requests.get(url, timeout=20)
    # Check if the request was successful
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve data from {url}. Status code: {response.status_code}")
    
    all_fight_data = []

    soup = BeautifulSoup(response.text, 'html.parser')

    # Get event info
    event_info_soup = soup.find_all('td', class_ = 'decision-top2')
    current_event = []

    for text in event_info_soup:
        current_event.append(text.get_text(strip=True,separator='||| '))  # Add text from soup into a list as a single object with ||| as a delimiter

    # Split items into different objects in the list
    current_event = current_event[0].split('||| ')

    for row in soup.find_all('td', class_='list2'):

        # Find the <a> tag (if it exists) within the row
        a_tag = row.find('a')

        # Extract the href if found, otherwise set to None
        href = ['https://mmadecisions.com/' + a_tag['href'] if a_tag else None]

        href.extend(current_event)

        all_fight_data.append(href)

    # Create dataframe
    df_fights = pd.DataFrame(all_fight_data,columns=['url', 'Event', 'Venue', 'Location'])
    df_fights['url'] = df_fights['url'].str.strip()

    # Reorder columns
    df_fights = df_fights[['Event', 'Location', 'Venue', 'url']]

    return df_fights


def scrape_scorecard(url):

    """
    Scrape scorecard data from the given URL.
    Args:
        url (str): The URL to scrape data from.
    Returns:
        pd.DataFrame: A DataFrame containing the scraped scorecard data.
    """

    # Check if the URL is valid
    url_pattern = re.compile(r'^https://mmadecisions\.com/decisions-by-event/\d+/$')
    if not url_pattern.match(url):
        raise ValueError(f"Invalid URL format: {url}")
    
    # Scrape the URL and get the soup
    response = requests.get(url, timeout=20)
    soup = BeautifulSoup(response.text, 'html.parser')

    tables = soup.find_all('table')
    second_table = tables[2]

    # Find all tr elements with class "top-row" or "decision"
    rows = second_table.find_all('tr', class_=['top-row', 'decision'])

    # Filter out rows with class "decision-bottom2" and "Tale of the Tape" text
    filtered_rows = [
        row for row in rows
        if 'decision-bottom2' not in row.get('class', []) and "TALE OF THE TAPE" not in row.text
    ]

    # Initialize an empty list to store data
    data = []

    # Extract data and append to the list
    for row in filtered_rows:
        row_text = row.get_text(strip=False)  # Get the text content of the row
        row_data = row_text.splitlines()  # Split the text into lines
        data.append(row_data)

    df = pd.DataFrame(data)
    df = df[[1, 2, 3]]
    df = df[~df[1].str.contains("LEGEND")]

    event = df[2][1]
    fight = url.rsplit('/', 1)[-1].replace('-', ' ')
    fighter_one = fight.rsplit(' vs', 1)[0]
    fighter_two = fight.rsplit(' vs', 1)[1]


    # Find the index of the first row containing "ROUND" in column 1
    round_index = df[df[1].str.contains("ROUND")].index[0] - 1

    # Remove rows before the found index
    df = df[round_index:]

    # Reset the index (optional)
    df = df.reset_index(drop=True)

    df = df[~df[1].str.contains("ROUND")]

    df['Judge'] = ''

    current_judge = None

    for index, row in df.iterrows():
        # Extract the value from column 2
        value = row[2]

        # Check if the value contains a judge's name
        if any(char.isalpha() for char in value):  # Check if any character is alphabetic
            current_judge = value  # Update current_judge if it's a judge's name

        # Assign the current_judge to the 'Judge' column
        df.loc[index, 'Judge'] = current_judge

    df = df[df[1] != '']
    df = df.rename(columns={1: 'Round', 2: 'ScoreOne', 3: 'ScoreTwo'})

    df['FighterOne'] = fighter_one
    df['FighterTwo'] = fighter_two
    df['Event'] = event
    df['Fight'] = fight
    df['url'] = url

    df = df[['Event',
             'Fight', 
             'Judge', 
             'Round', 
             'FighterOne', 
             'FighterTwo', 
             'ScoreOne', 
             'ScoreTwo', 
             'url']]

    return df