#!/usr/bin/env python3
"""
Build in Public - Social Media Post Generator

Parses Claude Code session transcripts and generates ready-to-post
social media content for Twitter/X, BlueSky, Instagram, LinkedIn, etc.

Usage:
    python generate_posts.py [SESSION_ID_OR_PATH] [--session SESSION_ID_OR_PATH] [--output OUTPUT_DIR]
    
If no session is specified, uses the most recently modified session.
"""

import json
import sys
import os
import re
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any, Set
from dataclasses import dataclass, field


@dataclass
class SessionHighlight:
    """A notable event from the coding session"""
    category: str  # 'feature', 'fix', 'refactor', 'test', 'docs', 'milestone'
    description: str
    files_involved: list = field(default_factory=list)
    commands_run: list = field(default_factory=list)
    timestamp: str = ""


@dataclass
class SessionSummary:
    """Aggregated session data for post generation"""
    session_id: str
    project_name: str
    duration_minutes: int
    highlights: list  # List[SessionHighlight]
    files_created: list
    files_modified: list
    tests_run: bool
    git_commits: list
    errors_fixed: int
    total_tool_calls: int
    languages_used: set = field(default_factory=set)


def safe_display_path(raw_path: str) -> str:
    """
    Privacy-safe display value for a path.

    Claude transcripts often contain absolute paths (e.g. /Users/<name>/...).
    For content meant to be shared publicly, we only keep the basename.
    """
    if not raw_path:
        return ""

    s = str(raw_path).strip().strip('"').strip("'")
    s = s.rstrip("/\\")
    s = s.replace("\\", "/")

    base = s.split("/")[-1] if s else ""
    return base or s


def safe_project_name(raw_project_dir: str, *, fallback: Optional[str] = None) -> str:
    """
    Return a privacy-safe project name.

    Claude's project directory names can encode absolute paths (e.g. Users-jane-dev-my-app),
    which would leak personal path information if used directly. Prefer a safe fallback
    (usually the current working directory name) when available.
    """
    raw = (raw_project_dir or "").strip()
    fb = (fallback or "").strip()

    if fb:
        # If we're running inside the project directory, this is the most accurate + safe.
        return fb

    if not raw:
        return ""

    # Heuristic: if this looks like an encoded path slug, take only a short tail segment
    # to avoid leaking username/home directory structure.
    tokens = [t for t in raw.split("-") if t]
    if len(tokens) >= 4:
        tail = tokens[-4:]
        generic_prefixes = {"dev", "code", "projects", "project", "repos", "repo", "work", "workspace", "src"}
        while tail and tail[0].lower() in generic_prefixes:
            tail = tail[1:]
        return "-".join(tail) or raw

    return raw


def find_claude_projects_dir() -> Path:
    """Locate the Claude Code projects directory"""
    home = Path.home()
    claude_dir = home / ".claude" / "projects"
    if claude_dir.exists():
        return claude_dir
    raise FileNotFoundError(f"Claude projects directory not found at {claude_dir}")


def get_latest_session(project_dir: Optional[Path] = None) -> Tuple[Path, str]:
    """Find the most recently modified session JSONL file"""
    projects_dir = find_claude_projects_dir()
    
    latest_file = None
    latest_mtime = 0
    
    for project_path in projects_dir.iterdir():
        if not project_path.is_dir():
            continue
        for session_file in project_path.glob("*.jsonl"):
            mtime = session_file.stat().st_mtime
            if mtime > latest_mtime:
                latest_mtime = mtime
                latest_file = session_file
    
    if latest_file is None:
        raise FileNotFoundError("No session files found")
    
    # Extract project name from path
    project_dir_name = latest_file.parent.name
    return latest_file, project_dir_name


def parse_session_jsonl(filepath: Path) -> List[Dict[str, Any]]:
    """Parse a Claude Code session JSONL file"""
    messages = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return messages


