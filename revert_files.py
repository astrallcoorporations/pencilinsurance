import json
import os
import glob

log_path = r'C:\Users\thats\.gemini\antigravity\brain\799db294-cccc-4227-846e-859df0f9ca25\.system_generated\logs\transcript.jsonl'
lines = open(log_path, encoding='utf-8').readlines()

# Recover JS files
step151 = next((json.loads(l) for l in lines if '"step_index":151' in l), None)
step158 = next((json.loads(l) for l in lines if '"step_index":158' in l), None)

if step151:
    with open('static/global-animations.js', 'w', encoding='utf-8') as f:
        f.write(step151['tool_calls'][0]['args']['CodeContent'])
    print('Restored static/global-animations.js')

if step158:
    with open('static/google-agent.js', 'w', encoding='utf-8') as f:
        f.write(step158['tool_calls'][0]['args']['CodeContent'])
    print('Restored static/google-agent.js')

# Revert HTML templates
templates_dir = "templates"
SYNE_FONT = '<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">'
OUTFIT_FONT = '<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">'

for filepath in glob.glob(os.path.join(templates_dir, "*.html")):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    original = content
    
    # Revert fonts
    if SYNE_FONT in content:
        content = content.replace(SYNE_FONT, OUTFIT_FONT)
    elif "family=Syne" in content:
        # Fallback regex-like replacement if exact string didn't match
        import re
        content = re.sub(r'<link[^>]*family=Syne[^>]*>', OUTFIT_FONT, content)
        
    # Revert scripts: Remove vanilla-tilt and ScrollTrigger
    content = content.replace('<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/ScrollTrigger.min.js"></script>\n', '')
    content = content.replace('<script src="https://cdnjs.cloudflare.com/ajax/libs/vanilla-tilt/1.8.0/vanilla-tilt.min.js"></script>\n', '')
    
    if original != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Reverted templates in {filepath}")

print("Done restoring files.")
