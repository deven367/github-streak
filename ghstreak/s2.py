#!/usr/bin/env python3
"""
GitHub Streak CLI App
A simple CLI tool to track your GitHub contribution streaks.
"""

import argparse
import sys
from datetime import datetime, timedelta
from ghapi.all import GhApi
import os


class GitHubStreakTracker:
    def __init__(self, token=None, username=None):
        """Initialize the GitHub API client."""
        self.token = token or os.getenv('GITHUB_TOKEN')
        self.username = username

        if not self.token:
            raise ValueError(
                'GitHub token is required. Set GITHUB_TOKEN environment variable'
                'or pass it directly.'
            )

        self.api = GhApi(token=self.token)

        # Get authenticated user info if username not provided
        if not self.username:
            user_info = self.api.users.get_authenticated()
            self.username = user_info.login

    def get_commit_dates(self, days_back=365):
        """Get all commit dates for the user within the specified time range."""
        commit_dates = set()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        print(f'Fetching commits for {self.username}...')
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
                        per_page=100,
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
                    if 'Git Repository is empty' in error_msg or '409' in error_msg:
                        # Silently skip empty repositories
                        skipped_repos += 1
                    elif '404' in error_msg:
                        # Repository not found or no access
                        skipped_repos += 1
                    else:
                        # Other errors - show warning but continue
                        print(f'Warning: Could not access {repo.name}: {e}')
                        skipped_repos += 1
                    continue

        except Exception as e:
            print(f'Error fetching repositories: {e}')
            return set()

        print(f'✅ Processed {processed_repos} repositories ({skipped_repos} skipped)')
        return commit_dates

    def calculate_streaks(self, commit_dates):
        """Calculate current and previous streaks from commit dates."""
        if not commit_dates:
            return 0, 0, None

        # Sort dates in descending order (most recent first)
        sorted_dates = sorted(commit_dates, reverse=True)
        today = datetime.now().date()

        streaks = []
        current_streak = 0

        # Check if there's activity today or yesterday (current streak)
        if today in commit_dates or (today - timedelta(days=1)) in commit_dates:
            current_date = today if today in commit_dates else today - timedelta(days=1)
            current_streak = 1

            # Count backwards for current streak
            check_date = current_date - timedelta(days=1)
            while check_date in commit_dates:
                current_streak += 1
                check_date -= timedelta(days=1)

        # Find all streaks by grouping consecutive dates
        if sorted_dates:
            streak_length = 1

            for i in range(1, len(sorted_dates)):
                if sorted_dates[i - 1] - sorted_dates[i] == timedelta(days=1):
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
            most_recent_date = max(commit_dates)
            days_since_last_commit = (today - most_recent_date).days
            previous_streak_end = days_since_last_commit

        return current_streak, previous_streak, previous_streak_end

    def display_streak_info(self):
        """Display current and previous streak information."""
        print(f'\n🔥 GitHub Streak Information for {self.username}')
        print('=' * 50)

        # Get commit dates for the last year
        commit_dates = self.get_commit_dates(days_back=365)

        if not commit_dates:
            print('❌ No commits found in the last 365 days.')
            return

        current_streak, previous_streak, days_since_last = self.calculate_streaks(
            commit_dates
        )

        # Display current streak
        print('\n📊 Current Streak:')
        if current_streak > 0:
            print(f'   🔥 {current_streak} days and counting!')
            print(f'   💪 Keep it up!')
        else:
            print('   💔 No current streak')
            if days_since_last:
                print(f'   ⏰ Last commit was {days_since_last} days ago')

        # Display previous streak
        print('\n📈 Previous Best Streak:')
        if previous_streak > 0:
            print(f'   🏆 {previous_streak} days')
            if current_streak == 0 and days_since_last:
                print(f'   📅 Ended {days_since_last} days ago')
        else:
            print('   📝 No previous streak found')

        # Display total activity
        total_active_days = len(commit_dates)
        print('\n📋 Summary (Last 365 days):')
        print(f'   📅 Total active days: {total_active_days}')
        print(f'   📊 Activity rate: {total_active_days / 365 * 100:.1f}%')

        # Show recent activity
        recent_dates = sorted(
            [d for d in commit_dates if d >= datetime.now().date() - timedelta(days=7)],
            reverse=True,
        )
        if recent_dates:
            print('\n🗓️  Recent activity (last 7 days):')
            for date in recent_dates:
                days_ago = (datetime.now().date() - date).days
                if days_ago == 0:
                    print(f'   ✅ Today ({date})')
                elif days_ago == 1:
                    print(f'   ✅ Yesterday ({date})')
                else:
                    print(f'   ✅ {days_ago} days ago ({date})')


def main():
    parser = argparse.ArgumentParser(
        description='Track your GitHub contribution streaks'
    )
    parser.add_argument(
        '--token', help='GitHub personal access token (or set GITHUB_TOKEN env var)'
    )
    parser.add_argument(
        '--username', help='GitHub username (defaults to authenticated user)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=365,
        help='Number of days to look back (default: 365)',
    )

    args = parser.parse_args()

    try:
        tracker = GitHubStreakTracker(token=args.token, username=args.username)
        tracker.display_streak_info()

    except ValueError as e:
        print(f'❌ Error: {e}')
        print('\n💡 To get started:')
        print(
            '1. Create a GitHub personal access token at: https://github.com/settings/tokens'
        )
        print('2. Set it as environment variable: export GITHUB_TOKEN=your_token_here')
        print('3. Or pass it directly: python github_streak.py --token your_token_here')
        sys.exit(1)

    except Exception as e:
        print(f'❌ Unexpected error: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
