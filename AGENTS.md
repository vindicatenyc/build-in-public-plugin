# Build in Public Plugin

A Claude Code plugin that automatically generates social media posts from coding sessions for the #BuildingInPublic community.

## Project Overview

**Type:** Claude Code Plugin
**Language:** Python 3.8+
**Purpose:** Parse coding session transcripts and generate ready-to-post content for Twitter/X, BlueSky, LinkedIn, Instagram, and Mastodon
**License:** MIT

## Tech Stack

- **Python 3.8+** - Core scripting language
- **JSON/JSONL** - Session data format
- **Claude Code Plugin API** - Hooks, commands, and skills
- **Standard Library Only** - No external dependencies required

## Project Structure

```
build-in-public-plugin/
├── .claude-plugin/
│   ├── plugin.json           # Plugin manifest and metadata
│   └── marketplace.json      # Marketplace listing info
├── commands/
│   ├── generate.md           # /build-in-public:generate command
│   └── preview.md            # /build-in-public:preview command
├── hooks/
│   └── hooks.json            # SessionEnd and Stop event hooks
├── scripts/
│   ├── generate_posts.py     # Main post generation engine (743 lines)
│   ├── session_end_hook.py   # Reminder hook on session end
│   └── activity_logger.py    # Activity tracking hook
├── skills/
│   └── build-in-public/
│       └── SKILL.md          # Auto-activation skill for social media
└── README.md                 # Installation and usage docs
```

## Key Components

### Post Generation Engine (`scripts/generate_posts.py`)

The core script that parses Claude Code session JSONL files and generates social media content.

**Key Features:**
- Privacy-safe path handling (removes absolute paths from output)
- Detects languages, files created/modified, git commits, tests run, errors fixed
- Generates posts in multiple formats and styles
- Supports both markdown and JSON output

**Usage:**
```bash
python3 scripts/generate_posts.py [--session SESSION_ID] [--output DIR] [--json]
```

**Style Options:**
- Twitter: `--twitter-style {devlog,ship,minimal}`
- LinkedIn: `--linkedin-style {professional,story,wins}`

### Hook System

**SessionEnd Hook** (`scripts/session_end_hook.py`):
- Triggers when a coding session ends
- Checks `.session_activity.json` for meaningful work
- Shows reminder to generate posts if session was productive

**Stop Hook** (`scripts/activity_logger.py`):
- Triggers after each assistant response
- Tracks activity metrics in `.session_activity.json`
- Monitors files modified, commits, commands run

### Commands

**`/build-in-public:generate`**
- Parses current or specified session
- Generates posts for all platforms
- Outputs markdown and optional JSON

**`/build-in-public:preview`**
- Shows session activity preview
- Helps decide if content is worth posting

### Skill Auto-Activation

The skill in `skills/build-in-public/SKILL.md` activates when users mention:
- "building in public" or "coding in public"
- Social media platforms (Twitter, X, BlueSky, LinkedIn, Instagram)
- Sharing progress or creating developer content

## Installation

**From Marketplace:**
```bash
/plugin marketplace add https://github.com/vindicatenyc/build-in-public-plugin
/plugin install build-in-public
```

**Local Development:**
```bash
git clone https://github.com/vindicatenyc/build-in-public-plugin.git
/plugin install --plugin-dir /path/to/build-in-public-plugin
```

## Development Commands

### Testing Post Generation
```bash
# Generate from latest session
python3 scripts/generate_posts.py --output . --json

# Generate from specific session
python3 scripts/generate_posts.py --session abc123 --output . --json

# Test different styles
python3 scripts/generate_posts.py --twitter-style devlog --linkedin-style story
```

### Testing Hooks
```bash
# Test session end hook (requires hook input JSON)
echo '{"session_id": "test"}' | python3 scripts/session_end_hook.py

# Test activity logger
echo '{}' | python3 scripts/activity_logger.py
```

### Linting and Formatting
```bash
# Check Python syntax
python3 -m py_compile scripts/*.py

# Run type checking (if mypy installed)
mypy scripts/
```

## Code Conventions

### Python Style
- Follow PEP 8 style guide
- Use type hints (Python 3.8+ syntax)
- Dataclasses for structured data (`SessionHighlight`, `SessionSummary`)
- Comprehensive docstrings for all public functions

### Privacy and Security
- **CRITICAL:** Always use `safe_display_path()` for file paths in output
- **CRITICAL:** Use `safe_project_name()` for project names in output
- Never expose absolute paths or usernames in social media content
- Only share basenames of files, not full paths

