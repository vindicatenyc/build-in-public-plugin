#!/usr/bin/env python3
"""
Build in Public - Social Media Post Generator

Parses Claude Code session transcripts and generates ready-to-post
social media content for Twitter/X, BlueSky, Instagram, LinkedIn, etc.

Usage:
    python generate_posts.py [--session SESSION_ID] [--output OUTPUT_DIR]
    
If no session is specified, uses the most recently modified session.
"""

import json
import sys
import os
import re
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional
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


def find_claude_projects_dir() -> Path:
    """Locate the Claude Code projects directory"""
    home = Path.home()
    claude_dir = home / ".claude" / "projects"
    if claude_dir.exists():
        return claude_dir
    raise FileNotFoundError(f"Claude projects directory not found at {claude_dir}")


def get_latest_session(project_dir: Optional[Path] = None) -> tuple[Path, str]:
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
    project_name = latest_file.parent.name.replace("-", "/").lstrip("/")
    return latest_file, project_name


def parse_session_jsonl(filepath: Path) -> list[dict]:
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


def extract_highlights(messages: list[dict]) -> SessionSummary:
    """Extract notable events and statistics from session messages"""
    highlights = []
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
                    ext = Path(file_path).suffix.lower()
                    if ext in lang_extensions:
                        languages_used.add(lang_extensions[ext])
                    
                    if tool_name in ('Write', 'create_file'):
                        files_created.add(file_path)
                    else:
                        files_modified.add(file_path)
            
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
            
            # Look for milestone language
            milestone_patterns = [
                r'(completed|finished|done with|implemented|added|created|fixed|resolved|refactored)',
                r'(feature|functionality|component|module|endpoint|api|ui|test|bug fix)'
            ]
            
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


def generate_posts(summary: SessionSummary) -> dict:
    """Generate social media posts from session summary"""
    posts = {
        'short': [],      # Twitter/X, BlueSky (280 chars)
        'medium': [],     # LinkedIn, Mastodon (500-700 chars)
        'thread': [],     # Twitter/X thread (multiple tweets)
        'long': [],       # Blog snippet, Instagram caption
        'hashtags': []
    }
    
    # Generate hashtags
    hashtags = ['#BuildingInPublic', '#CodingInPublic']
    for lang in list(summary.languages_used)[:3]:
        hashtags.append(f'#{lang.replace("/", "").replace(" ", "")}')
    if summary.tests_run:
        hashtags.append('#TDD')
    posts['hashtags'] = hashtags
    
    hashtag_str = ' '.join(hashtags[:4])
    
    # Short posts (Twitter/X, BlueSky)
    if summary.git_commits:
        commit_msg = summary.git_commits[0][:80]
        posts['short'].append(
            f"✅ Just shipped: {commit_msg}\n\n{hashtag_str}"
        )
    
    if summary.files_created:
        count = len(summary.files_created)
        posts['short'].append(
            f"🛠️ Coding session complete!\n\nCreated {count} new file{'s' if count > 1 else ''} today.\n\n{hashtag_str}"
        )
    
    if summary.errors_fixed > 0:
        posts['short'].append(
            f"🐛➡️✅ Squashed {summary.errors_fixed} bug{'s' if summary.errors_fixed > 1 else ''} today!\n\nThe best feeling in coding.\n\n{hashtag_str}"
        )
    
    if summary.duration_minutes > 0:
        hours = summary.duration_minutes // 60
        mins = summary.duration_minutes % 60
        time_str = f"{hours}h {mins}m" if hours else f"{mins} minutes"
        posts['short'].append(
            f"⏱️ {time_str} of focused coding\n\n{summary.total_tool_calls} operations later... progress!\n\n{hashtag_str}"
        )
    
    # Thread posts
    thread = []
    thread.append(f"🧵 Today's coding session recap:\n\n{hashtag_str}")
    
    if summary.languages_used:
        langs = ', '.join(list(summary.languages_used)[:4])
        thread.append(f"💻 Tech stack: {langs}")
    
    if summary.files_created:
        file_list = '\n'.join(f"  • {Path(f).name}" for f in summary.files_created[:4])
        thread.append(f"📝 New files:\n{file_list}")
    
    if summary.git_commits:
        commits = '\n'.join(f"  ✅ {c[:60]}" for c in summary.git_commits[:3])
        thread.append(f"📦 Commits:\n{commits}")
    
    if summary.tests_run:
        thread.append("🧪 Tests: Passing ✅")
    
    thread.append("What are you building today? 👇")
    posts['thread'] = thread
    
    # Medium posts (LinkedIn)
    medium_post = f"""Coding session complete! 🚀

Today I worked on {summary.project_name or 'my project'} using {', '.join(list(summary.languages_used)[:3]) or 'code'}.

Key accomplishments:
"""
    
    if summary.git_commits:
        medium_post += f"• Shipped: {summary.git_commits[0][:100]}\n"
    if summary.files_created:
        medium_post += f"• Created {len(summary.files_created)} new files\n"
    if summary.files_modified:
        medium_post += f"• Modified {len(summary.files_modified)} existing files\n"
    if summary.errors_fixed:
        medium_post += f"• Fixed {summary.errors_fixed} bugs\n"
    if summary.tests_run:
        medium_post += "• All tests passing ✅\n"
    
    medium_post += f"\n{' '.join(hashtags)}"
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
        long_post += f"\nTech: {', '.join(summary.languages_used)}\n"
    
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
Languages: {', '.join(summary.languages_used) or 'N/A'}

