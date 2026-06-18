import os
import glob
import re

templates_dir = "templates"

FONTS_TAG = """<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">"""
GSAP_TAG = """<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>"""
ANIM_TAG = """<script src="/static/global-animations.js" defer></script>"""
AGENT_TAG = """
<script>
  if (!window.GEMINI_API_KEY) {
    window.GEMINI_API_KEY = "{{ gemini_api_key }}";
  }
</script>
<script src="/static/google-agent.js" defer></script>
"""

for filepath in glob.glob(os.path.join(templates_dir, "*.html")):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    original = content
    # 1. Replace apple-light with google
    content = content.replace("apple-light", "google")
    content = content.replace("Apple Light", "Google")
    
    # 2. Add Fonts
    if "family=Outfit" not in content and "</head>" in content:
        content = content.replace("</head>", f"{FONTS_TAG}\n</head>")
        
    # 3. Add GSAP
    if "gsap.min.js" not in content and "</body>" in content:
        content = content.replace("</body>", f"{GSAP_TAG}\n</body>")
        
    # 4. Add global animations
    if "global-animations.js" not in content and "</body>" in content:
        content = content.replace("</body>", f"{ANIM_TAG}\n</body>")
        
    # 5. Add agent
    if "google-agent.js" not in content and "</body>" in content:
        content = content.replace("</body>", f"{AGENT_TAG}\n</body>")

    if original != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {filepath}")
    else:
        print(f"No changes for {filepath}")

