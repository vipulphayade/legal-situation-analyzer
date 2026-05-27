from pathlib import Path
import shutil

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend-modern"
V9 = ROOT / "v9_reference_frontend"

print("\n=== FRONTEND REPAIR SCRIPT ===\n")

# ---------------------------------------------------
# 1. CLEAN REDUNDANT BUILD/CACHE FOLDERS
# ---------------------------------------------------

folders_to_remove = [
    "node_modules",
    "dist",
    "build",
    ".vite",
    ".next",
    ".cache",
]

for folder_name in folders_to_remove:
    target = V9 / folder_name

    if target.exists():
        print(f"Removing: {target}")
        shutil.rmtree(target, ignore_errors=True)

print("\nV9 reference cleanup complete.\n")

# ---------------------------------------------------
# 2. FIX INDEX.CSS
# ---------------------------------------------------

index_css = FRONTEND / "src" / "index.css"

if index_css.exists():
    index_css.write_text('@import "tailwindcss";\n')
    print("Fixed src/index.css")

# ---------------------------------------------------
# 3. RESET APP.CSS TEMPORARILY
# ---------------------------------------------------

app_css = FRONTEND / "src" / "App.css"

if app_css.exists():
    app_css.write_text("/* Temporary clean reset */\n")
    print("Reset src/App.css")

# ---------------------------------------------------
# 4. FIX POSTCSS CONFIG
# ---------------------------------------------------

postcss_config = FRONTEND / "postcss.config.js"

postcss_content = '''
export default {
  plugins: {
    "@tailwindcss/postcss": {},
  },
}
'''

postcss_config.write_text(postcss_content)
print("Fixed postcss.config.js")

# ---------------------------------------------------
# 5. CHECK PACKAGE.JSON
# ---------------------------------------------------

package_json = FRONTEND / "package.json"

if package_json.exists():
    print("\nReminder:")
    print("Ensure these packages exist:")
    print("- tailwindcss")
    print("- @tailwindcss/postcss")
    print("- @tailwindcss/vite")
    print("- framer-motion")
    print("- lucide-react")

# ---------------------------------------------------
# DONE
# ---------------------------------------------------

print("\nIf app renders, architecture is stable.")