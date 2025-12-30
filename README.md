# 📱 Build in Public - Claude Code Plugin

Generate engaging social media posts from your Claude Code sessions for the #BuildingInPublic community.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## What It Does

This plugin automatically tracks your coding sessions and generates ready-to-post content for:

- **Twitter/X** - Short posts (280 chars) and threads
- **BlueSky** - Short posts (300 chars)
- **LinkedIn** - Professional medium-length updates
- **Instagram** - Long-form captions with hashtags
- **Mastodon** - Medium posts with hashtags

## Installation

### From GitHub

```bash
# In Claude Code, run:
/plugin marketplace add https://github.com/vindicatenyc/build-in-public-plugin

# Then install:
/plugin install build-in-public
```

### Local Installation (for development)

```bash
# Clone the repo
git clone https://github.com/vindicatenyc/build-in-public-plugin.git

# In Claude Code, add as local plugin:
/plugin install --plugin-dir /path/to/build-in-public-plugin
```

## Usage

### Generate Posts

After a coding session, run:

```
/build-in-public:generate
```

This will:
1. Parse your current session transcript
2. Extract highlights (commits, files created, bugs fixed, etc.)
3. Generate posts for all platforms
4. Save to `output/build-in-public_[timestamp].md` and `.json` in your project directory

**Note:** Output files are created in the current project's `output/` directory, not in the plugin directory.

### Preview Session

Want to see what happened before generating posts?

```
/build-in-public:preview
```

### Automatic Reminders

The plugin includes a `SessionEnd` hook that reminds you to generate posts when you've had a productive session.

### Project Configuration

**Important:** Add this to each project's `.gitignore` to avoid committing generated posts:

```gitignore
# Build in Public generated posts
output/
build-in-public_*.md
build-in-public_*.json
```

The plugin creates an `output/` directory in your project directory (not the plugin directory) to keep generated files organized and separate from your code.

## Output Example

### Short Post (Twitter/X - No Hashtags)
```
✅ Just shipped: Add user authentication with JWT tokens
```

*Note: Hashtags removed from X/Twitter posts per platform best practices*

### Thread (Twitter/X - Compelling Hook)
```
Tweet 1/6:
Just shipped: Add user authentication with JWT tokens

Thread on how it came together 👇

Tweet 2/6:
💻 Tech stack: Python, FastAPI, PostgreSQL

Tweet 3/6:
📝 New files:
  • auth.py
  • jwt_handler.py
  • user_model.py

Tweet 4/6:
📦 Commits:
  ✅ Add user authentication with JWT tokens
  ✅ Implement refresh token rotation

Tweet 5/6:
🧪 Tests: All passing ✅

Nothing beats that green checkmark feeling.

Tweet 6/6:
What are you building today?
```

*Note: First tweet designed as a hook to drive engagement and thread views*

## Automation Integration

The JSON output is designed for automation tools. Example structure:

```json
{
  "summary": {
    "session_id": "abc123",
    "project_name": "my-api",
    "duration_minutes": 45,
    "files_created": ["auth.py", "jwt_handler.py"],
    "git_commits": ["Add user authentication"],
    "languages_used": ["Python", "SQL"]
  },
  "posts": {
    "short": ["Tweet-ready post 1", "Tweet-ready post 2"],
    "thread": ["Tweet 1/5", "Tweet 2/5", "..."],
    "medium": ["LinkedIn post"],
    "long": ["Instagram caption"],
    "hashtags": ["#BuildingInPublic", "#Python"]
  }
}
```

### Example: Auto-publish with your own script

```python
import json

with open('build-in-public_20250101_120000.json') as f:
    data = json.load(f)

# Post to Twitter
tweet = data['posts']['short'][0]
twitter_client.post(tweet)

# Post to BlueSky
bluesky_client.post(tweet)

# Post to LinkedIn
linkedin_post = data['posts']['medium'][0]
linkedin_client.post(linkedin_post)
```

## Configuration

### Customize Hashtags

Edit `scripts/generate_posts.py` to add your own default hashtags:

```python
hashtags = ['#BuildingInPublic', '#CodingInPublic', '#YourHashtag']
```

### Disable Session End Reminder

Remove or comment out the `SessionEnd` hook in `hooks/hooks.json`:

```json
{
  "SessionEnd": []
}
```

## Plugin Structure

```
build-in-public-plugin/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest
├── commands/
│   ├── generate.md          # /build-in-public:generate
│   └── preview.md           # /build-in-public:preview
├── hooks/
│   └── hooks.json           # SessionEnd and Stop hooks
├── scripts/
│   ├── generate_posts.py    # Main post generation script
│   ├── session_end_hook.py  # Session end reminder
│   └── activity_logger.py   # Activity tracking
├── skills/
│   └── build-in-public/
│       └── SKILL.md         # Auto-activation skill
└── README.md
```

## Requirements

- Claude Code (any recent version)
- Python 3.8+ (for the generation scripts)

## Contributing

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Submit a PR

## License

MIT License - see [LICENSE](LICENSE) for details.

## Credits

Created for the #BuildingInPublic community 🚀

---

**Like this plugin?** Give it a ⭐ on GitHub and share your generated posts!
