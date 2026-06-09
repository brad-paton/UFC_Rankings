from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import requests
import re 

url_rankings = 'https://www.ufc.com/rankings'

try:
    response_rankings_page = requests.get(url_rankings)
    response_rankings_page.raise_for_status()  
    soup_rankings_page = BeautifulSoup(response_rankings_page.content, 'html.parser')
    print("Successfully fetched and parsed the UFC rankings page.")

    # Locate all div elements with class 'view-grouping'
    all_rankings_groupings = soup_rankings_page.find_all('div', class_='view-grouping')

    if all_rankings_groupings:
        print(f"Found {len(all_rankings_groupings)} ranking groupings.")
        # We will process these groupings in a subsequent cell to extract structured data.
    else:
        print("Error: No 'view-grouping' divs found on the page.")

except requests.exceptions.RequestException as e:
    print(f"Error fetching the UFC rankings page ({url_rankings}): {e}")
    soup_rankings_page = None # Set to None in case of an error
    all_rankings_groupings = [] # Initialize as empty list in case of error




rankings_data = []

if 'all_rankings_groupings' not in locals() or not all_rankings_groupings:
    print("No ranking groupings found. Please run the previous cell to fetch the rankings.")
else:
    for i, grouping in enumerate(all_rankings_groupings):
        # Extract division name
        division_header_div = grouping.find('div', class_='view-grouping-header')
        division_name = 'Unknown Division'
        if division_header_div:
            raw_division_text = division_header_div.get_text(separator=' ', strip=True)
            division_name = raw_division_text.replace('Top Rank', '').strip()

        print(f"Processing division: {division_name}")

        view_grouping_content_div = grouping.find('div', class_='view-grouping-content')

        rankings_table = view_grouping_content_div.find('table', class_='cols-0') if view_grouping_content_div else None

        if not rankings_table:
            print(f"  No ranking table found for division: {division_name}")
            continue

        # Find all table rows (<tr>) within the tbody
        fighter_rows = rankings_table.find('tbody').find_all('tr')

        for row in fighter_rows:
            fighter_rank_td = row.find('td', class_='views-field-weight-class-rank')
            fighter_name_td = row.find('td', class_='views-field-title')
            rank_change_td = row.find('td', class_='views-field views-field-weight-class-rank-change')

            fighter_name = fighter_name_td.find('a').get_text(strip=True) if fighter_name_td and fighter_name_td.find('a') else 'N/A'

            full_rank_text = fighter_rank_td.get_text(strip=True) if fighter_rank_td else ''
            fighter_rank = 'NR'
            fighter_notes = ''

            if full_rank_text:
                # Attempt to extract numerical rank and any additional notes
                match = re.match(r'(\d+|C|NR)?\s*(.*)', full_rank_text)
                if match:
                    extracted_rank = match.group(1) if match.group(1) else ''
                    extracted_notes = match.group(2).strip()

                    if extracted_rank:
                        fighter_rank = extracted_rank
                    if extracted_notes:
                        fighter_notes = extracted_notes
                else:
                    # If regex doesn't match a standard rank, treat whole text as rank and no notes
                    fighter_rank = full_rank_text

            # Extract rank change text and append to notes
            rank_change_text = rank_change_td.get_text(strip=True) if rank_change_td else ''
            if rank_change_text:
                # Insert space between 'by' and the number if applicable
                rank_change_text = re.sub(r'(by)(\d+)', r'\1 \2', rank_change_text)
                if fighter_notes:
                    fighter_notes += f", {rank_change_text}"
                else:
                    fighter_notes = rank_change_text

            # Default note for truly unranked but listed fighters (if no other notes)
            if not full_rank_text and fighter_name != 'N/A':
                fighter_rank = 'NR'
                if not fighter_notes:
                    fighter_notes = 'Not Ranked'
                else:
                    fighter_notes = 'Not Ranked, ' + fighter_notes

            if fighter_name != 'N/A': # Only add if a fighter name is found
                rankings_data.append({
                    'division': division_name,
                    'fighter_name': fighter_name,
                    'rank': fighter_rank,
                    'notes': fighter_notes
                })

df_rankings = pd.DataFrame(rankings_data)


champions_data = []

if 'all_rankings_groupings' not in locals() or not all_rankings_groupings:
    print("No ranking groupings found. Please run the cell to fetch rankings first.")
