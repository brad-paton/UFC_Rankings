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
    try:
        df_fights = pd.DataFrame(all_fight_data,columns=['url', 'Event', 'Venue', 'Location'])
    except Exception:
        return None
    
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


def scrape_events_from_page(soup_obj):
    """
    Extracts event names, URLs, and dates from a BeautifulSoup object representing a UFC events page.
    Args:
        soup_obj (BeautifulSoup): The BeautifulSoup object of the page.
    Returns:
        list: A list of dictionaries, each containing 'event_name', 'event_url', and 'event_date'.
    """
    event_data = []
    if soup_obj:
        potential_event_container = soup_obj.find('div', class_='b-statistics__sub-entry')

        if potential_event_container:
            events_table = potential_event_container.find('table', class_='b-statistics__table-events')

            if events_table:
                rows = events_table.find('tbody').find_all('tr')

                for row in rows:
                    # Check if the row contains the specified image. If it does, skip this row.
                    if row.find('img', src='http://1e49bc5171d173577ecd-1323f4090557a33db01577564f60846c.r80.cf1.rackcdn.com/next.png', class_='b-statistics__icon'):
                        continue

                    first_td = row.find('td')
                    if first_td:
                        event_link_tag = first_td.find('a')
                        event_date_tag = first_td.find('span', class_='b-statistics__date')

                        if event_link_tag and event_date_tag:
                            event_name = event_link_tag.text.strip()
                            event_url = event_link_tag['href']
                            event_date = event_date_tag.text.strip()
                            event_data.append({'event_name': event_name, 'event_url': event_url, 'event_date': event_date})
    return event_data

def clean_and_split_numeric(text_content):
    cleaned_text = ' '.join(text_content.split()).replace('\n', ' ')
    parts = cleaned_text.split()
    val1 = int(parts[0]) if parts and parts[0].isdigit() else 0
    val2 = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    return val1, val2

def scrape_fight_details(soup_event_detail):
    """
    Extracts fight details from a BeautifulSoup object of a UFC event detail page.
    Args:
        soup_event_detail (BeautifulSoup): The BeautifulSoup object of the event detail page.
    Returns:
        list: A list of dictionaries, each containing details for one fight.
    """
    fight_details = []
    fights_table = soup_event_detail.find('table', class_='js-fight-table')

    if fights_table:
        rows = fights_table.find('tbody').find_all('tr', class_='b-fight-details__table-row')

        # Define bonus image mappings
        bonus_mapping = {
            'perf.png': 'Performance of the Night',
            'fight.png': 'Fight of the Night',
            'sub.png': 'Submission of the Night',
            'ko.png': 'Knockout of the Night'
        }

        for i, row in enumerate(rows):
            # Check if the row contains the 'next fight' image, which indicates it's not a fight row
            if row.find('img', src='http://1e49bc5171d173577ecd-1323f4090557a33db01577564f60846c.r80.cf1.rackcdn.com/next.png', class_='b-statistics__icon'):
                continue

            cols = row.find_all('td', class_='b-fight-details__table-col')

            if len(cols) < 10: # Ensure we have enough columns for expected data
                continue

            fight_info = {}

            # Fighter names and URLs - 1st column
            fighters_div = cols[1].find_all('p', class_='b-fight-details__table-text')
            if len(fighters_div) == 2:
                fighter1_tag = fighters_div[0].find('a')
                fighter2_tag = fighters_div[1].find('a')
                fight_info['fighter1_name'] = fighter1_tag.text.strip() if fighter1_tag else ''
                fight_info['fighter1_url'] = fighter1_tag['href'] if fighter1_tag else ''
                fight_info['fighter2_name'] = fighter2_tag.text.strip() if fighter2_tag else ''
                fight_info['fighter2_url'] = fighter2_tag['href'] if fighter2_tag else ''
            else:
                fight_info['fighter1_name'] = ''
                fight_info['fighter1_url'] = ''
                fight_info['fighter2_name'] = ''
                fight_info['fighter2_url'] = ''

            # Extract Kd, Str, Td, Sub (columns 2, 3, 4, 5 respectively)
            fight_info['fighter1_kd'], fight_info['fighter2_kd'] = clean_and_split_numeric(cols[2].text)
            fight_info['fighter1_str'], fight_info['fighter2_str'] = clean_and_split_numeric(cols[3].text)
            fight_info['fighter1_td'], fight_info['fighter2_td'] = clean_and_split_numeric(cols[4].text)
            fight_info['fighter1_sub'], fight_info['fighter2_sub'] = clean_and_split_numeric(cols[5].text)

            # Weight class - 6th column
            fight_info['weight_class'] = cols[6].text.strip()

            # Method - 7th column
            fight_info['method'] = cols[7].text.strip()

            # Round - 8th column
            fight_info['round'] = cols[8].text.strip()

            # Time - 9th column
            fight_info['time'] = cols[9].text.strip()

            # Extract bonus information
            fight_info['bonus'] = None

            # Search for img tags based on src attribute, without class
            bonus_images = []
            for keyword in bonus_mapping.keys():
                found_imgs = row.find_all('img', src=lambda s: s and s.endswith(keyword))
                bonus_images.extend(found_imgs)

            for img_tag in bonus_images:
                img_src = img_tag.get('src')
                for key, value in bonus_mapping.items():
                    if img_src and img_src.endswith(key):
                        fight_info['bonus'] = value
                        break
                if fight_info['bonus'] is not None: # Stop searching if a bonus is found
                    break

            # Add championship detection
            fight_info['is_championship'] = 'Championship' if row.find('img', src=lambda s: s and s.endswith('belt.png')) else None

            # Extract fight_details_url from the 'data-link' attribute of the row
            fight_info['fight_details_url'] = row.get('data-link')

            fight_details.append(fight_info)
    return fight_details

