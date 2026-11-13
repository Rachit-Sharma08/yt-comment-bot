# youtube.py — sirf OFFICIAL YouTube Data API v3 (AGENTS.md rule: koi scraping nahi)
# Login code auth_test.py se reuse kiya hai — wahi token.json + client_secret flow

import socket  # IPv4 filter ke liye (neeche reason)

# --- IPv4-only workaround: is network par IPv6 route toota hai ---
# httplib2 (YouTube API client) IPv6 try karta hai aur timeout ho jaata hai,
# IPv4 par fallback nahi karta. Isliye getaddrinfo se sirf IPv4 hi lene do.
# (Ye auth_test.py wala hi code hai — wahan verify ho chuka hai)
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_only(*args, **kwargs):
    # Har DNS answer me se sirf IPv4 (AF_INET) records rakh do
    return [r for r in _orig_getaddrinfo(*args, **kwargs) if r[0] == socket.AF_INET]


socket.getaddrinfo = _ipv4_only  # ab process me sab IPv4 se hi connect karenge

import os  # token.json exist check ke liye
from datetime import datetime, timezone  # comment ki age (purana/naya) nikalne ke liye
from pathlib import Path  # video_notes/<video_id>.md padhne ke liye

from google.auth.transport.requests import Request  # expired token ko refresh karne ke liye
from google.oauth2.credentials import Credentials  # saved token (token.json) padhne ke liye
from google_auth_oauthlib.flow import InstalledAppFlow  # naya OAuth login (browser)
from googleapiclient.discovery import build  # YouTube API ka client banata hai

import config  # MODE, QUOTA_LIMIT padhne ke liye
import db  # quota aur video-cache ka saara hisaab db.py se

# Scope = permission. force-ssl se comment read + post dono milte hain
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

# --- Quota costs (official docs: youtube.commentThreads.list = 1, comments.insert = 50) ---
LIST_COST = 1  # har list-type call (channels/commentThreads/videos)
INSERT_COST = 50  # reply post = 50 units — mehnga hai, isliye limit zaroori

# Service ek hi banegi (baar-baar build = faltu ka kaam)
_service = None


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
            creds.refresh(Request())  # expired — bina browser ke refresh ho jaayega
            save_token(creds)  # refreshed token wapas file me save
            return creds

    # --- Case 2: pehli baar — browser khulega, approve karna padega ---
    flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
    creds = flow.run_local_server(port=0)  # local server + browser window
    save_token(creds)  # token.json me save — agli baar browser nahi
    return creds


def get_service():
    # YouTube API client (auth ke saath) — ek hi baar banao, reuse karo
    global _service
    if _service is None:
        _service = build("youtube", "v3", credentials=get_credentials())
    return _service


def _ensure_quota(cost):
    # Call se PEHLE check: aaj ka budget is call ke baad bhi bacha rahega?
    used = db.quota_used_today()
    if used + cost > config.QUOTA_LIMIT:
        raise RuntimeError(
            f"Quota khatam: aaj {used} units kharch, limit {config.QUOTA_LIMIT} — "
            "aaj ke liye bot ruk jaayega (kal reset hoga)"
        )


def get_my_channel_id():
    # Logged-in account ka channel id (UC...) — iske comments khud ke hain, unhe skip karna hai
    yt = get_service()
    _ensure_quota(LIST_COST)
    resp = yt.channels().list(part="snippet", mine=True).execute()  # sirf mera channel
    db.add_quota(LIST_COST)  # har API call ke BAAD quota record
    items = resp.get("items", [])
    if not items:
        # Is account par YouTube channel bana ho tabhi bot chalega
        raise RuntimeError("Koi channel nahi mila — is account se YouTube channel banao")
    return items[0]["id"]


def _is_too_old(published_at):
    # publishedAt = "2026-11-13T08:30:00Z" (UTC). MAX_COMMENT_AGE_HOURS se purana = skip
    try:
        when = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except ValueError:
        return False  # date parse na ho to fresh maano (galat tarike se reply rokna nahi)
    age_hours = (datetime.now(timezone.utc) - when).total_seconds() / 3600
    return age_hours > config.MAX_COMMENT_AGE_HOURS