### Post Generation
- Keep character counts within platform limits (280 for Twitter, 300 for BlueSky)
- Generate multiple options per format (short, medium, thread, long)
- Include relevant hashtags based on detected tech stack
- Use emojis purposefully (not excessively)

### Error Handling
- All JSON parsing wrapped in try-except
- File operations check existence before reading
- Exit hooks gracefully with `sys.exit(0)` to avoid blocking sessions

## Important Patterns

### Session Data Location
Claude Code stores sessions in JSONL format at:
```
~/.claude/projects/<project-name>/<session-id>.jsonl
```

Each line is a JSON object representing a message (user, assistant, tool_use, tool_result).

### Hook Environment Variables
- `CLAUDE_PLUGIN_ROOT` - Absolute path to plugin directory
- Use this to reference plugin scripts and store temporary data

### Privacy-First Design
The plugin is designed for public sharing, so it:
- Strips absolute paths from all output
- Uses basename-only for files
- Derives safe project names from directory names
- Never exposes usernames or home directory paths

## Common Tasks

### Adding a New Platform
1. Add platform to post format documentation in README
2. Update `generate_posts()` function with new format
3. Add to `format_output()` markdown template
4. Update character limits and style guidelines

### Customizing Hashtags
Edit the hashtag generation in `generate_posts.py`:
```python
hashtags = ['#BuildingInPublic', '#CodingInPublic']
# Add your custom hashtags here
```

### Adding New Session Metrics
1. Add field to `SessionSummary` dataclass
2. Extract metric in `extract_highlights()` function
3. Include in `format_output()` stats table
4. Update JSON output schema

### Disabling Reminders
Remove or comment out the SessionEnd hook in `hooks/hooks.json`:
```json
{
  "SessionEnd": []
}
```

## Output Formats

### Markdown Output
Human-readable file with:
- Multiple options for each platform
- Character counts for each post
- Session statistics table
- Files created and commits list

### JSON Output
Structured data for automation:
```json
{
  "summary": {
    "session_id": "...",
    "project_name": "...",
    "duration_minutes": 45,
    "files_created": ["file.py"],
    "git_commits": ["commit message"],
    "languages_used": ["Python"],
    "total_tool_calls": 32
  },
  "posts": {
    "short": ["tweet 1", "tweet 2"],
    "thread": ["1/5 tweet", "2/5 tweet", ...],
    "medium": ["linkedin post"],
    "long": ["instagram caption"],
    "hashtags": ["#BuildingInPublic", "#Python"]
  }
}
```

## Gotchas and Known Issues

### Path Privacy
- **Always** use `safe_display_path()` and `safe_project_name()` in output
- JSONL files contain absolute paths - must sanitize before sharing

### Session Detection
- If no session specified, uses most recently modified JSONL file
- May not always be the "current" session if multiple projects active

### Hook Timing
- `Stop` hook fires after EVERY assistant response (can be frequent)
- `SessionEnd` hook fires when session explicitly ends (less frequent)
- Activity log persists between responses within same session

### Character Limits
- Twitter: 280 characters (strict)
- BlueSky: 300 characters
- Instagram: No hard limit, but first 125 chars important
- Thread posts must each fit within individual tweet limits

### Language Detection
- Based solely on file extensions
- Won't detect languages from inline code or tool use
- Manual override via `--project-name` if needed

## Extension Points

The plugin is designed for extension:

1. **New post styles** - Add to `generate_posts()` function
2. **Custom filters** - Extend `extract_highlights()` logic
3. **Platform integrations** - Use JSON output with API clients
4. **Analytics** - Parse generated JSON for trending topics
5. **Automation** - Schedule posts using JSON + cron + API clients

## Resources

- [Claude Code Plugin Docs](https://github.com/anthropics/claude-code)
- [Building in Public Guide](https://twitter.com/search?q=%23BuildingInPublic)
- Repository: https://github.com/vindicatenyc/build-in-public-plugin
- Issues: https://github.com/vindicatenyc/build-in-public-plugin/issues

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Follow existing code style and conventions
4. Test post generation with various session types
5. Ensure privacy functions are used for all paths
6. Submit pull request with clear description

## Testing Checklist

Before committing changes:
- [ ] Test with empty/minimal sessions
- [ ] Test with large sessions (100+ tool calls)
- [ ] Verify no absolute paths in output
- [ ] Check character counts for all platforms
- [ ] Test both markdown and JSON output
- [ ] Verify hooks don't crash on invalid input
- [ ] Test with different project directory names
