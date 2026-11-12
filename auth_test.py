# auth_test.py — Step 1 ka test: OAuth login + mera channel + latest 20 comments
# NOTE: client_secret.json aur token.json ka content KABHI print nahi karna

import socket  # IPv6 filter ke liye (neeche reason)

# --- IPv4-only workaround: is network par IPv6 route toota hai ---
# httplib2 (YouTube API client) IPv6 try karta hai aur timeout ho jaata hai,
# IPv4 par fallback nahi karta. Isliye getaddrinfo se sirf IPv4 hi lene do.
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_only(*args, **kwargs):
    # Har DNS answer me se sirf IPv4 (AF_INET) records rakh do
    return [r for r in _orig_getaddrinfo(*args, **kwargs) if r[0] == socket.AF_INET]


socket.getaddrinfo = _ipv4_only  # ab process me sab IPv4 se hi connect karenge

import os  # token.json exist check ke liye
import sys  # console encoding ke liye

# Windows console cp1252 use karta hai jo emoji/Unicode comment nahi padh sakta
# (UnicodeEncodeError aata tha) — UTF-8 + replace se kuch bhi crash nahi karega
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from google.auth.transport.requests import Request  # expired token ko refresh karne ke liye
from google.oauth2.credentials import Credentials  # saved token (token.json) padhne ke liye
from google_auth_oauthlib.flow import InstalledAppFlow  # naya OAuth login chalata hai (browser kholta hai)
from googleapiclient.discovery import build  # YouTube API ka client banata hai

# Scope = permission. force-ssl se comment read + post dono milte hain (baad me reply yahi se jayega)
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


def save_token(creds):
    # Token ko file me save karo — print NAHI, sirf file me
    with open("token.json", "w", encoding="utf-8") as f:
        f.write(creds.to_json())


def get_credentials():
    # --- Case 1: token.json pehle se hai (purana login) ---
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)  # token padho
        if creds.valid:
            return creds  # token abhi bhi valid hai — browser BILKUL nahi khulega
        if creds.refresh_token:
            creds.refresh(Request())  # token expired hai — bina browser ke naya token le lo
            save_token(creds)  # refreshed token wapas file me save
            return creds

    # --- Case 2: pehli baar chala rahe ho — browser khulega, tum approve karoge ---
    flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
    creds = flow.run_local_server(port=0)  # local server start + browser window khulta hai
    save_token(creds)  # token.json me save — agli baar yahi se login, browser nahi
    return creds


def main():
    creds = get_credentials()  # login ya purana token restore hua

    # YouTube API client banao (auth ke saath)
    youtube = build("youtube", "v3", credentials=creds)

    # --- Step 3: mera channel ka naam + id ---
    # mine=true = sirf logged-in account ka channel laata hai
    ch = youtube.channels().list(part="snippet", mine=True).execute()
    items = ch.get("items", [])  # channel mila ya nahi (khali list ho sakti hai)
    if not items:
        print("Koi channel nahi mila — is account se YouTube channel banao tabhi chalega")
        return
    name = items[0]["snippet"]["title"]  # channel ka naam
    channel_id = items[0]["id"]  # channel id (UC wali)
    print(f"Channel: {name} | ID: {channel_id}")

    # --- Step 4: is channel ke latest 20 comments ---
    resp = youtube.commentThreads().list(
        part="snippet",  # comment ka content chahiye
        allThreadsRelatedToChannelId=channel_id,  # is channel ki videos ke sab comment threads
        maxResults=20,  # sirf 20 comment
        order="time",  # naye sabse pehle (latest first)
    ).execute()

    threads = resp.get("items", [])  # comments mile ya khali list
    if not threads:
        print("Koi comment nahi mila (comments disabled ho sakti hain)")
        return

    print(f"\nLatest {len(threads)} comments:")
    for t in threads:
        top = t["snippet"]["topLevelComment"]["snippet"]  # thread ka top-level comment
        video_id = t["snippet"]["videoId"]  # kis video par comment hai
        comment_id = t["id"]  # comment id (baad me isipe reply post hoga)
        author = top["authorDisplayName"]  # comment karne wala
        # Text ko ek line me + 100 char tak kaato taaki output saaf rahe
        text = top["textOriginal"].replace("\n", " ")[:100]
        print(f"  video={video_id} | comment={comment_id} | author={author} | text={text}")


if __name__ == "__main__":
    main()  # script yahan se shuru hota hai
