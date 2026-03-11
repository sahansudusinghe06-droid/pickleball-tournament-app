import gspread
from oauth2client.service_account import ServiceAccountCredentials

GOOGLE_KEY_FILE = "google_key.json"
SHEET_NAME = "SEC Pickleball Tournament Data"

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_KEY_FILE, scope)
client = gspread.authorize(creds)

spreadsheet = client.open(SHEET_NAME)
worksheet = spreadsheet.worksheet("Settings")

worksheet.update("A1:B2", [
    ["Key", "Value"],
    ["test_connection", "SUCCESS"]
])

print("Google Sheet connection worked.")