def extract_highlights(messages: List[Dict[str, Any]]) -> SessionSummary:
    """Extract notable events and statistics from session messages"""
    highlights: List[SessionHighlight] = []
    files_created = set()
    files_modified = set()
    git_commits = []
    errors_fixed = 0
    tests_run = False
    total_tool_calls = 0
    languages_used = set()
    
    # Language detection patterns
    lang_extensions = {
        '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
        '.jsx': 'React', '.tsx': 'React/TypeScript', '.go': 'Go',
        '.rs': 'Rust', '.rb': 'Ruby', '.java': 'Java', '.cpp': 'C++',
        '.c': 'C', '.swift': 'Swift', '.kt': 'Kotlin', '.sql': 'SQL',
        '.html': 'HTML', '.css': 'CSS', '.scss': 'SCSS', '.vue': 'Vue',
        '.svelte': 'Svelte', '.md': 'Markdown', '.json': 'JSON',
        '.yaml': 'YAML', '.yml': 'YAML', '.sh': 'Bash', '.dockerfile': 'Docker'
    }
    
    first_timestamp = None
    last_timestamp = None
    
    for msg in messages:
        # Track timestamps
        if 'timestamp' in msg:
            ts = msg['timestamp']
            if first_timestamp is None:
                first_timestamp = ts
            last_timestamp = ts
        
        # Process tool uses
        if msg.get('type') == 'tool_use' or 'tool_input' in msg:
            total_tool_calls += 1
            tool_name = msg.get('name', msg.get('tool_name', ''))
            tool_input = msg.get('tool_input', msg.get('input', {}))
            
            # File operations
            if tool_name in ('Write', 'Edit', 'MultiEdit', 'create_file', 'str_replace'):
                file_path = tool_input.get('file_path', tool_input.get('path', ''))
                if file_path:
                    safe_path = safe_display_path(file_path)
                    ext = Path(safe_path).suffix.lower()
                    if ext in lang_extensions:
                        languages_used.add(lang_extensions[ext])
                    
                    if tool_name in ('Write', 'create_file'):
                        files_created.add(safe_path)
                    else:
                        files_modified.add(safe_path)
            
            # Bash commands
            elif tool_name == 'Bash':
                command = tool_input.get('command', '')
                
                # Git commits
                if 'git commit' in command:
                    commit_match = re.search(r'-m ["\'](.+?)["\']', command)
                    if commit_match:
                        git_commits.append(commit_match.group(1))
                
                # Test runs
                if any(t in command for t in ['pytest', 'jest', 'npm test', 'cargo test', 'go test', 'rspec']):
                    tests_run = True
        
        # Process assistant messages for context
        if msg.get('type') == 'assistant' or msg.get('role') == 'assistant':
            content = msg.get('content', '')
            if isinstance(content, list):
                content = ' '.join(str(c.get('text', '')) for c in content if isinstance(c, dict))
            
            content_lower = content.lower() if isinstance(content, str) else ''
            
            if 'error' in content_lower and ('fixed' in content_lower or 'resolved' in content_lower):
                errors_fixed += 1
    
    # Calculate duration
    duration_minutes = 0
    if first_timestamp and last_timestamp:
        try:
            # Try to parse ISO format timestamps
            if isinstance(first_timestamp, str):
                first_dt = datetime.fromisoformat(first_timestamp.replace('Z', '+00:00'))
                last_dt = datetime.fromisoformat(last_timestamp.replace('Z', '+00:00'))
                duration_minutes = int((last_dt - first_dt).total_seconds() / 60)
        except (ValueError, TypeError):
            pass
    
    # Create highlights from significant events
    if files_created:
        highlights.append(SessionHighlight(
            category='feature',
            description=f"Created {len(files_created)} new file(s)",
            files_involved=list(files_created)[:5]
        ))
    
    if git_commits:
        for commit in git_commits[:3]:  # Top 3 commits
            highlights.append(SessionHighlight(
                category='milestone',
                description=commit
            ))
    
    if tests_run:
        highlights.append(SessionHighlight(
            category='test',
            description="Ran test suite"
        ))
    
    if errors_fixed > 0:
        highlights.append(SessionHighlight(
            category='fix',
            description=f"Fixed {errors_fixed} error(s)"
        ))
    
    return SessionSummary(
        session_id="",
        project_name="",
        duration_minutes=duration_minutes,
        highlights=highlights,
        files_created=list(files_created),
        files_modified=list(files_modified),
        tests_run=tests_run,
        git_commits=git_commits,
        errors_fixed=errors_fixed,
        total_tool_calls=total_tool_calls,
        languages_used=languages_used
    )


