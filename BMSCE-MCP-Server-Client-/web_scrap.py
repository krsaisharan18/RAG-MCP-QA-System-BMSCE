import re
import json
import requests
from bs4 import BeautifulSoup
from config import WEB_REQUEST_TIMEOUT

def get_news_events():
    """
    Scrape news and events from BMSCE website.
    Uses WEB_REQUEST_TIMEOUT from config.py for request timeout.
    """
    url = "https://bmsce.ac.in"
    try:
        response = requests.get(url, timeout=WEB_REQUEST_TIMEOUT)
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

    except requests.exceptions.RequestException as e:
        error_message = json.dumps({"error": f"Failed to retrieve the webpage: {e}"}, indent=4)
        return error_message

    news_list = []
    articles = soup.select(".col-sm-12.col-md-12.col-lg-12 article")

    for article in articles:
        # Extract date
        day_tag = article.select_one(".post-date .day")
        month_tag = article.select_one(".post-date .month")
        date = f"{day_tag.get_text(strip=True)} {month_tag.get_text(strip=True)}" if day_tag and month_tag else "No date"

        # Extract title
        h4_tag = article.find("h4")
        title = h4_tag.get_text(strip=True) if h4_tag else "No title"

        # Append data as a dictionary to the list
        news_list.append({
            "date": date,
            "title": title
        })
    
    # Convert the list of dictionaries to a JSON string
    return json.dumps(news_list, indent=4)


def get_notifications():
    """
    Scrape notifications from BMSCE website.
    Uses WEB_REQUEST_TIMEOUT from config.py for request timeout.
    """
    url = "https://bmsce.ac.in"
    try:
        response = requests.get(url, timeout=WEB_REQUEST_TIMEOUT)
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

    except requests.exceptions.RequestException as e:
        error_message = json.dumps({"error": f"Failed to retrieve the webpage: {e}"}, indent=4)
        return error_message

    notifications_list = []
    college_tab = soup.find("div", {"id": "CollegeNotifications"})
    
    if not college_tab:
        return json.dumps([{"error": "College notifications section not found."}], indent=4)

    notifications = college_tab.find_all("li", class_="text-justify")

    for li in notifications:
        # Create a copy to avoid modifying the original soup object in the loop
        li_copy = li
        
        # Remove links, icons, and line breaks for clean text
        for tag in li_copy.find_all(["a", "img", "i", "br"]):
            tag.decompose()

        # Extract clean text
        text = li_copy.get_text(strip=True)

        # Extract date using regex
        date_match = re.search(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{4}\b", text)
        date = date_match.group(0) if date_match else "No date found"

        # Append data as a dictionary to the list
        notifications_list.append({
            "notification": text,
            "date": date
        })
        
    # Convert the list of dictionaries to a JSON string
    return json.dumps(notifications_list, indent=4)