else:
    for grouping in all_rankings_groupings:
        division_header_div = grouping.find('div', class_='view-grouping-header')
        division_name = 'Unknown Division'
        if division_header_div:
            raw_division_text = division_header_div.get_text(separator=' ', strip=True)
            division_name = raw_division_text.replace('Top Rank', '').strip()

        champion_details_div = grouping.find('div', class_=lambda c: c and 'rankings--athlete--champion' in c)

        if champion_details_div:
            champion_name = 'N/A'
            fighter_name_link = champion_details_div.find('a')
            if fighter_name_link:
                champion_name = fighter_name_link.get_text(strip=True)
            else:

                h5_tag = champion_details_div.find('h5')
                if h5_tag:
                    champion_name = h5_tag.get_text(strip=True)
                else:
                    name_div = champion_details_div.find('div', class_='rankings--athlete--name')
                    if name_div:
                        champion_name = name_div.get_text(strip=True)
                    else:

                        raw_champion_text = champion_details_div.get_text(strip=True)
                        champion_name = re.sub(r'\b(Men\'s Pound-for-Pound|Top Rank|Flyweight|Bantamweight|Featherweight|Lightweight|Welterweight|Middleweight|Light Heavyweight|Heavyweight|Women\'s Pound-for-Pound|Women\'s Strawweight|Women\'s Flyweight|Women\'s Bantamweight|Champion)\b', '', raw_champion_text, flags=re.IGNORECASE).strip()
                        champion_name = re.sub(r'\s+', ' ', champion_name).strip() 

            if champion_name != 'N/A' and champion_name != '':
                champions_data.append({
                    'division': division_name,
                    'fighter_name': champion_name,
                    'rank': 'C', # Assign 'C' for Champion
                    'notes': 'Current Champion'
                })

df_champions = pd.DataFrame(champions_data, columns=['division', 'fighter_name', 'rank', 'notes'])

if not df_champions.empty:
    df_champions = df_champions[~df_champions['division'].str.contains('Pound-for-Pound', case=False)].copy()
    df_champions['rank'] = '0'
    df_champions['notes'] = df_champions.apply(
        lambda row: 'Champion' if 'Vacant' not in row['fighter_name'] else row['notes'],
        axis=1
    )
else:
    df_champions = pd.DataFrame(columns=['division', 'fighter_name', 'rank', 'notes'])


df_combined = pd.concat([df_rankings, df_champions], ignore_index=True)

# Convert 'rank' to numeric, replacing 'NR' with a large number for sorting purposes
df_combined['rank'] = df_combined['rank'].replace({'NR': 999, 'C': 0}).astype(int)

df_combined = df_combined.sort_values(by=['division', 'rank'])

from datetime import datetime

current_datetime = datetime.now()
formatted_datetime = current_datetime.strftime("%Y-%m-%d")

df_combined['Date'] = formatted_datetime

df_combined_renamed = df_combined.rename(columns={
    'Date': 'Date',
    'division': 'Division',
    'fighter_name': 'Fighter',
    'rank': 'Ranking',
    'notes': 'Notes'
})

# Reorder the columns
df_combined = df_combined_renamed[['Date', 'Division', 'Fighter', 'Ranking', 'Notes']]

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



#Read in existing csv from repository
existing_csv = pd.read_csv('datasets/UFC_Rankings.csv')

#Combine the existing csv with the new data
combined = pd.concat([existing_csv, df_combined], ignore_index=False)

combined.loc[combined['Ranking'] == 'Champion', 'Ranking'] = 0
combined.loc[combined['Ranking'] == 0, 'Notes'] = 'Champion'

combined['Division'] = pd.Categorical(combined['Division'], categories=divisions, ordered=True)
combined['Ranking'] = pd.to_numeric(combined['Ranking'], errors='coerce')
combined = combined.dropna(subset=['Ranking']).copy()
combined['Ranking'] = combined['Ranking'].astype(int)

#Sort values and convert back to a csv
combined = combined.sort_values(by=['Date', 'Division', 'Ranking'], ascending=[False, True, True])





combined.to_csv('datasets/UFC_Rankings.csv', index=False)





# Get the max date from the DataFrame
max_date = df_combined['Date'].max()
df_combined = df_combined[df_combined['Date'] == max_date].copy()

