#!/usr/bin/env python3
"""
GitHub Streak CLI App
A simple CLI tool to track your GitHub contribution streaks.
"""

import argparse
import sys
from datetime import datetime, timedelta
from collections import defaultdict
from ghapi.all import GhApi
import os

class GitHubStreakTracker:
    def __init__(self, token=None, username=None):
        """Initialize the GitHub API client."""
        self.token = token or os.getenv('GITHUB_TOKEN')
        self.username = username

        if not self.token:
            raise ValueError("GitHub token is required. Set GITHUB_TOKEN environment variable or pass it directly.")

        self.api = GhApi(token=self.token)

        # Get authenticated user info if username not provided
        if not self.username:
            user_info = self.api.users.get_authenticated()
            self.username = user_info.login

    def get_all_activity_dates(self, days_back=365):
        """Get all GitHub activity dates including commits, repos, issues, PRs, etc."""
        activity_dates = defaultdict(list)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        print(f"Fetching GitHub activity for {self.username}...")

        # Get commit dates
        commit_dates = self.get_commit_dates(days_back)
        for date in commit_dates:
            activity_dates[date].append('commit')

        # Get repository creation dates
        repo_dates = self.get_repository_dates(start_date, end_date)
        for date in repo_dates:
            activity_dates[date].append('repo')

        # Get issues and PR dates
        issue_dates = self.get_issue_dates(start_date, end_date)
        for date in issue_dates:
            activity_dates[date].append('issue')

        pr_dates = self.get_pr_dates(start_date, end_date)
        for date in pr_dates:
            activity_dates[date].append('pr')

        # Get release dates
        release_dates = self.get_release_dates(start_date, end_date)
        for date in release_dates:
            activity_dates[date].append('release')

        return activity_dates

    def get_commit_dates(self, days_back=365):
        """Get all commit dates for the user within the specified time range."""
        commit_dates = set()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        print("📝 Fetching commits...")
        processed_repos = 0
        skipped_repos = 0

        try:
            # Get all repositories for the user
            repos = self.api.repos.list_for_user(self.username, per_page=100)

            for repo in repos:
                try:
                    # Skip forks unless they have commits from the user
                    if repo.fork:
                        skipped_repos += 1
                        continue

                    # Skip empty repositories
                    if repo.size == 0:
                        skipped_repos += 1
                        continue

                    # Get commits from the repository
                    commits = self.api.repos.list_commits(
                        owner=self.username,
                        repo=repo.name,
                        author=self.username,
                        since=start_date.isoformat(),
                        until=end_date.isoformat(),
                        per_page=100
                    )

                    for commit in commits:
                        commit_date = datetime.fromisoformat(
                            commit.commit.author.date.replace('Z', '+00:00')
                        ).date()
                        commit_dates.add(commit_date)

                    processed_repos += 1

                except Exception as e:
                    # Handle specific error cases
                    error_msg = str(e)
                    if "Git Repository is empty" in error_msg or "409" in error_msg:
                        # Silently skip empty repositories
                        skipped_repos += 1
                    elif "404" in error_msg:
                        # Repository not found or no access
                        skipped_repos += 1
                    else:
                        # Other errors - show warning but continue
                        print(f"Warning: Could not access {repo.name}: {e}")
                        skipped_repos += 1
                    continue

        except Exception as e:
            print(f"Error fetching repositories: {e}")
            return set()

        print(f"   ✅ Processed {processed_repos} repositories ({skipped_repos} skipped)")
        return commit_dates

    def get_repository_dates(self, start_date, end_date):
        """Get dates when repositories were created."""
        repo_dates = set()
        print("📁 Fetching repository creations...")

        try:
            repos = self.api.repos.list_for_user(self.username, per_page=100)
            count = 0

            for repo in repos:
                if repo.fork:
                    continue

                created_date = datetime.fromisoformat(
                    repo.created_at.replace('Z', '+00:00')
                ).date()

                if start_date.date() <= created_date <= end_date.date():
                    repo_dates.add(created_date)
                    count += 1

            print(f"   ✅ Found {count} repository creations")

        except Exception as e:
            print(f"   ❌ Error fetching repositories: {e}")

        return repo_dates

    def get_issue_dates(self, start_date, end_date):
        """Get dates when issues were created."""
        issue_dates = set()
        print("🐛 Fetching issue creations...")

        try:
            # Search for issues created by the user
            query = f"author:{self.username} type:issue created:>={start_date.date()}"
            issues = self.api.search.issues_and_pull_requests(query, per_page=100)

            count = 0
            for issue in issues.items:
                if not issue.pull_request:  # Make sure it's an issue, not a PR
                    created_date = datetime.fromisoformat(
                        issue.created_at.replace('Z', '+00:00')
                    ).date()
                    issue_dates.add(created_date)
                    count += 1

            print(f"   ✅ Found {count} issue creations")

        except Exception as e:
            print(f"   ❌ Error fetching issues: {e}")

        return issue_dates

    def get_pr_dates(self, start_date, end_date):
        """Get dates when pull requests were created."""
        pr_dates = set()
        print("🔀 Fetching pull request creations...")

        try:
            # Search for PRs created by the user
            query = f"author:{self.username} type:pr created:>={start_date.date()}"
            prs = self.api.search.issues_and_pull_requests(query, per_page=100)

            count = 0
            for pr in prs.items:
                if pr.pull_request:  # Make sure it's a PR
                    created_date = datetime.fromisoformat(
                        pr.created_at.replace('Z', '+00:00')
                    ).date()
                    pr_dates.add(created_date)
                    count += 1

            print(f"   ✅ Found {count} pull request creations")

        except Exception as e:
            print(f"   ❌ Error fetching pull requests: {e}")

        return pr_dates

    def get_release_dates(self, start_date, end_date):
        """Get dates when releases were created."""
        release_dates = set()
        print("🚀 Fetching release creations...")

        try:
            repos = self.api.repos.list_for_user(self.username, per_page=100)
            count = 0

            for repo in repos:
                if repo.fork:
                    continue

                try:
                    releases = self.api.repos.list_releases(
                        owner=self.username,
                        repo=repo.name,
                        per_page=100
                    )

                    for release in releases:
                        created_date = datetime.fromisoformat(
                            release.created_at.replace('Z', '+00:00')
                        ).date()

                        if start_date.date() <= created_date <= end_date.date():
                            release_dates.add(created_date)
                            count += 1

                except Exception:
                    # Skip repositories where we can't access releases
                    continue

            print(f"   ✅ Found {count} release creations")

        except Exception as e:
            print(f"   ❌ Error fetching releases: {e}")

        return release_dates

    def calculate_streaks(self, activity_dates):
        """Calculate current and previous streaks from activity dates."""
        if not activity_dates:
            return 0, 0, None

        # Get just the dates (keys) and sort in descending order
        date_set = set(activity_dates.keys())
        sorted_dates = sorted(date_set, reverse=True)
        today = datetime.now().date()

        streaks = []
        current_streak = 0

        # Check if there's activity today or yesterday (current streak)
        if today in date_set or (today - timedelta(days=1)) in date_set:
            current_date = today if today in date_set else today - timedelta(days=1)
            current_streak = 1

            # Count backwards for current streak
            check_date = current_date - timedelta(days=1)
            while check_date in date_set:
                current_streak += 1
                check_date -= timedelta(days=1)

        # Find all streaks by grouping consecutive dates
        if sorted_dates:
            streak_start = sorted_dates[0]
            streak_length = 1

            for i in range(1, len(sorted_dates)):
                if sorted_dates[i-1] - sorted_dates[i] == timedelta(days=1):
                    streak_length += 1
                else:
                    streaks.append(streak_length)
                    streak_length = 1

            streaks.append(streak_length)

        # Find previous streak (largest streak that's not the current one)
        previous_streak = 0
        previous_streak_end = None

        if current_streak > 0 and len(streaks) > 1:
            # Remove current streak from consideration
            other_streaks = streaks[1:] if streaks[0] == current_streak else streaks
            if other_streaks:
                previous_streak = max(other_streaks)
        elif current_streak == 0 and streaks:
            # No current streak, so the most recent is the previous
            previous_streak = streaks[0]
            # Find when this streak ended
            most_recent_date = max(date_set)
            days_since_last_activity = (today - most_recent_date).days
            previous_streak_end = days_since_last_activity

        return current_streak, previous_streak, previous_streak_end

    def display_streak_info(self):
        """Display current and previous streak information."""
        print(f"\n🔥 GitHub Streak Information for {self.username}")
        print("=" * 50)

        # Get all activity dates for the last year
        activity_dates = self.get_all_activity_dates(days_back=365)

        if not activity_dates:
            print("❌ No GitHub activity found in the last 365 days.")
            return

        current_streak, previous_streak, days_since_last = self.calculate_streaks(activity_dates)

        # Display current streak
        print(f"\n📊 Current Streak:")
        if current_streak > 0:
            print(f"   🔥 {current_streak} days and counting!")
            print(f"   💪 Keep it up!")
        else:
            print(f"   💔 No current streak")
            if days_since_last:
                print(f"   ⏰ Last activity was {days_since_last} days ago")

        # Display previous streak
        print(f"\n📈 Previous Best Streak:")
        if previous_streak > 0:
            print(f"   🏆 {previous_streak} days")
            if current_streak == 0 and days_since_last:
                print(f"   📅 Ended {days_since_last} days ago")
        else:
            print(f"   📝 No previous streak found")

        # Display total activity
        total_active_days = len(activity_dates)
        activity_counts = defaultdict(int)
        for activities in activity_dates.values():
            for activity in activities:
                activity_counts[activity] += 1

        print(f"\n📋 Summary (Last 365 days):")
        print(f"   📅 Total active days: {total_active_days}")
        print(f"   📊 Activity rate: {total_active_days/365*100:.1f}%")
        print(f"\n📈 Activity Breakdown:")

        activity_emojis = {
            'commit': '📝',
            'repo': '📁',
            'issue': '🐛',
            'pr': '🔀',
            'release': '🚀'
        }

        for activity_type, count in activity_counts.items():
            emoji = activity_emojis.get(activity_type, '📌')
            activity_name = activity_type.replace('_', ' ').title()
            if activity_type == 'pr':
                activity_name = 'Pull Requests'
            elif activity_type == 'repo':
                activity_name = 'Repositories Created'
            elif activity_type == 'issue':
                activity_name = 'Issues Created'
            elif activity_type == 'release':
                activity_name = 'Releases Created'
            elif activity_type == 'commit':
                activity_name = 'Commit Days'

            print(f"   {emoji} {activity_name}: {count}")

        # Show recent activity with details
        recent_dates = sorted([d for d in activity_dates.keys() if d >= datetime.now().date() - timedelta(days=7)], reverse=True)
        if recent_dates:
            print(f"\n🗓️  Recent activity (last 7 days):")
            for date in recent_dates:
                days_ago = (datetime.now().date() - date).days
                activities = activity_dates[date]

                # Format activity types
                activity_str = []
                for activity in set(activities):  # Remove duplicates
                    count = activities.count(activity)
                    emoji = activity_emojis.get(activity, '📌')
                    if count > 1:
                        activity_str.append(f"{emoji}{activity}({count})")
                    else:
                        activity_str.append(f"{emoji}{activity}")

                activity_display = " ".join(activity_str)

                if days_ago == 0:
                    print(f"   ✅ Today ({date}): {activity_display}")
                elif days_ago == 1:
                    print(f"   ✅ Yesterday ({date}): {activity_display}")
                else:
                    print(f"   ✅ {days_ago} days ago ({date}): {activity_display}")

def main():
    parser = argparse.ArgumentParser(description="Track your GitHub contribution streaks")
    parser.add_argument('--token', help='GitHub personal access token (or set GITHUB_TOKEN env var)')
    parser.add_argument('--username', help='GitHub username (defaults to authenticated user)')
    parser.add_argument('--days', type=int, default=365, help='Number of days to look back (default: 365)')

    args = parser.parse_args()

    try:
        tracker = GitHubStreakTracker(token=args.token, username=args.username)
        tracker.display_streak_info()

    except ValueError as e:
        print(f"❌ Error: {e}")
        print("\n💡 To get started:")
        print("1. Create a GitHub personal access token at: https://github.com/settings/tokens")
        print("2. Set it as environment variable: export GITHUB_TOKEN=your_token_here")
        print("3. Or pass it directly: python github_streak.py --token your_token_here")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()