#!/usr/bin/env python3
import os
import requests
import datetime
import textwrap

# read the env var (set by the workflow)
USERNAME = os.getenv("GITHUB_USERNAME")

# Config
GITHUB_API_BASE = "https://api.github.com"
TEMPLATE_PATH = "templates/resume_template.md"
OUTPUT_PATH = "Resume.md"
PROJECTS_EXCLUDE = {".github", "templates", "scripts", ".git", "__pycache__"}
PROJECT_SUMMARY_MAX_CHARS = 250  # limit for each summary

def safe_first_paragraph_from_text(text):
    # split into paragraphs by blank lines
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not parts:
        return ""
    # use first paragraph and collapse newlines
    first = " ".join(parts[0].splitlines()).strip()
    if len(first) > PROJECT_SUMMARY_MAX_CHARS:
        return first[:PROJECT_SUMMARY_MAX_CHARS].rsplit(" ", 1)[0] + "..."
    return first

def read_local_readme_summary(folder_path):
    # look for README.md (case-insensitive)
    for name in ("README.md", "Readme.md", "readme.md"):
        fp = os.path.join(folder_path, name)
        if os.path.isfile(fp):
            with open(fp, "r", encoding="utf-8") as f:
                text = f.read()
            return safe_first_paragraph_from_text(text)
    # fallback: no README -> try to give a hint
    try:
        items = os.listdir(folder_path)
        items = [i for i in items if not i.startswith(".")][:6]
        if items:
            return "Contains: " + ", ".join(items)
    except Exception:
        pass
    return "No README available."

def get_github_user_stats(username):
    # minimal unauthenticated calls (rate-limited but fine for weekly use)
    user_resp = requests.get(f"{GITHUB_API_BASE}/users/{username}")
    user_resp.raise_for_status()
    user = user_resp.json()

    # get public repos (first page). If many repos exist, for stats it's usually enough.
    repos_resp = requests.get(f"{GITHUB_API_BASE}/users/{username}/repos?per_page=100")
    repos_resp.raise_for_status()
    repos = repos_resp.json()

    total_stars = sum(repo.get("stargazers_count", 0) for repo in repos)
    language_counts = {}
    for repo in repos:
        lang = repo.get("language")
        if lang:
            language_counts[lang] = language_counts.get(lang, 0) + 1
    top_languages = ", ".join(sorted(language_counts, key=language_counts.get, reverse=True)[:5])

    # Optional: commits count across repos would require extra requests (omitted for speed)
    return {
        "name": user.get("name") or username,
        "public_repos": user.get("public_repos", 0),
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "stars": total_stars,
        "languages": top_languages if top_languages else "—",
        "updated_date": datetime.datetime.now().strftime("%d %b %Y")
    }

def discover_projects_and_summaries():
    root_items = sorted(os.listdir("."))
    projects = []
    for item in root_items:
        if item in PROJECTS_EXCLUDE:
            continue
        if item.startswith("."):
            continue
        if os.path.isdir(item):
            summary = read_local_readme_summary(item)
            projects.append({
                "name": item,
                "path": item,
                "summary": summary
            })
    return projects

def render_projects_md(projects):
    if not projects:
        return "No project folders found in this repository."
    lines = ["## 🧩 Projects\n"]
    for p in projects:
        # show relative link to folder and short summary
        lines.append(f"- **[{p['name']}](./{p['path']})** — {p['summary']}")
    return "\n".join(lines)

def write_resume(template_data: dict, projects_md: str):
    # read template
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    # replace simple placeholders
    for key, value in template_data.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))

    # insert projects block
    template = template.replace("{{projects}}", projects_md)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(template)

def main():
    if not USERNAME:
        raise Exception("GITHUB_USERNAME environment variable not set! Add secret RESUME_USER and map it in the workflow.")
    print(f"Fetching GitHub stats for: {USERNAME}")

    stats = get_github_user_stats(USERNAME)
    projects = discover_projects_and_summaries()
    projects_md = render_projects_md(projects)

    write_resume(stats, projects_md)
    print("Resume.md updated successfully!")

if __name__ == "__main__":
    main()
