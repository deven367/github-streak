# ghstreak

A simple CLI tool to track your GitHub contribution streaks.

## Installation

```bash
pip install ghstreak
```

## Usage

```bash
ghstreak <github_username>
```

Example:

```bash
ghstreak deven367
```

## Authentication

For higher API rate limits, set your GitHub token as an environment variable:

```bash
export GITHUB_TOKEN=your_token_here
```

You can create a personal access token at: <https://github.com/settings/tokens>

## Output

The tool displays:

- Your current contribution streak (consecutive days with contributions)
- Your previous streak (if applicable) and when it ended

## Requirements

- Python >= 3.7
- requests >= 2.25.0
- python-dotenv >= 0.19.0
