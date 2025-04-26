import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

def scorecard_scrape(url):
    response = requests.get(url)
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
    round = df[1][1]
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

    df = df[['Event', 'Fight', 'Judge', 'Round', 'FighterOne', 'FighterTwo', 'ScoreOne', 'ScoreTwo', 'url']]

    return df