def scrape_general_fight_details(soup_fight_detail):
    """
    Extracts general fight details (event name, date, location, decision, referee)
    from a BeautifulSoup object of a UFC fight detail page.
    Args:
        soup_fight_detail (BeautifulSoup): The BeautifulSoup object of the fight detail page.
    Returns:
        dict: A dictionary containing the extracted general fight details.
    """
    general_fight_details = {
        'event_name': '',
        'event_date': '',
        'event_location': '',
        'decision_method': '',
        'referee': ''
    }

    # Extract Event Name
    event_name_tag = soup_fight_detail.find('h2', class_='b-content__title')
    if event_name_tag:
        event_link = event_name_tag.find('a', class_='b-link')
        if event_link:
            general_fight_details['event_name'] = event_link.text.strip()

    # Event Date and Location are NOT on this page. They should be retrieved from df_all_events via merge.
    # The previous attempts to find them on this page were incorrect due to their absence.

    # Extract Decision Method and Referee (found within the fight details section)
    main_container = soup_fight_detail.find('div', class_='b-fight-details__fight')

    if main_container:
        info_paragraphs = main_container.find_all('p', class_='b-fight-details__text')
        for p_tag in info_paragraphs:
            # Search for Method
            # Use a lambda function for string matching to be more flexible with whitespace
            method_label = p_tag.find('i', class_='b-fight-details__label', string=lambda text: text and 'Method:' in text)
            if method_label:
                # Find the next <i> tag that has a 'font-style: normal' attribute (or just any <i> tag if style not present)
                method_value_tag = method_label.find_next_sibling('i', style='font-style: normal')
                if not method_value_tag: # Fallback if specific style not found, try any immediate <i> sibling
                    method_value_tag = method_label.find_next_sibling('i')

                if method_value_tag: # If an <i> tag was found
                    general_fight_details['decision_method'] = method_value_tag.text.strip()
                else: # If no <i> tag, check if the next sibling is text
                    next_s = method_label.next_sibling
                    if next_s and isinstance(next_s, str): # Check if it's a string (text node)
                        general_fight_details['decision_method'] = next_s.strip()

            # Search for Referee
            # Use a lambda function for string matching to be more flexible with whitespace
            referee_label = p_tag.find('i', class_='b-fight-details__label', string=lambda text: text and 'Referee:' in text)
            if referee_label:
                # Find the next <span> tag
                referee_value_tag = referee_label.find_next_sibling('span')
                if referee_value_tag: # If a <span> tag was found
                    general_fight_details['referee'] = referee_value_tag.text.strip()
                else: # If no <span> tag, check if the next sibling is text
                    next_s = referee_label.next_sibling
                    if next_s and isinstance(next_s, str): # Check if it's a string (text node)
                        general_fight_details['referee'] = next_s.strip()

    return general_fight_details

