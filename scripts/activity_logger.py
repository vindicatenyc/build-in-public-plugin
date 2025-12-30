#!/usr/bin/env python3
"""
Activity Logger for Build in Public plugin.

This hook fires after Claude Code responds (Stop event) and logs
activity metrics for the session to help decide if posts should be generated.
"""

import json
import sys
import os
from pathlib import Path


def main():
    # Read hook input from stdin
    try:
        hook_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_data = {}
    
    # Get plugin root for storing activity log
    plugin_root = os.environ.get('CLAUDE_PLUGIN_ROOT', '')
    if not plugin_root:
        sys.exit(0)
    
    activity_file = Path(plugin_root) / '.session_activity.json'
    
    # Load existing activity or create new
    if activity_file.exists():
        try:
            with open(activity_file, 'r') as f:
                activity = json.load(f)
        except:
            activity = {}
    else:
        activity = {
            'files_modified': 0,
            'files_created': 0,
            'git_commits': 0,
            'commands_run': 0,
            'responses': 0
        }
    
    # Increment response counter
    activity['responses'] = activity.get('responses', 0) + 1
    
    # Check the session transcript for recent activity if available
    transcript_path = hook_data.get('transcript_path', '')
    if transcript_path and os.path.exists(transcript_path):
        try:
            # Read last few lines of transcript for recent activity
            with open(transcript_path, 'r') as f:
                lines = f.readlines()
            
            # Check recent messages for file operations
            for line in lines[-20:]:  # Check last 20 messages
                try:
                    msg = json.loads(line)
                    tool_name = msg.get('name', msg.get('tool_name', ''))
                    
                    if tool_name in ('Write', 'create_file'):
                        activity['files_created'] = activity.get('files_created', 0) + 1
                    elif tool_name in ('Edit', 'MultiEdit', 'str_replace'):
                        activity['files_modified'] = activity.get('files_modified', 0) + 1
                    elif tool_name == 'Bash':
                        activity['commands_run'] = activity.get('commands_run', 0) + 1
                        command = msg.get('tool_input', {}).get('command', '')
                        if 'git commit' in command:
                            activity['git_commits'] = activity.get('git_commits', 0) + 1
                except:
                    continue
        except:
            pass
    
    # Save activity log
    try:
        with open(activity_file, 'w') as f:
            json.dump(activity, f)
    except:
        pass
    
    sys.exit(0)


if __name__ == '__main__':
    main()
