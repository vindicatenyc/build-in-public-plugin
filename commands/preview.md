---
description: Preview what happened in the current session before generating posts
---

# Build in Public - Session Preview

Get a quick preview of the current coding session's highlights before generating social media posts.

## Instructions

1. Analyze the current session to identify:
   - Files created and modified
   - Git commits made
   - Tests run
   - Bugs fixed
   - Languages/technologies used
   - Key milestones achieved

2. Present a summary to the user in a conversational format

3. Ask if they want to:
   - Generate posts now (suggest running `/build-in-public:generate`)
   - Add any custom context or achievements to highlight
   - Focus on specific aspects (e.g., just the bug fixes, just the new feature)

## Summary Format

Present the session summary like this:

"Here's what we accomplished in this session:

📁 **Files**: Created X, modified Y
💻 **Tech**: [languages used]
📦 **Commits**: [list key commits]
🐛 **Bugs fixed**: X
🧪 **Tests**: [passed/failed/not run]
⏱️ **Duration**: ~X minutes

Highlights worth sharing:
1. [highlight 1]
2. [highlight 2]
3. [highlight 3]

Would you like me to generate posts now? You can also tell me what to emphasize - for example, 'focus on the bug fixes' or 'highlight the new API endpoint'."
