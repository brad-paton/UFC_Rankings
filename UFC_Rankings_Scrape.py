from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import requests

#Rankings URL
URL = 'https://www.ufc.com/rankings'

response = requests.get(URL)

# Parse the HTML content using BeautifulSoup
soup = BeautifulSoup(response.content, 'html.parser')
# Extract all text from the webpage
text = soup.get_text(separator='\n', strip=True)

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

#Read in existing csv from repository
existing_csv = pd.read_csv('datasets/UFC_Rankings.csv')

#Combine the existing csv with the new data
combined = pd.concat([existing_csv, df], ignore_index=False)

combined.loc[combined['Ranking'] == 'Champion', 'Ranking'] = 0
combined.loc[combined['Ranking'] == 0, 'Notes'] = 'Champion'

combined['Division'] = pd.Categorical(combined['Division'], categories=divisions, ordered=True)
combined['Ranking'] = combined['Ranking'].astype(int)

#Sort values and convert back to a csv
combined = combined.sort_values(by=['Date', 'Division', 'Ranking'], ascending=[False, True, True])
combined.to_csv('datasets/UFC_Rankings.csv', index=False)

# Get the max date from the DataFrame
max_date = df['Date'].max()
df = df[df['Date'] == max_date].copy()

# DataFrame with divisions containing "women's"
df_women = df[df['Division'].str.lower().str.contains("women's")].copy()

# DataFrame with divisions NOT containing "women's"
df_men = df[~df['Division'].str.lower().str.contains("women's")].copy()

# Clean notes
df_men['Notes'] = df_men['Notes'].replace({
    'None': '',
    'Rank increased by': '▲',
    'Rank decreased by': '▼'
}, regex=True)

df_women['Notes'] = df_women['Notes'].replace({
    'None': '',
    'Rank increased by': '▲',
    'Rank decreased by': '▼'
}, regex=True)

# Create combined column
df_men['Combined'] = df_men['Fighter'] + '\t' + df_men['Notes']
df_women['Combined'] = df_women['Fighter'] + '\t' + df_women['Notes']

# Remove the 'Date' and 'Notes' columns
df_women = df_women.drop(columns=['Date', 'Notes', 'Fighter'])
df_men = df_men.drop(columns=['Date', 'Notes', 'Fighter'])

# Convert Ranking to numeric, errors='ignore' keeps 'Champion'/'Interim' as strings if already set
df_men['Ranking'] = pd.to_numeric(df_men['Ranking'], errors='ignore')
df_women['Ranking'] = pd.to_numeric(df_women['Ranking'], errors='ignore')

# Sort by Division and Ranking
df_men = df_men.sort_values(['Division', 'Ranking']).reset_index(drop=True)
df_women = df_women.sort_values(['Division', 'Ranking']).reset_index(drop=True)

# Add an index field that counts up for each division group
df_men['Rank'] = df_men.groupby('Division').cumcount()
df_women['Rank'] = df_women.groupby('Division').cumcount()

# Replace only the leading '0  Champion' or '1  Interim' with 'Champion' or 'Interim'
df_men['Combined'] = df_men['Combined'].str.replace(r'Champion$', '(C)', regex=True)
df_men['Combined'] = df_men['Combined'].str.replace(r'interim$', '(I))', regex=True)

df_women['Combined'] = df_women['Combined'].str.replace(r'Champion$', '(C)', regex=True)
df_women['Combined'] = df_women['Combined'].str.replace(r'interim$', '(I)', regex=True)

# Now pivot using Rank as the index
df_men_pivot = df_men.pivot(index='Rank', columns='Division', values='Combined')
df_women_pivot = df_women.pivot(index='Rank', columns='Division', values='Combined')

df_men_pivot = df_men_pivot[['Flyweight', 'Bantamweight', 'Featherweight', 'Lightweight', 'Welterweight', 'Middleweight', 'Light Heavyweight', 'Heavyweight']]
df_women_pivot = df_women_pivot[["Women's Strawweight", "Women's Flyweight", "Women's Bantamweight"]]

df_men_pivot = df_men_pivot.reset_index(drop=True)
df_women_pivot = df_women_pivot.reset_index(drop=True)

# Create the header for the README file
header = f"## UFC Rankings as of {max_date}\n\n"

with open("README.md", "w") as f:
    f.write(header)
    f.write("### Men's Divisions\n\n")
    f.write(df_men_pivot.to_markdown())
    f.write("\n\n### Women's Divisions\n\n")
    f.write(df_women_pivot.to_markdown())
    f.write("\n")


print(f"README.md has been updated with the latest UFC rankings as of {max_date}")