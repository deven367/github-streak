from datetime import date, timedelta
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_contributions(username, days=365):
    # GitHub GraphQL API to get contribution calendar
    token = os.getenv('GITHUB_TOKEN')

    if not token:
        print("Warning: No GITHUB_TOKEN found. API rate limits will be very restrictive.")
        print("To fix this, set your token: export GITHUB_TOKEN=your_token_here")
        print("You can create a token at: https://github.com/settings/tokens")
        print()

    from_date = (date.today() - timedelta(days=days)).isoformat() + "T00:00:00Z"
    to_date = date.today().isoformat() + "T23:59:59Z"

    query = f"""
    query {{
      user(login: "{username}") {{
        contributionsCollection(from: "{from_date}", to: "{to_date}") {{
          contributionCalendar {{
            weeks {{
              contributionDays {{
                date
                contributionCount
              }}
            }}
          }}
        }}
      }}
    }}
    """

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    } if token else {"Content-Type": "application/json"}

    try:
        response = requests.post(
            "https://api.github.com/graphql",
            json={"query": query},
            headers=headers
        )
        response.raise_for_status()
        result = response.json()

        if 'errors' in result:
            raise Exception(f"GraphQL Error: {result['errors']}")

        days_data = []
        for week in result['data']['user']['contributionsCollection']['contributionCalendar']['weeks']:
            for day in week['contributionDays']:
                days_data.append({
                    "date": day["date"],
                    "count": day["contributionCount"]
                })
        return sorted(days_data, key=lambda x: x["date"], reverse=True)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            raise Exception("GitHub API rate limit exceeded. Please set GITHUB_TOKEN environment variable.")
        raise

def analyze_streaks(days_data):
    current_streak = 0
    previous_streak = 0
    gap_found = False
    last_active_day = None

    for i, day in enumerate(days_data):
        if day['count'] > 0:
            if not gap_found:
                current_streak += 1
            else:
                previous_streak += 1
        else:
            if not gap_found:
                gap_found = True
                last_active_day = days_data[i-1]["date"] if i > 0 else None
            elif previous_streak > 0:
                break

    return {
        "current_streak": current_streak,
        "previous_streak": previous_streak,
        "last_active_day": last_active_day
    }

def main():
    import sys
    if len(sys.argv) != 2:
        print("Usage: ghstreak <github_username>")
        sys.exit(1)

    username = sys.argv[1]
    data = get_contributions(username)
    result = analyze_streaks(data)
    print(f"Current streak: {result['current_streak']} days")
    if result['previous_streak'] > 0:
        print(f"Previous streak: {result['previous_streak']} days, ended on {result['last_active_day']}")
    else:
        print("No previous streak found")

if __name__ == "__main__":
    main()
