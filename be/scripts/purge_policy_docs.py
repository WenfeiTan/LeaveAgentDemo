from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from sqlalchemy import text
from sqlmodel import Session

THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[2]
BE_ROOT = THIS_FILE.parents[1]
for p in (str(PROJECT_ROOT), str(BE_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from be.config.db import engine


def purge_docs(policy_group: str, doc_names: List[str] | None) -> int:
    with Session(engine) as session:
        if doc_names:
            result = session.execute(
                text(
                    """
                    DELETE FROM public.policy_chunks
                    WHERE policy_group = :policy_group
                      AND doc_name = ANY(:doc_names)
                    """
                ),
                {"policy_group": policy_group, "doc_names": doc_names},
            )
        else:
            result = session.execute(
                text("DELETE FROM public.policy_chunks WHERE policy_group = :policy_group"),
                {"policy_group": policy_group},
            )
        session.commit()
        return result.rowcount or 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete policy chunk docs from pgvector table.")
    parser.add_argument("--policy-group", default="FTE_CN_GZ")
    parser.add_argument(
        "--doc-name",
        action="append",
        dest="doc_names",
        help="Doc name to delete, repeatable. If omitted, delete all docs in policy_group.",
    )
    args = parser.parse_args()

    deleted = purge_docs(policy_group=args.policy_group, doc_names=args.doc_names)
    print(f"Deleted {deleted} rows from public.policy_chunks (policy_group={args.policy_group}).")


if __name__ == "__main__":
    main()