---

## 📱 Short Posts (Twitter/X, BlueSky - 280 chars)

"""
    
    for i, post in enumerate(posts['short'], 1):
        char_count = len(post)
        output += f"### Option {i} ({char_count} chars)\n\n```\n{post}\n```\n\n"
    
    output += """---

## 🧵 Thread (Twitter/X)

"""
    
    for i, tweet in enumerate(posts['thread'], 1):
        char_count = len(tweet)
        output += f"**{i}/{len(posts['thread'])}** ({char_count} chars)\n\n```\n{tweet}\n```\n\n"
    
    output += """---

## 💼 Medium Posts (LinkedIn, Mastodon)

"""
    
    for i, post in enumerate(posts['medium'], 1):
        output += f"### Option {i}\n\n```\n{post}\n```\n\n"
    
    output += """---

## 📸 Long Form (Instagram, Blog)

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
            output += f"- `{f}`\n"
    
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
    parser.add_argument('--output', '-o', default='.', help='Output directory')
    parser.add_argument('--json', action='store_true', help='Also output raw JSON')
    
    args = parser.parse_args()
    
    # Find session file
    if args.session:
        if os.path.exists(args.session):
            session_path = Path(args.session)
            project_name = session_path.parent.name
        else:
            # Try to find by session ID
            projects_dir = find_claude_projects_dir()
            session_path = None
            for project in projects_dir.iterdir():
                candidate = project / f"{args.session}.jsonl"
                if candidate.exists():
                    session_path = candidate
                    project_name = project.name
                    break
            if not session_path:
                print(f"Error: Session '{args.session}' not found", file=sys.stderr)
                sys.exit(1)
    else:
        session_path, project_name = get_latest_session()
    
    session_id = session_path.stem
    
    print(f"📖 Parsing session: {session_id}", file=sys.stderr)
    print(f"📁 Project: {project_name}", file=sys.stderr)
    
    # Parse and analyze
    messages = parse_session_jsonl(session_path)
    summary = extract_highlights(messages)
    summary.session_id = session_id
    summary.project_name = project_name.replace("-", "/").lstrip("/")
    
    # Generate posts
    posts = generate_posts(summary)
    
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
                    'files_created': summary.files_created,
                    'files_modified': summary.files_modified,
                    'git_commits': summary.git_commits,
                    'errors_fixed': summary.errors_fixed,
                    'tests_run': summary.tests_run,
                    'languages_used': list(summary.languages_used),
                    'total_tool_calls': summary.total_tool_calls
                },
                'posts': posts
            }, f, indent=2)
        print(f"📄 JSON output: {json_file}", file=sys.stderr)
    
    # Also print the markdown to stdout for piping
    print(output)


if __name__ == '__main__':
    main()
