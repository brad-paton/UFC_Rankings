from datetime import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup


# Function to scrape the webpage
def scrape_website(url):
    # Send a GET request to the URL
    response = requests.get(url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
           # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract all text from the webpage
        text = soup.get_text(separator='\n', strip=True)

        return text
    else:
        return f"Failed to retrieve the webpage. Status code: {response.status_code}"
    
url = 'https://www.ufc.com/rankings'

# Call the function and print the result
text = scrape_website(url)

# Split the text into lines
lines = text.splitlines()

#Convert to pandas dataframe
df = pd.DataFrame({'Fighter':lines})

#Trim unnecessary rows
rmtop = df[df['Fighter'] == 'Top Rank'].index
df = df.loc[rmtop[0] + 1:]

rmbottom = df[df['Fighter'] == 'How are rankings determined?'].index
df = df.loc[:rmbottom[0]-1]

#Create notes column and populate it with the values in the list below
comments = ['NR', 'Champion', 'interim', 'Rank increased by', 'Rank decreased by']

df['Notes'] = None

df.reset_index(drop = True, inplace = True)

for comment in comments:
    indices = df[df['Fighter'] == comment].index
    for index in indices:
        if index > 0:
            df.at[index - 1, 'Notes'] = comment
            df.at[index, 'Fighter'] = pd.NA

#drop empty rows
df = df.dropna(subset = ['Fighter'])
df.reset_index(drop = True, inplace = True)

#Convert notes and fighter columns to strings
df['Notes'] = df['Notes'].astype(str)
df['Fighter'] = df['Fighter'].astype(str)

#Iterate through rows to add number ranks changed to notes
for index, row in df.iterrows():
    if 'Rank' in row['Notes']:
        if index + 1 < len(df):
            nextrow = df.iloc[index + 1]['Fighter']
            df.at[index, 'Notes'] += ' ' + nextrow
            df.at[index + 1, 'Fighter'] = pd.NA

#Drop empty rows
df = df.dropna(subset = ['Fighter'])
df.reset_index(drop = True, inplace = True)

#Ordered list of divisions
divisions = [
"Men's Pound-for-Pound", 
"Flyweight", 
"Bantamweight",
"Featherweight",
"Lightweight",
"Welterweight",
"Middleweight",
"Light Heavyweight",
"Heavyweight",
"Women's Pound-for-Pound",
"Women's Strawweight",
"Women's Flyweight",
"Women's Bantamweight",
]

#Initailize division column
df['Division'] = None

#Iterate through rows adding the division to each row
for row in range(len(df)):
    if df.at[row, 'Fighter'] in divisions:
        currentdivision = df.at[row, 'Fighter']
    df.at[row, 'Division'] = currentdivision

#Remove rows with the top rank text
df = df[df['Fighter'] != 'Top Rank']
df = df[~df['Fighter'].isin(divisions)]

df.reset_index(drop = True, inplace = True)

#Initalize ranking column
df['Ranking'] = None

#Iterate through rows adding ranking to ranking column
for index, row in df.iterrows():
    if len(row['Fighter']) < 3:
        if index + 1 < len(df):
            currentranking = df.iloc[index]['Fighter']
            df.at[index + 1, 'Ranking'] = currentranking

df.loc[df['Notes'] == 'Champion', 'Ranking'] = 0

#Drop empty rows
df = df.dropna(subset = ['Ranking'])

#Create date column
df['Date'] = None

#Add today's date to all rows
df['Date'] = datetime.now().strftime('%Y-%m-%d')

#Sort Columns
df = df[['Date', 'Division', 'Fighter', 'Ranking', 'Notes']]

existing_csv_path = 'UFC_Rankings.csv'

existing_csv = pd.read_csv(existing_csv_path)

combined = pd.concat([existing_csv, df], ignore_index=False)

combined.loc[combined['Ranking'] == 'Champion', 'Ranking'] = 0
combined.loc[combined['Ranking'] == 0, 'Notes'] = 'Champion'

combined['Division'] = pd.Categorical(combined['Division'], categories=divisions, ordered=True)
combined['Ranking'] = combined['Ranking'].astype(int)

combined = combined.sort_values(by=['Date', 'Division', 'Ranking'], ascending=[False, True, True])
combined.to_csv('UFC_Rankings.csv', index=False)
