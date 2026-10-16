"""
Run the full pipeline in order: clean → merge → analysis.
Use this instead of running the steps one at a time so nothing is analyzed
from stale files.
"""
import clean
import merge
import analysis


def main():
    print("########## STEP 1: CLEAN ##########")
    clean.main()

    print("\n########## STEP 2: MERGE ##########")
    merge.main()

    print("\n########## STEP 3: ANALYSIS ##########")
    analysis.main()

    print("\nDone.")


if __name__ == "__main__":
    main()
