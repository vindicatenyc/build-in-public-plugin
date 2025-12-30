#!/usr/bin/env python3
"""
Session End Hook for Build in Public plugin.

This hook fires when a Claude Code session ends and reminds the user
to generate their #BuildingInPublic posts.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime


def main():
    # Read hook input from stdin
    try:
        hook_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_data = {}
    
    # Check if this was a substantial session
    session_id = hook_data.get('session_id', '')
    
    # Get the activity log to see if there was meaningful work
    plugin_root = os.environ.get('CLAUDE_PLUGIN_ROOT', '')
    activity_log = Path(plugin_root) / '.session_activity.json' if plugin_root else None
    
    has_activity = False
    if activity_log and activity_log.exists():
        try:
            with open(activity_log, 'r') as f:
                activity = json.load(f)
                # Consider it substantial if there were file edits or commits
                has_activity = (
                    activity.get('files_modified', 0) > 0 or
                    activity.get('files_created', 0) > 0 or
                    activity.get('git_commits', 0) > 0
                )
        except:
            pass
    
    if has_activity:
        # Print reminder message (will be shown to user)
        print("\n" + "=" * 50)
        print("📱 BUILD IN PUBLIC REMINDER")
        print("=" * 50)
        print("\nYou had a productive session! Consider sharing your progress.")
        print("\nRun /build-in-public:generate to create social media posts")
        print("for Twitter/X, BlueSky, LinkedIn, and more.")
        print("\n" + "=" * 50)
    
    # Clean up activity log for next session
    if activity_log and activity_log.exists():
        activity_log.unlink()
    
    # Always exit successfully
    sys.exit(0)


if __name__ == '__main__':
    main()