def generate_posts(
    summary: SessionSummary,
    twitter_style: str = "devlog",
    linkedin_style: str = "professional",
) -> dict:
    """Generate social media posts from session summary"""
    posts = {
        'short': [],      # Twitter/X, BlueSky (280 chars)
        'medium': [],     # LinkedIn, Mastodon (500-700 chars)
        'thread': [],     # Twitter/X thread (multiple tweets)
        'long': [],       # Blog snippet, Instagram caption
        'hashtags': []
    }
    
    twitter_style = (twitter_style or "devlog").strip().lower()
    linkedin_style = (linkedin_style or "professional").strip().lower()

    # Generate hashtags
    hashtags = ['#BuildingInPublic', '#CodingInPublic']
    for lang in sorted(list(summary.languages_used))[:3]:
        hashtags.append(f'#{lang.replace("/", "").replace(" ", "")}')
    if summary.tests_run:
        hashtags.append('#TDD')
    posts['hashtags'] = hashtags
    
    def _plural(n: int, singular: str, plural: Optional[str] = None) -> str:
        if n == 1:
            return singular
        return plural or f"{singular}s"

    def _time_str(minutes: int) -> str:
        if minutes <= 0:
            return ""
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m" if hours else f"{mins} minutes"

    # Platform-specific hashtag handling
    # X/Twitter: No hashtags (per Elon's guidance - they look spammy)
    # Other platforms: Include hashtags
    hashtag_str_x = ''  # No hashtags for X/Twitter
    hashtag_str_other = ' '.join(hashtags[:4])  # For BlueSky, LinkedIn, etc.

    # Short posts (Twitter/X - NO hashtags per Elon's guidance)
    if summary.git_commits:
        commit_msg = summary.git_commits[0][:80]
        if twitter_style == "devlog":
            posts['short'].append(f"devlog: shipped {commit_msg}")
        elif twitter_style == "minimal":
            posts['short'].append(f"Shipped: {commit_msg}")
        else:  # ship
            posts['short'].append(f"✅ Just shipped: {commit_msg}")

    if summary.files_created:
        count = len(summary.files_created)
        if twitter_style == "devlog":
            posts['short'].append(f"devlog: added {count} {_plural(count, 'new file')}")
        elif twitter_style == "minimal":
            posts['short'].append(f"Created {count} {_plural(count, 'new file')}")
        else:
            posts['short'].append(
                f"🛠️ Coding session complete!\n\nCreated {count} new file{'s' if count > 1 else ''} today."
            )

    if summary.errors_fixed > 0:
        n = summary.errors_fixed
        if twitter_style == "devlog":
            posts['short'].append(f"devlog: fixed {n} {_plural(n, 'bug')}")
        elif twitter_style == "minimal":
            posts['short'].append(f"Fixed {n} {_plural(n, 'bug')}")
        else:
            posts['short'].append(
                f"🐛➡️✅ Squashed {n} bug{'s' if n > 1 else ''} today!\n\nThe best feeling in coding."
            )

    if summary.duration_minutes > 0:
        t = _time_str(summary.duration_minutes)
        if twitter_style == "devlog":
            posts['short'].append(f"devlog: {t} in the trenches ({summary.total_tool_calls} ops)")
        elif twitter_style == "minimal":
            posts['short'].append(f"{t} of focused coding ({summary.total_tool_calls} ops)")
        else:
            posts['short'].append(
                f"⏱️ {t} of focused coding\n\n{summary.total_tool_calls} operations later... progress!"
            )
    
    # Thread posts (X/Twitter - compelling hooks, NO hashtags)
    thread = []

    # Only generate threads if there's actual content to share
    has_content = (
        summary.git_commits or
        summary.files_created or
        summary.errors_fixed > 0 or
        summary.tests_run or
        len(summary.languages_used) > 0
    )

    if has_content:
        # Tweet 1: Compelling hook that makes people want to read more
        hook_options = []

        if summary.git_commits:
            commit_preview = summary.git_commits[0][:100]
            if twitter_style == "devlog":
                hook_options.append(f"devlog: Just shipped {commit_preview}\n\nHere's what went into this 🧵")
            else:
                hook_options.append(f"Just shipped: {commit_preview}\n\nThread on how it came together 👇")

        if summary.files_created and len(summary.files_created) >= 3:
            count = len(summary.files_created)
            langs = ', '.join(sorted(list(summary.languages_used))[:2]) if summary.languages_used else 'code'
            if twitter_style == "devlog":
                hook_options.append(f"devlog: Created {count} new files today\n\n{langs} - building in public 🧵")
            else:
                hook_options.append(f"Built {count} new files today in {langs}\n\nBreakdown 👇")

        if summary.errors_fixed >= 2:
            n = summary.errors_fixed
            if twitter_style == "devlog":
                hook_options.append(f"devlog: Squashed {n} bugs in today's session\n\nThe debugging journey 🧵")
            else:
                hook_options.append(f"Fixed {n} bugs today\n\nWhat I learned 👇")

        # If we have a project with tech stack, use that
        if summary.languages_used and summary.duration_minutes > 15:
            langs = ', '.join(sorted(list(summary.languages_used))[:3])
            time_str = _time_str(summary.duration_minutes)
            if twitter_style == "devlog":
                hook_options.append(f"devlog: {time_str} deep in {langs}\n\nSession recap 🧵")
            else:
                hook_options.append(f"{time_str} building with {langs}\n\nWhat I shipped 👇")

        # Use the first available hook, or create a minimal one
        if hook_options:
            thread.append(hook_options[0])
        else:
            # Fallback for light sessions
            project = summary.project_name or "my project"
            if twitter_style == "devlog":
                thread.append(f"devlog: Working on {project}\n\nProgress update 🧵")
            else:
                thread.append(f"Quick session on {project}\n\nWhat changed 👇")

        # Tweet 2: Tech stack (if available)
        if summary.languages_used:
            langs = ', '.join(sorted(list(summary.languages_used))[:4])
            thread.append(f"💻 Tech stack: {langs}")

        # Tweet 3: Files created (if any)
        if summary.files_created:
            file_list = '\n'.join(f"  • {Path(f).name}" for f in summary.files_created[:5])
            thread.append(f"📝 New files:\n{file_list}")

        # Tweet 4: Commits (if any)
        if summary.git_commits:
            commits = '\n'.join(f"  ✅ {c[:60]}" for c in summary.git_commits[:3])
            thread.append(f"📦 Commits:\n{commits}")

        # Tweet 5: Tests (if run)
        if summary.tests_run:
            thread.append("🧪 Tests: All passing ✅\n\nNothing beats that green checkmark feeling.")

        # Tweet 6: Errors fixed (if any)
        if summary.errors_fixed > 0:
            n = summary.errors_fixed
            thread.append(f"🐛 Fixed {n} {_plural(n, 'bug')}\n\nDebugging is just detective work with code.")

        # Final tweet: Engagement
        thread.append("What are you building today?")

    posts['thread'] = thread
    
    # Medium posts (LinkedIn)
    project = summary.project_name or 'my project'
    langs = ', '.join(sorted(list(summary.languages_used))[:3])
    time_str = _time_str(summary.duration_minutes)
    first_commit = summary.git_commits[0][:100] if summary.git_commits else ""

    bullet_lines = []
    if first_commit:
        bullet_lines.append(f"• Shipped: {first_commit}")
    if summary.files_created:
        n = len(summary.files_created)
        bullet_lines.append(f"• Created {n} {_plural(n, 'new file')}")
    if summary.files_modified:
        n = len(summary.files_modified)
        bullet_lines.append(f"• Updated {n} {_plural(n, 'existing file')}")
    if summary.errors_fixed:
        n = summary.errors_fixed
        bullet_lines.append(f"• Fixed {n} {_plural(n, 'bug')}")
    if summary.tests_run:
        bullet_lines.append("• Ran tests ✅")

    bullets_block = "\n".join(bullet_lines) if bullet_lines else "• Made meaningful progress"
    linkedin_hashtags = " ".join(hashtags[:6])

    def _dedupe(strings: List[str]) -> List[str]:
        seen = set()
        out = []
        for s in strings:
            if s and s not in seen:
                seen.add(s)
                out.append(s)
        return out

    if linkedin_style == "story":
        headline_options = [
            "A small win (and a lesson)",
            "A quick story from today’s build",
            "One of those satisfying sessions",
        ]
        intro_options = []
        if summary.errors_fixed:
            intro_options.append(f"Started with a few errors in {project} and ended with a cleaner build.")
        if summary.tests_run:
            intro_options.append(f"Leaned on tests to keep {project} moving in the right direction.")
        if time_str:
            intro_options.append(f"{time_str} on {project} — the kind of steady progress that adds up.")
        if langs:
            intro_options.append(f"Worked through a set of improvements in {project} ({langs}).")
        intro_options.append(f"Another step forward on {project}.")
        intros = _dedupe(intro_options)

        for i, intro in enumerate(intros[:3], 1):
            headline = headline_options[(i - 1) % len(headline_options)]
            medium_post = f"""{headline}

{intro}

What changed:
{bullets_block}

Curious what you’re building right now — what’s on your plate this week?

{linkedin_hashtags}"""
            posts['medium'].append(medium_post)
    elif linkedin_style == "wins":
        headline_options = [
            "Progress, in numbers",
            "Session snapshot",
            "Quick status update",
        ]
        metrics = []
        if time_str:
            metrics.append(time_str)
        if summary.files_created:
            n = len(summary.files_created)
            metrics.append(f"{n} {_plural(n, 'new file')}")
        if summary.errors_fixed:
            n = summary.errors_fixed
            metrics.append(f"{n} {_plural(n, 'bug')} fixed")
        if summary.tests_run:
            metrics.append("tests run ✅")
        metrics_line = " • ".join(metrics) if metrics else ""

        intro_options = []
        if metrics_line:
            intro_options.append(f"{project} — {metrics_line}.")
        if first_commit:
            intro_options.append(f"Latest shipped change in {project}: {first_commit}.")
        if langs:
            intro_options.append(f"{project} + {langs} + consistent iteration.")
        intro_options.append(f"Keeping momentum on {project}.")
        intros = _dedupe(intro_options)

        for i, intro in enumerate(intros[:3], 1):
            headline = headline_options[(i - 1) % len(headline_options)]
            medium_post = f"""{headline}

{intro}

Highlights:
{bullets_block}

{linkedin_hashtags}"""
            posts['medium'].append(medium_post)
    else:  # professional (default)
        headline_options = [
            "Build update",
            "Progress update",
            "Product update",
            "Engineering update",
        ]
        intro_options = []
        if first_commit:
            intro_options.append(f"Quick update on {project}: shipped “{first_commit}”.")
            intro_options.append(f"{project} update — shipped “{first_commit}”.")
        if langs:
            intro_options.append(f"Made progress on {project} using {langs}.")
        if time_str:
            intro_options.append(f"{time_str} of focused work on {project}.")
        intro_options.append(f"Incremental improvements to {project} — moving it forward.")
        intros = _dedupe(intro_options)

        for i, intro in enumerate(intros[:3], 1):
            headline = headline_options[(i - 1) % len(headline_options)]
            medium_post = f"""{headline}

{intro}

Key outcomes:
{bullets_block}

What are you building this week?

{linkedin_hashtags}"""
            posts['medium'].append(medium_post)
    
    # Long form (Instagram caption / blog)
    long_post = f"""Today's build session 🛠️

{summary.duration_minutes} minutes of focused coding on {summary.project_name or 'my project'}.

The journey:
"""
    
    for highlight in summary.highlights[:5]:
        emoji = {'feature': '✨', 'fix': '🐛', 'test': '🧪', 'milestone': '🎯', 'refactor': '♻️', 'docs': '📚'}.get(highlight.category, '•')
        long_post += f"{emoji} {highlight.description}\n"
    
    if summary.languages_used:
        long_post += f"\nTech: {', '.join(sorted(summary.languages_used))}\n"
    
    long_post += f"""
Building in public means sharing the journey - the wins, the bugs, and everything in between.

What's your current project? Drop a comment! 👇

{' '.join(hashtags)}
"""
    posts['long'].append(long_post)
    
    return posts


