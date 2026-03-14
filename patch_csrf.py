import os
import glob

templates_dir = r"f:\CODE\六合彩\templates"
html_files = glob.glob(os.path.join(templates_dir, "*.html"))

csrf_snippet = """
    <!-- CSRF Token Global Setup -->
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <script>
        const originalFetch = window.fetch;
        window.fetch = async function(resource, config) {
            config = config || {};
            const method = (config.method || 'GET').toUpperCase();
            if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
                config.headers = {
                    ...config.headers,
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
                };
            }
            return originalFetch(resource, config);
        };
    </script>
</head>"""

for html_file in html_files:
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "csrf-token" in content:
        print(f"Skipping {html_file}, CSRF already present.")
        continue
    
    if "</head>" in content:
        content = content.replace("</head>", csrf_snippet)
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Patched {html_file}")
    else:
        print(f"Could not find </head> in {html_file}")
