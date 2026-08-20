import requests, json
FAO_TOKEN = "eyJraWQiOiJVSFE2dmwrekFTaGRpSGpsOFFSK0d2ZW13RWIzSjZNdytYNTRURXZtNUNJPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIzMjI1ZDRkNC1iMDgxLTcwOTItZmZjMi02MDg0ZjViMzMyNGEiLCJpc3MiOiJodHRwczovL2NvZ25pdG8taWRwLmV1LXdlc3QtMS5hbWF6b25hd3MuY29tL2V1LXdlc3QtMV9iTkVMTk9DMnYiLCJ2ZXJzaW9uIjoyLCJjbGllbnRfaWQiOiIyY3NsdHNpZ2FvODVpdmhwNm9qcDFhaWM3byIsIm9yaWdpbl9qdGkiOiIxMmJiM2M4YS02Yzg3LTQxZTMtYTY1Ni04YmI1OTIxM2U0ZDMiLCJldmVudF9pZCI6IjRkZTJlZjcxLWJhNDItNGZhZS1hMzU3LTAwZmJlMGNkMGI0ZiIsInRva2VuX3VzZSI6ImFjY2VzcyIsInNjb3BlIjoiYXdzLmNvZ25pdG8uc2lnbmluLnVzZXIuYWRtaW4gcGhvbmUgb3BlbmlkIHByb2ZpbGUgZW1haWwiLCJhdXRoX3RpbWUiOjE3ODYwMjIzOTUsImV4cCI6MTc4NjAyNTk5NSwiaWF0IjoxNzg2MDIyMzk1LCJqdGkiOiJmNTM3NjE0MC03ZmUyLTRkYzItYThjMC03NDg4MjkyNDVlMmIiLCJ1c2VybmFtZSI6InNhbWVyIn0.KGw9M2ZkeI89DQhlT0rsamgi9TCJ7LqUo7AaB6q7AOuxjvxJj3Q4w6X9W6YG5rp9Zg54HhBdijlQyeFMoThCpLQk0MIxwoj9sjFJl2SyBhFUI7r4llusV86YBUWEOwNSnvOCPjIhmYfqJZA1Wh8UeDclMZqO8kBzvxlPEsSLf1sAlOu5F0tUacTvKLIYQ8RdSE_emP5GYyyCuuvWLJqydismWzZ_HXGYj7DGPYFdU6Ve8BANe7SXqxTyXkaP7vI6trAzTCSk-Sy_TjQKOgEwFpapvK7rzzkT8V2g3EQ0-bKajjOETOk0fuE2kzlOdItdBbI4osN07oJbN2kyMK9T_A"
headers = {"Authorization": "Bearer " + FAO_TOKEN}

# Try fetching data from RP with Tunisia area (222) and item 1331
test_urls = [
    "https://faostatservices.fao.org/api/v1/en/data/RP?item=1331&area=222",
    "https://faostatservices.fao.org/api/v1/en/data/RP?item=1331",
    "https://faostatservices.fao.org/api/v1/en/data/RP?element=5157",
    # Try different domain - EP (Pesticides Use)
    "https://faostatservices.fao.org/api/v1/en/data/EP?element=5157&item=1331&year=2020",
]

for url in test_urls:
    resp = requests.get(url, headers=headers)
    data = resp.json()
    records = len(data.get("data", []))
    print(f"URL: ...{url[-60:]} => {records} records")
    if records > 0:
        print("  Sample:", json.dumps(data["data"][:1], indent=2))
