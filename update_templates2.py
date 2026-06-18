import os
import glob

templates_dir = "templates"

SYNE_FONT = """<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">"""
LIBS = """
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/ScrollTrigger.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vanilla-tilt/1.8.0/vanilla-tilt.min.js"></script>
"""

for filepath in glob.glob(os.path.join(templates_dir, "*.html")):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    original = content
    
    # Add new fonts
    if "family=Syne" not in content and "</head>" in content:
        content = content.replace("</head>", f"{SYNE_FONT}\n</head>")
        
    # Add new libraries
    if "ScrollTrigger.min.js" not in content and "</body>" in content:
        # replace old gsap injection if it exists
        if '<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>' in content:
             content = content.replace('<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>', LIBS)
        else:
             content = content.replace("</body>", f"{LIBS}\n</body>")

    if original != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {filepath}")
    else:
        print(f"No changes for {filepath}")