def parse_strike_attempt_data(text):
    """
    Parses text like '4 of 18' into (landed, attempted) integers.
    Returns (0, 0) if parsing fails.
    """
    if not text or 'of' not in text:
        return 0, 0
    parts = text.split(' of ')
    try:
        landed = int(parts[0].strip())
        attempted = int(parts[1].strip())
        return landed, attempted
    except ValueError:
        return 0, 0

def parse_percentage(text):
    """
    Parses text like '22%' into an integer percentage. Returns 0 if parsing fails.
    """
    if not text or '%' not in text:
        return 0
    try:
        return int(text.replace('%', '').strip())
    except ValueError:
        return 0

def parse_control_time(text):
    """
    Parses control time text 'MM:SS' into total seconds.
    Returns 0 if parsing fails or '---'.
    """
    if not text or text == '---':
        return 0
    try:
        minutes, seconds = map(int, text.split(':'))
        return minutes * 60 + seconds
    except ValueError:
        return 0

def scrape_round_by_round_stats(soup_fight_detail):
    """
    Extracts round-by-round fight statistics from a BeautifulSoup object of a UFC fight detail page.
    Args:
        soup_fight_detail (BeautifulSoup): The BeautifulSoup object of the fight detail page.
    Returns:
        list: A list of dictionaries, each containing detailed stats for one fighter in one round.
    """
    all_round_stats = []
    # Find the first table with this class (general stats)
    fight_details_table = soup_fight_detail.find('table', class_='b-fight-details__table js-fight-table')

    if not fight_details_table:
        return []

    rows = fight_details_table.find('tbody').find_all(['thead', 'tr'])

    current_round = 0
    fighter_names = ['', ''] # To store names for the current round

    for row in rows:
        if 'b-fight-details__table-row_type_head' in row.get('class', []):
            # This is a round header row
            current_round_text = row.find('th').text.strip()
            if 'Round' in current_round_text:
                current_round = int(current_round_text.split(' ')[1])
            continue

        if 'b-fight-details__table-row' in row.get('class', []):
            # This is a data row
            cols = row.find_all('td', class_='b-fight-details__table-col')
            if not cols or len(cols) < 10: # Ensure enough columns
                continue

            # Extract fighter names from the first column
            fighter_divs = cols[0].find_all('p', class_='b-fight-details__table-text')
            if len(fighter_divs) == 2:
                fighter_names[0] = fighter_divs[0].find('a').text.strip()
                fighter_names[1] = fighter_divs[1].find('a').text.strip()
            else:
                continue # Skip if fighter names can't be parsed correctly

            # Extract data for fighter 1 and fighter 2
            for i in range(2):
                fighter_stats = {'round': current_round, 'fighter_name': fighter_names[i]}

                # KD (Column 2)
                kd_text = cols[1].find_all('p', class_='b-fight-details__table-text')[i].text.strip()
                fighter_stats['kd'] = int(kd_text) if kd_text.isdigit() else 0

                # Sig. str. (Column 3)
                sig_str_landed, sig_str_attempted = parse_strike_attempt_data(cols[2].find_all('p', class_='b-fight-details__table-text')[i].text.strip())
                fighter_stats['sig_str_landed'] = sig_str_landed
                fighter_stats['sig_str_attempted'] = sig_str_attempted

                # Sig. str. % (Column 4)
                fighter_stats['sig_str_percent'] = parse_percentage(cols[3].find_all('p', class_='b-fight-details__table-text')[i].text.strip())

                # Total str. (Column 5)
                total_str_landed, total_str_attempted = parse_strike_attempt_data(cols[4].find_all('p', class_='b-fight-details__table-text')[i].text.strip())
                fighter_stats['total_str_landed'] = total_str_landed
                fighter_stats['total_str_attempted'] = total_str_attempted

                # Td (Column 6)
                td_landed, td_attempted = parse_strike_attempt_data(cols[5].find_all('p', class_='b-fight-details__table-text')[i].text.strip())
                fighter_stats['td_landed'] = td_landed
                fighter_stats['td_attempted'] = td_attempted

                # Td % (Column 7)
                fighter_stats['td_percent'] = parse_percentage(cols[6].find_all('p', class_='b-fight-details__table-text')[i].text.strip())

                # Sub. att (Column 8)
                sub_att_text = cols[7].find_all('p', class_='b-fight-details__table-text')[i].text.strip()
                fighter_stats['sub_att'] = int(sub_att_text) if sub_att_text.isdigit() else 0

                # Rev. (Column 9)
                rev_text = cols[8].find_all('p', class_='b-fight-details__table-text')[i].text.strip()
                fighter_stats['rev'] = int(rev_text) if rev_text.isdigit() else 0

                # Ctrl (Column 10)
                fighter_stats['control_time_seconds'] = parse_control_time(cols[9].find_all('p', class_='b-fight-details__table-text')[i].text.strip())

                all_round_stats.append(fighter_stats)

    return all_round_stats