def format_output(posts: dict, summary: SessionSummary) -> str:
    """Format posts into a readable markdown document"""
    output = f"""# Build in Public - Session Posts

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Session: {summary.session_id}
Project: {summary.project_name}
Duration: {summary.duration_minutes} minutes
Languages: {', '.join(sorted(summary.languages_used)) or 'N/A'}

---

## 📱 Short Posts (Twitter/X - No hashtags)

*Note: Hashtags removed per Elon's guidance - they look spammy on X*

"""

    for i, post in enumerate(posts['short'], 1):
        char_count = len(post)
        output += f"### Option {i} ({char_count} chars)\n\n```\n{post}\n```\n\n"

    output += """---

## 🧵 Thread (Twitter/X - No hashtags, compelling hooks)

*Note: First tweet designed as a hook to drive engagement*

"""

    if posts['thread']:
        for i, tweet in enumerate(posts['thread'], 1):
            char_count = len(tweet)
            output += f"**{i}/{len(posts['thread'])}** ({char_count} chars)\n\n```\n{tweet}\n```\n\n"
    else:
        output += "*No thread generated - insufficient content for engaging thread*\n\n"
    
    output += """---

## 💼 Medium Posts (LinkedIn, Mastodon - With hashtags)

*Note: Hashtags work well on LinkedIn and Mastodon for discoverability*

"""
    
    for i, post in enumerate(posts['medium'], 1):
        output += f"### Option {i}\n\n```\n{post}\n```\n\n"
    
    output += """---

## 📸 Long Form (Instagram, Blog - With hashtags)

*Note: Instagram posts can use up to 30 hashtags for maximum reach*

"""
    
    for i, post in enumerate(posts['long'], 1):
        output += f"### Option {i}\n\n```\n{post}\n```\n\n"
    
    output += f"""---

## #️⃣ Hashtags

Copy these: `{' '.join(posts['hashtags'])}`

---

## 📊 Session Stats

| Metric | Value |
|--------|-------|
| Files Created | {len(summary.files_created)} |
| Files Modified | {len(summary.files_modified)} |
| Git Commits | {len(summary.git_commits)} |
| Bugs Fixed | {summary.errors_fixed} |
| Tests Run | {'Yes' if summary.tests_run else 'No'} |
| Total Operations | {summary.total_tool_calls} |

"""
    
    if summary.files_created:
        output += "\n### Files Created\n\n"
        for f in summary.files_created[:10]:
            output += f"- `{safe_display_path(f)}`\n"
    
    if summary.git_commits:
        output += "\n### Commits\n\n"
        for c in summary.git_commits:
            output += f"- {c}\n"
    
    return output


