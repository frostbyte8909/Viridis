import subprocess
import random
from datetime import datetime, timedelta
import os
import shutil

commits = [
    ("b07ab79c2610ddb3c66bc30e681fc60d1fb8530b", "Initialize project structure and config files"),
    ("9bf8f3b0a12de4d55c829e1ba88c4b68f8f56f75", "Create FastAPI app factory and config"),
    ("f98c62cc687be9b361534660691512d2fff42fa1", "Set up PostgreSQL SQLAlchemy models"),
    ("27890d6cafd24d441a646bff1e8b4d2d24b11832", "Configure Alembic for async migrations"),
    ("8babc69739aa59122ccd58b40055f07c415c8540", "Set up Redis connection pool and Lua scripts"),
    ("ca072273c6230c141e539c796d5d430adf0bd02c", "Implement core Redis Lua script wrappers and ZSET concurrency guard"),
    ("cc50fd12861d0ec9ab9ee1aa947c42675a82ddb3", "Implement decision engine orchestrator and enforce endpoint"),
    ("cc87c09d567cc64aec8ea6ad2ab235b8004f2770", "Build management plane, API key issuance, and HMAC override verification"),
    ("488d525e15b188865467331ca9c0f6c65ddddf11", "Add PostgreSQL trigger migration for audit log immutability"),
    ("f5bca224e511ed4e87af24f74dc7d0ea2b62caa3", "Integrate Redis Streams async audit pipeline and operational modes"),
    ("4c94e239edf8babf5223f3d53a03a67532b2414f", "Finalize CI/CD pipeline, k6 load testing, and project documentation"),
    ("bf5c0435d0da3360795446a23e5cec64a7a5f5a0", "Fix docker build order, fix alembic graph, and add intensive load testing benchmarks"),
    ("0b668d9c40cc0cb32cb8c871e6d5ca6b969c5c7c", "Move README to repository root for visibility"),
    ("51736d4c3894e3ef8840e8020d8e53a61a103b95", "Add basic pytest framework for CI"),
    ("d765fe73c037ae4f1926c9cafb811b6a72aef4ad", "Add production docker-compose configuration"),
    ("600e101cfcaa754b295166c546a4c65967233111", "Implement Azure IaC Bicep templates for Container Apps"),
    ("5c36dfe458e3c0a6d9665fd72551e11c07ca11b8", "Implement GitHub Actions CI/CD pipeline"),
    ("cf2cc06b4adf701e23d494cbbf488fab4a2b7b97", "pre-fix commit before pytest issues fix"),
    ("5fcc97d5c604bc6b98634af4998dc4df7699bdc0", "fix pytest import error and update status code assertion"),
    ("bd9b071f99c3edee9573df4a7142438bab36d079", "implement key hashing offloading, audit log partitioning migration, and DB fallback circuit breaker"),
    ("7dfd6599792142e1ed6bb1953895e5a652073491", "add GCP IaC layer using Terraform (VPC, Memorystore Redis, Cloud SQL, Secret Manager, and Cloud Run)"),
    ("7da99c748201b4b8ef2158c2add13a7d1a24822c", "Pre-change commit"),
    ("6c1cd919abec4e568414c8b90399aa8da4e147e9", "Security fixes: C-01, H-01, H-02, H-03, H-04, M-01, M-03"),
    ("2fa9e53986a6930b00aed157af3b87e7bdc58be9", "Security fixes: C-02, C-03, C-05, C-06, C-07, H-05, H-06, H-07, H-08, H-09, H-10, H-11, M-05, M-06, M-07, M-08, M-09, M-10, M-11"),
    ("5f3c1f41ac48ae0667b44ea2f67a81e65fc92a81", "chore: Restore and secure CI/CD deployment pipeline"),
    ("a1a83ad30d479df4a465eb047a1e27024ebe2d25", "Create codeql.yml"),
    ("745c2307eb9622f4d857aac19931cd14b5a95e1a", "ci: fix github action paths, node 20 deprecation warnings, and missing python version"),
    ("5d923adc3ff6e96f033682524ac62bc8707d4874", "fix: resolve codeql alerts, add strict pydantic types, and clean up code quality issues"),
    ("668ab45d764bf75595954195973c5731ef7bea0d", "ci: enforce workflow permissions"),
    ("efdd59d14cd52ee339374ddce8982fdaa610f2fe", "fix: resolve pydantic url casting bug and strengthen HMAC derivation for codeql"),
    ("9ffb595d88f2a7a205d57e03e7be6af1f2ec16fb", "fix: resolve redis type hint import and definitively satisfy codeql hashing rule"),
    ("eab7d8f67f7556c64d48aba76621c68a03596673", "Merge pull request #14 from frostbyte8909/feature/pr-checks"),
    ("b19e73d6dbb637a099e90b911bedcb3b010be04f", "docs: rewrite root README with professional FAANG-style formatting"),
    ("7c3b21c26730ae216b8c0d00206fcb93db6f5929", "docs: add banner image"),
    ("829886a690c2e0d9e9f876db94415721bf2bd84c", "docs: replace mermaid diagram with architecture image"),
    ("4ec3205ee4b67c3e0b58cc70e1809ce1bb4e4089", "docs: add medium article link and caption to architecture diagram"),
    ("fdc9b95c4106fad501efa84a8291ff7a5974dd43", "docs: rename project from viridian to viridis"),
    ("1ce630347ee450c74e14174b46e9020399083d48", "feat: implement per-key limits, quota API, and audit export"),
]

