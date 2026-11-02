"""
Run the full pipeline in order: clean → clean payroll → merge → analysis.
Use this instead of running the steps one at a time so nothing is analyzed
from stale files.

(download_payroll.py is a one-time download and is not run here.)
"""
import clean
import clean_payroll
import merge
import analysis


def main():
    print("########## STEP 1: CLEAN ##########")
    clean.main()

    print("\n########## STEP 1b: CLEAN PAYROLL ##########")
    clean_payroll.main()

    print("\n########## STEP 2: MERGE ##########")
    merge.main()

    print("\n########## STEP 3: ANALYSIS ##########")
    analysis.main()

    print("\nDone.")


if __name__ == "__main__":
    main()