def scrape_detailed_strike_stats(soup_fight_detail):
    """
    Extracts detailed strike location statistics (Head, Body, Leg, Distance, Clinch, Ground)
    from the second table with class 'b-fight-details__table js-fight-table'.
    Args:
        soup_fight_detail (BeautifulSoup): The BeautifulSoup object of the fight detail page.
    Returns:n        list: A list of dictionaries, each containing detailed strike stats for one fighter in one round.
    """
    all_strike_stats = []
    all_tables = soup_fight_detail.find_all('table', class_='b-fight-details__table js-fight-table')

    strike_detail_table = None
    # Identify the table that contains strike breakdown by checking for 'Head' header
    for table in all_tables:
        header_row = table.find('thead', class_='b-fight-details__table-head_rnd')
        # Use a more robust check for the 'Head' header
        if header_row and header_row.find('th', text=lambda t: t and 'Head' in t.strip()):
            strike_detail_table = table
            break

    if not strike_detail_table:
        return []

    rows = strike_detail_table.find('tbody').find_all(['thead', 'tr'])

    current_round = 0
    fighter_names = ['', '']

    for row in rows:
        if 'b-fight-details__table-row_type_head' in row.get('class', []):
            current_round_text = row.find('th').text.strip()
            if 'Round' in current_round_text:
                current_round = int(current_round_text.split(' ')[1])
            continue

        if 'b-fight-details__table-row' in row.get('class', []):
            cols = row.find_all('td', class_='b-fight-details__table-col')
            # We expect 9 columns in the header for this table:
            # Fighter, Sig. str, Sig. str. %, Head, Body, Leg, Distance, Clinch, Ground
            if not cols or len(cols) < 9:
                continue

            fighter_divs = cols[0].find_all('p', class_='b-fight-details__table-text')
            if len(fighter_divs) == 2:
                fighter_names[0] = fighter_divs[0].find('a').text.strip()
                fighter_names[1] = fighter_divs[1].find('a').text.strip()
            else:
                continue

            for i in range(2):
                fighter_stats = {'round': current_round, 'fighter_name': fighter_names[i]}

                # Head (Column 3)
                head_landed, head_attempted = parse_strike_attempt_data(cols[3].find_all('p', class_='b-fight-details__table-text')[i].text.strip())
                fighter_stats['sig_str_head_landed'] = head_landed
                fighter_stats['sig_str_head_attempted'] = head_attempted

                # Body (Column 4)
                body_landed, body_attempted = parse_strike_attempt_data(cols[4].find_all('p', class_='b-fight-details__table-text')[i].text.strip())
                fighter_stats['sig_str_body_landed'] = body_landed
                fighter_stats['sig_str_body_attempted'] = body_attempted

                # Leg (Column 5)
                leg_landed, leg_attempted = parse_strike_attempt_data(cols[5].find_all('p', class_='b-fight-details__table-text')[i].text.strip())
                fighter_stats['sig_str_leg_landed'] = leg_landed
                fighter_stats['sig_str_leg_attempted'] = leg_attempted

                # Distance (Column 6)
                distance_landed, distance_attempted = parse_strike_attempt_data(cols[6].find_all('p', class_='b-fight-details__table-text')[i].text.strip())
                fighter_stats['sig_str_distance_landed'] = distance_landed
                fighter_stats['sig_str_distance_attempted'] = distance_attempted

                # Clinch (Column 7)
                clinch_landed, clinch_attempted = parse_strike_attempt_data(cols[7].find_all('p', class_='b-fight-details__table-text')[i].text.strip())
                fighter_stats['sig_str_clinch_landed'] = clinch_landed
                fighter_stats['sig_str_clinch_attempted'] = clinch_attempted

                # Ground (Column 8)
                ground_landed, ground_attempted = parse_strike_attempt_data(cols[8].find_all('p', class_='b-fight-details__table-text')[i].text.strip())
                fighter_stats['sig_str_ground_landed'] = ground_landed
                fighter_stats['sig_str_ground_attempted'] = ground_attempted

                all_strike_stats.append(fighter_stats)
    return all_strike_stats

