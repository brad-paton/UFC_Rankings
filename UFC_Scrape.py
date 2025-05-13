from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import re
import requests

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