def fetch_new_comments(max_results=50):
    """Naye comments list karo (latest pehle) — sirf wo jo actually process karne hain.

    Returns: (comments, skips)
      comments = [{"comment_id", "video_id", "author", "author_channel_id", "text"}, ...]
      skips    = {"too_old": n, "already_replied": n} — inhe db me "skipped" save
                 kar chuka hoon (duplicate rokne ke liye), main.py sirf count dikhaye.
    """
    yt = get_service()
    channel_id = get_my_channel_id()  # apne channel ke comments filter karne ke liye

    _ensure_quota(LIST_COST)
    resp = yt.commentThreads().list(
        part="snippet",  # comment ka content chahiye
        allThreadsRelatedToChannelId=channel_id,  # is channel ki videos ke sab threads
        maxResults=max_results,  # API ki max 100 per page
        order="time",  # naye sabse pehle (latest first)
    ).execute()
    db.add_quota(LIST_COST)  # list = 1 unit

    comments = []
    skips = {}
    for item in resp.get("items", []):
        top = item["snippet"]["topLevelComment"]["snippet"]  # thread ka top-level comment
        comment_id = item["id"]  # isi par baad me reply post hoga
        video_id = item["snippet"]["videoId"]  # kis video par comment hai
        text = top.get("textOriginal", "")  # poora text (filter isi par chalega)

        # Duplicate: db me pehle se save hai (kisi bhi status me) to chhod do
        if db.already_done(comment_id):
            continue

        # Apne channel ke khud ke comments par reply NAHI (AGENTS.md spam rule)
        author_channel_id = top.get("authorChannelId", {}).get("value", "")
        if author_channel_id == channel_id:
            continue

        # Purana comment (24h se zyada) — reply nahi, db me "skipped/too_old"
        if _is_too_old(top.get("publishedAt", "")):
            db.save_reply(comment_id, video_id, text, "", "skipped", "too_old")
            skips["too_old"] = skips.get("too_old", 0) + 1
            continue

        # Thread me pehle se kisi ne reply ki (totalReplyCount > 0) —
        # discussion chal rahi hai, beech me mat chuo. db me "skipped/already_replied"
        if item["snippet"].get("totalReplyCount", 0) > 0:
            db.save_reply(comment_id, video_id, text, "", "skipped", "already_replied")
            skips["already_replied"] = skips.get("already_replied", 0) + 1
            continue

        comments.append({
            "comment_id": comment_id,
            "video_id": video_id,
            "author": top.get("authorDisplayName", ""),
            "author_channel_id": author_channel_id,
            "text": text,
        })
    return comments, skips


def get_video_info(video_id):
    """(title, description) — pehle db cache dekho, tabhi API call karo (quota bache)."""
    cached = db.get_video(video_id)
    if cached:
        return cached  # cache hit — 1 unit bach gayi

    yt = get_service()
    _ensure_quota(LIST_COST)
    resp = yt.videos().list(part="snippet", id=video_id).execute()
    db.add_quota(LIST_COST)  # list = 1 unit
    items = resp.get("items", [])
    if not items:
        # Video delete/private ho sakti hai — khali info de do, crash nahi
        return ("", "")

    sn = items[0]["snippet"]
    title = sn.get("title", "")
    description = sn.get("description", "")
    db.save_video(video_id, title, description)  # agli baar cache se milega
    return (title, description)


def get_video_notes(video_id):
    # Optional notes file: video_notes/<video_id>.md — ho to uska text, warna khali
    path = Path("video_notes") / f"{video_id}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""  # notes optional hain


def post_reply(parent_comment_id, text):
    """comment par reply post karo. Sirf MODE=="auto" — warna error (fail-safe)."""
    # Fail-safe: draft mode me ye function chalega hi nahi — galat call par turant error
    if config.MODE != "auto":
        raise RuntimeError(
            f"post_reply sirf MODE=auto me chalta hai (abhi MODE={config.MODE!r})"
        )

    yt = get_service()
    _ensure_quota(INSERT_COST)  # 50 units — pehle check, warna limit toot jaati hai
    yt.comments().insert(
        part="snippet",
        body={
            "snippet": {
                "parentId": parent_comment_id,  # kis comment par reply
                "textOriginal": text,  # bot ka reply text
            }
        },
    ).execute()
    db.add_quota(INSERT_COST)  # insert = 50 units