# DataFrame with divisions containing "women's"
df_women = df_combined[df_combined['Division'].str.lower().str.contains("women's")].copy()

# DataFrame with divisions NOT containing "women's"
df_men = df_combined[~df_combined['Division'].str.lower().str.contains("women's")].copy()

# Fill NaN values with empty string before processing
df_men['Notes'] = df_men['Notes'].fillna('')
df_women['Notes'] = df_women['Notes'].fillna('')

# Clean notes
df_men['Notes'] = df_men['Notes'].replace({
    'Rank increased by': '▲',
    'Rank decreased by': '▼'
}, regex=True)

df_women['Notes'] = df_women['Notes'].replace({
    'Rank increased by': '▲',
    'Rank decreased by': '▼'
}, regex=True)

# Create combined column
df_men['Combined'] = df_men['Fighter'] + '\t' + df_men['Notes']
df_women['Combined'] = df_women['Fighter'] + '\t' + df_women['Notes']

# Remove the 'Date' and 'Notes' columns
df_women = df_women.drop(columns=['Date', 'Notes', 'Fighter'])
df_men = df_men.drop(columns=['Date', 'Notes', 'Fighter'])

# Convert Ranking to numeric, coerce non-numeric values to NaN
df_men['Ranking'] = pd.to_numeric(df_men['Ranking'], errors='coerce')
df_women['Ranking'] = pd.to_numeric(df_women['Ranking'], errors='coerce')

# Sort by Division and Ranking
df_men = df_men.sort_values(['Division', 'Ranking']).reset_index(drop=True)
df_women = df_women.sort_values(['Division', 'Ranking']).reset_index(drop=True)

# Add an index field that counts up for each division group
df_men['Rank'] = df_men.groupby('Division').cumcount()
df_women['Rank'] = df_women.groupby('Division').cumcount()

# Replace only the leading '0  Champion' or '1  Interim' with 'Champion' or 'Interim'
df_men['Combined'] = df_men['Combined'].str.replace(r'Champion$', '(C)', regex=True)
df_men['Combined'] = df_men['Combined'].str.replace(r'interim$', '(I)', regex=True)

df_women['Combined'] = df_women['Combined'].str.replace(r'Champion$', '(C)', regex=True)
df_women['Combined'] = df_women['Combined'].str.replace(r'interim$', '(I)', regex=True)

# Now pivot using Rank as the index
df_men_pivot = df_men.pivot_table(index='Rank', columns='Division', values='Combined', aggfunc='first')
df_women_pivot = df_women.pivot_table(index='Rank', columns='Division', values='Combined', aggfunc='first')

# Fill NaN values with empty strings
df_men_pivot = df_men_pivot.fillna('')
df_women_pivot = df_women_pivot.fillna('')

df_men_pivot = df_men_pivot.reindex(columns=['Flyweight', 'Bantamweight', 'Featherweight', 'Lightweight', 'Welterweight', 'Middleweight', 'Light Heavyweight', 'Heavyweight'], fill_value='')
df_women_pivot = df_women_pivot.reindex(columns=["Women's Strawweight", "Women's Flyweight", "Women's Bantamweight"], fill_value='')

df_men_pivot = df_men_pivot.reset_index(drop=True)
df_women_pivot = df_women_pivot.reset_index(drop=True)
# Split df_men_pivot into light and heavy divisions
light_divisions = ['Flyweight', 'Bantamweight', 'Featherweight', 'Lightweight']
heavy_divisions = ['Welterweight', 'Middleweight', 'Light Heavyweight', 'Heavyweight']

df_men_light = df_men_pivot[light_divisions]
df_men_heavy = df_men_pivot[heavy_divisions]
# Create the header for the README file
header = f"## UFC Rankings as of {max_date}\n\n"

with open("README.md", "w") as f:
    f.write(header)
    f.write("### Men's Light Divisions\n\n")
    f.write(df_men_light.to_markdown())
    f.write("### Men's Heavy Divisions\n\n")
    f.write(df_men_heavy.to_markdown())
    f.write("\n\n### Women's Divisions\n\n")
    f.write(df_women_pivot.to_markdown())
    f.write("\n")


print(f"README.md has been updated with the latest UFC rankings as of {max_date}")