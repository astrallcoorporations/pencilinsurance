import json
import re

log_path = r'C:\Users\thats\.gemini\antigravity\brain\799db294-cccc-4227-846e-859df0f9ca25\.system_generated\logs\transcript.jsonl'
lines = open(log_path, encoding='utf-8').readlines()

content = ""
for l in reversed(lines):
    if 'static/google-agent.js' in l and 'write_to_file' in l and 'CodeContent' in l and 'implementation_plan' not in l and '"step_index":' in l:
        step = json.loads(l)
        if int(step['step_index']) < 181:
            content = step['tool_calls'][0]['args']['CodeContent']
            break

if content:
    with open('static/google-agent.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully restored static/google-agent.js")
else:
    print("Failed to find google-agent.js content")
