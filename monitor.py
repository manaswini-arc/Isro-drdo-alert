import os
import re
import json
import requests
from bs4 import BeautifulSoup

ISRO_URL = "https://isro.gov.in"
DRDO_URL = "https://rac.gov.in"
CUET_URL = "https://cuet.nta.nic.in/"
NTA_MAIN_URL = "https://nta.ac.in/"
STATE_FILE = "state.json"
NTFY_TOPIC = os.getenv("NTFY_TOPIC")

def send_notification(message):
    """Sends a push notification via ntfy.sh."""
    if not NTFY_TOPIC:
        print("Error: NTFY_TOPIC environment variable is missing.")
        return
    print(f"Sending Notification: {message}")
    try:
        requests.post(f"https://ntfy.sh{NTFY_TOPIC}", data=message.encode('utf-8'))
    except Exception as e:
        print(f"Failed to send ntfy message: {e}")

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"isro_seen": [], "drdo_text": "", "cuet_seen": [], "nta_seen": []}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

def check_isro(state):
    print("Checking ISRO Portal...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(ISRO_URL, headers=headers, timeout=15)
        if response.status_code != 200:
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        notices = []
        for link in soup.find_all('a'):
            text = link.get_text()
            if "read more" in text.lower():
                title = link.parent.get_text(separator=" ").strip() if link.parent else text
                title = re.sub(r'\s+', ' ', title)
                if title and title not in notices:
                    notices.append(title)

        new_isro_seen = list(notices)
        old_seen = state.get("isro_seen", [])
        new_items = [n for n in notices if n not in old_seen]
        
        for item in new_items:
            if re.search(r'\bsc\b', item, re.IGNORECASE) and (
                "scientist" in item.lower() or "engineer" in item.lower()):
                send_notification(f"🚨 NEW ISRO SC NOTICE:\n{item}\nURL: {ISRO_URL}")
                
        state["isro_seen"] = new_isro_seen
    except Exception as e:
        print(f"Error checking ISRO: {e}")

def check_drdo(state):
    print("Checking DRDO RAC Portal...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(DRDO_URL, headers=headers, timeout=15)
        if response.status_code != 200:
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        current_lines = [line.strip() for line in soup.get_text().splitlines() if line.strip()]
        
        old_text_raw = state.get("drdo_text", "")
        old_lines = old_text_raw.splitlines() if old_text_raw else []
        new_lines = [line for line in current_lines if line not in old_lines]
        
        for line in new_lines:
            if re.search(r'\bd\b', line, re.IGNORECASE) and "scientist" in line.lower():
                send_notification(f"🚨 NEW DRDO SCIENTIST 'D' NOTICE:\n{line}\nURL: {DRDO_URL}")
            elif "scientist" in line.lower() or "recruitment" in line.lower():
                print(f"General DRDO alteration: {line}")
                send_notification(f"🔔 DRDO Portal Update:\n{line}\nURL: {DRDO_URL}")

        state["drdo_text"] = "\n".join(current_lines)
    except Exception as e:
        print(f"Error checking DRDO: {e}")

def check_cuet(state):
    print("Checking CUET Dedicated Portal...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(CUET_URL, headers=headers, timeout=15)
        if response.status_code != 200:
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        notices = []
        
        for element in soup.find_all(['a', 'li']):
            text = element.get_text().strip()
            text = re.sub(r'\s+', ' ', text)
            if len(text) > 10 and text not in notices:
                if any(k in text.lower() for k in ["notice", "cuet", "registration", "bulletin", "apply"]):
                    notices.append(text)

        old_seen = state.get("cuet_seen", [])
        new_items = [n for n in notices if n not in old_seen]
        
        for item in new_items:
            send_notification(f"🎓 NEW CUET PORTAL UPDATE:\n{item}\nURL: {CUET_URL}")
            
        state["cuet_seen"] = list(notices)
    except Exception as e:
        print(f"Error checking CUET Portal: {e}")

def check_nta_main(state):
    print("Checking Main NTA Announcements Portal...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(NTA_MAIN_URL, headers=headers, timeout=15)
        if response.status_code != 200:
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        nta_notices = []
        
        # Scrapes active marquee lines or public notice sections on the main page
        for element in soup.find_all(['a', 'li', 'p']):
            text = element.get_text().strip()
            text = re.sub(r'\s+', ' ', text)
            if len(text) > 12 and text not in nta_notices:
                # Intentionally filters for general NTA notices relating strictly to CUET
                if "cuet" in text.lower():
                    nta_notices.append(text)

        old_seen = state.get("nta_seen", [])
        new_items = [n for n in nta_notices if n not in old_seen]
        
        for item in new_items:
            send_notification(f"🏛️ OFFICIAL NTA MAIN BOARD ALERT:\n{item}\nURL: {NTA_MAIN_URL}")
            
        state["nta_seen"] = list(nta_notices)
    except Exception as e:
        print(f"Error checking Main NTA Board: {e}")

def main():
    state = load_state()
    check_isro(state)
    check_drdo(state)
    check_cuet(state)
    check_nta_main(state) # Runs the new NTA universal board checker
    save_state(state)

if __name__ == "__main__":
    main()
    
