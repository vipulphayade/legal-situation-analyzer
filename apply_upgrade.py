
import os
import shutil
import zipfile
from pathlib import Path

ROOT = Path.cwd()

ZIP_NAME = "v13_retrieval_upgrade_full.zip"

BACKEND_TARGETS = {
    "api/embeddings.py": "api/embeddings.py",
    "api/hybrid_retrieval.py": "api/hybrid_retrieval.py",
    "api/reranker.py": "api/reranker.py",
    "api/scoring.py": "api/scoring.py",
    "api/search.py": "api/search.py",
}

DATASET_TARGETS = {
    "dataset/improved_full_dataset.json": "dataset/improved_full_dataset.json",
    "dataset/improved_dataset_sample.json": "dataset/improved_dataset_sample.json",
}

BACKUP_DIR = ROOT / "backup_before_v13_upgrade"

def safe_copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

def backup_file(path):
    if path.exists():
        backup_path = BACKUP_DIR / path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_path)

def main():
    zip_path = ROOT / ZIP_NAME

    if not zip_path.exists():
        print(f"ERROR: {ZIP_NAME} not found in root folder.")
        return

    extract_dir = ROOT / "_v13_upgrade_extract"

    if extract_dir.exists():
        shutil.rmtree(extract_dir)

    extract_dir.mkdir(parents=True)

    print("Extracting upgrade package...")

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    print("Creating backup...")

    BACKUP_DIR.mkdir(exist_ok=True)

    for target in list(BACKEND_TARGETS.values()) + list(DATASET_TARGETS.values()):
        backup_file(Path(target))

    print("Applying backend updates...")

    for src_rel, dst_rel in BACKEND_TARGETS.items():
        src = extract_dir / src_rel
        dst = ROOT / dst_rel

        if src.exists():
            safe_copy(src, dst)
            print(f"Updated: {dst_rel}")

    print("Applying dataset updates...")

    dataset_updated = False

    for src_rel, dst_rel in DATASET_TARGETS.items():
        src = extract_dir / src_rel
        dst = ROOT / dst_rel

        if src.exists():
            safe_copy(src, dst)
            dataset_updated = True
            print(f"Updated: {dst_rel}")

    print("\n===================================")
    print("Upgrade completed successfully.")
    print("===================================\n")

    print("IMPORTANT NEXT STEPS:")
    print("1. Rebuild embeddings/vector index")
    print("2. Restart backend server")
    print("3. Test key retrieval queries")
    print("\nRecommended validation query:")
    print("'notice period for conducting managing committee meeting'")
    print("\nExpected:")
    print("- Bye-law 132 should rank above procedural clauses")

    print("\nBackup created at:")
    print(BACKUP_DIR)

if __name__ == "__main__":
    main()