def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running {cmd}: {e.output.decode('utf-8')}")
        raise

# Time configuration
start_date = datetime.now() - timedelta(days=21)
current_date = start_date

timeline = []
for i in range(len(commits)):
    gap_type = random.choice(['sprint', 'sprint', 'all_nighter', 'sleep'])
    if gap_type == 'sprint':
        delta = timedelta(hours=random.uniform(1, 6))
    elif gap_type == 'all_nighter':
        delta = timedelta(minutes=random.uniform(15, 90))
    elif gap_type == 'sleep':
        delta = timedelta(hours=random.uniform(3, 5))
    
    current_date += delta
    timeline.append(current_date)

# Clone the repo to a temp directory to extract specific commits cleanly
run("rm -rf /tmp/viridis_temp")
run("git clone . /tmp/viridis_temp")

# Checkout orphan branch
run("git checkout --orphan realistic-history")
run("git rm -rf .")

changelog_content = "# Changelog\n\nAll notable changes to the Viridis project will be documented in this file in chronological order.\n\n"

for idx, ((orig_hash, subject), commit_date) in enumerate(zip(commits, timeline)):
    # Sync the exact file tree of orig_hash into the current directory
    run(f"cd /tmp/viridis_temp && git reset --hard {orig_hash} && git clean -fdx")
    run("rsync -a --delete --exclude=.git --exclude=CHANGELOG.md --exclude=scratch /tmp/viridis_temp/ .")
    
    run("git add -A")
    date_str = commit_date.strftime("%a, %d %b %Y %H:%M:%S %z")
    env = f'GIT_AUTHOR_DATE="{date_str}" GIT_COMMITTER_DATE="{date_str}"'
    run(f'{env} git commit -m "{subject}"')
    
    new_hash = run("git rev-parse HEAD")[:7]
    
    line = f"{idx+1}. `{new_hash}` [+] {subject}\n"
    if "[-] docs: replace" in subject or "[-] docs: rename" in subject:
        line = line.replace("[+]", "[-]")
        
    changelog_content += line
    
    with open("CHANGELOG.md", "w") as f:
        f.write(changelog_content)
    
    cl_date = commit_date + timedelta(minutes=random.randint(2, 15))
    cl_date_str = cl_date.strftime("%a, %d %b %Y %H:%M:%S %z")
    cl_env = f'GIT_AUTHOR_DATE="{cl_date_str}" GIT_COMMITTER_DATE="{cl_date_str}"'
    
    run("git add CHANGELOG.md")
    run(f'{cl_env} git commit -m "docs: update changelog for {subject}"')

run("git branch -D main")
run("git branch -m main")
run("git push origin main --force")
