---
description: Generate "building in public" social media posts from the current or specified session
---

# Build in Public - Generate Posts

Generate social media posts from your Claude Code session for sharing on Twitter/X, BlueSky, LinkedIn, Instagram, and other platforms.

## Instructions

1. Run the post generation script located at `${CLAUDE_PLUGIN_ROOT}/scripts/generate_posts.py`

2. If `$ARGUMENTS` contains a session ID or file path, pass it as the final positional argument (or via `--session "$ARGUMENTS"`)

3. Create output directory if it doesn't exist and output posts there to keep the project clean

4. Also generate JSON for automation: `--json`

## Command to Run

```bash
mkdir -p output && python3 "${CLAUDE_PLUGIN_ROOT}/scripts/generate_posts.py" --output output --json $ARGUMENTS
```

## After Running

1. Show the user a summary of what was generated
2. Highlight the best 1-2 short posts that are ready to copy/paste
3. Mention that the full markdown file contains thread options, LinkedIn posts, and Instagram captions
4. Let them know the JSON file can be used by automation tools to publish posts

## Example Output Summary

After generating, tell the user something like:

"I've generated your #BuildingInPublic posts! Here's the best tweet-ready option:

[paste the best short post here]

Full options saved to: output/build-in-public_[timestamp].md
JSON for automation: output/build-in-public_[timestamp].json

The file includes Twitter threads, LinkedIn posts, and Instagram captions. Which platform would you like to post to first?"
