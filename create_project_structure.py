#!/usr/bin/env python3

"""
Create the directory structure for the EAM Maintenance History PoC monorepo.

- Safe to run multiple times (idempotent)
- Does not overwrite existing files
- Creates directories and empty placeholder files
"""

from pathlib import Path

PROJECT_ROOT = Path(".")  # run from repo root


DIRECTORIES = [
    ".devcontainer",
    ".github/prompts",
    ".github/workflows",
    ".github/ISSUE_TEMPLATE",
    "contracts/schemas",
    "contracts/asyncapi",
    "contracts/openapi",
    "contracts/contract",
    "platform/bootstrap",
    "services/eam-sim",
    "services/cdc-sim",
    "services/normalizer",
    "services/data-product",
    "services/consumers/notif-pull",
    "services/consumers/ecst",
    "docs/adr",
]

FILES = [
    # Root files
    "README.md",
    "AGENTS.md",
    "Makefile",

    # Devcontainer
    ".devcontainer/devcontainer.json",
    ".devcontainer/docker-compose.codespaces.yml",

    # GitHub / Copilot
    ".github/copilot-instructions.md",
    ".github/prompts/README.md",
    ".github/workflows/ci.yml",

    # Contracts
    "contracts/contract/product.contract.yaml",

    # Platform
    "platform/docker-compose.yml",
    "platform/bootstrap/00_create_topics.sh",
    "platform/bootstrap/01_register_artifacts.sh",
    "platform/bootstrap/02_seed_keycloak.sh",
    "platform/bootstrap/03_init_db.sql",

    # Documentation
    "docs/ARCHITECTURE.md",
    "docs/RUNBOOK.md",
    "docs/adr/0001-cdc-before-after.md",
    "docs/adr/0002-ecst-embedded-asset-summary.md",
]


def create_directories():
    for d in DIRECTORIES:
        path = PROJECT_ROOT / d
        path.mkdir(parents=True, exist_ok=True)
        print(f"✅ directory: {path}")


def create_files():
    for f in FILES:
        path = PROJECT_ROOT / f
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
            print(f"📝 file: {path}")
        else:
            print(f"↪️  exists: {path}")


def main():
    print("🚀 Creating EAM Maintenance PoC project structure...\n")
    create_directories()
    create_files()
    print("\n✅ Project structure ready.")


if __name__ == "__main__":
    main()