def main():
    parser = argparse.ArgumentParser(
        description='Generate social media posts from Claude Code sessions'
    )
    parser.add_argument('--session', '-s', help='Session ID or path to JSONL file')
    parser.add_argument('session_spec', nargs='?', help='Session ID or path to JSONL file (positional)')
    parser.add_argument('--output', '-o', default='.', help='Output directory')
    parser.add_argument('--json', action='store_true', help='Also output raw JSON')
    parser.add_argument('--project-name', help='Override project name (privacy-safe)')
    parser.add_argument(
        '--twitter-style',
        default='devlog',
        choices=['devlog', 'ship', 'minimal'],
        help='Style preset for Twitter/X + BlueSky short/thread posts',
    )
    parser.add_argument(
        '--linkedin-style',
        default='professional',
        choices=['professional', 'story', 'wins'],
        help='Style preset for LinkedIn medium posts',
    )
    
    args = parser.parse_args()
    
    # Find session file
    session_spec = args.session or args.session_spec
    if session_spec:
        if os.path.exists(session_spec):
            session_path = Path(session_spec)
            project_dir_name = session_path.parent.name
        else:
            # Try to find by session ID
            projects_dir = find_claude_projects_dir()
            session_path = None
            for project in projects_dir.iterdir():
                candidate = project / f"{session_spec}.jsonl"
                if candidate.exists():
                    session_path = candidate
                    project_dir_name = project.name
                    break
            if not session_path:
                print(f"Error: Session '{session_spec}' not found", file=sys.stderr)
                sys.exit(1)
    else:
        session_path, project_dir_name = get_latest_session()
    
    session_id = session_path.stem
    project_name = safe_project_name(project_dir_name, fallback=(args.project_name or Path.cwd().name))
    
    print(f"📖 Parsing session: {session_id}", file=sys.stderr)
    print(f"📁 Project: {project_name}", file=sys.stderr)
    
    # Parse and analyze
    messages = parse_session_jsonl(session_path)
    summary = extract_highlights(messages)
    summary.session_id = session_id
    summary.project_name = project_name
    
    # Generate posts
    posts = generate_posts(
        summary,
        twitter_style=args.twitter_style,
        linkedin_style=args.linkedin_style,
    )
    
    # Format output
    output = format_output(posts, summary)
    
    # Write output
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f"build-in-public_{timestamp}.md"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output)
    
    print(f"\n✅ Posts generated: {output_file}", file=sys.stderr)
    
    if args.json:
        json_file = output_dir / f"build-in-public_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'session_id': summary.session_id,
                    'project_name': summary.project_name,
                    'duration_minutes': summary.duration_minutes,
                    'styles': {
                        'twitter': args.twitter_style,
                        'linkedin': args.linkedin_style,
                    },
                    # Keep filenames privacy-safe (no absolute paths).
                    'files_created': [safe_display_path(p) for p in summary.files_created],
                    'files_modified': [safe_display_path(p) for p in summary.files_modified],
                    'git_commits': summary.git_commits,
                    'errors_fixed': summary.errors_fixed,
                    'tests_run': summary.tests_run,
                    'languages_used': sorted(list(summary.languages_used)),
                    'total_tool_calls': summary.total_tool_calls
                },
                'posts': posts
            }, f, indent=2)
        print(f"📄 JSON output: {json_file}", file=sys.stderr)
    
    # Also print the markdown to stdout for piping
    print(output)


if __name__ == '__main__':
    main()
