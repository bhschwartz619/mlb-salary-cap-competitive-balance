"""
Run the full pipeline in order: clean → clean payroll → merge → analysis → salary analysis → figures.
Use this instead of running the steps one at a time so nothing is analyzed
from stale files.

"""
import clean
import clean_payroll
import merge
import analysis
import salary_analysis
import figures


def main():
    print("########## STEP 1: CLEAN ##########")
    clean.main()

    print("\n########## STEP 1b: CLEAN PAYROLL ##########")
    clean_payroll.main()

    print("\n########## STEP 2: MERGE ##########")
    merge.main()

    print("\n########## STEP 3: ANALYSIS ##########")
    analysis.main()

    print("\n########## STEP 4: SALARY -> WAR -> WINS ##########")
    salary_analysis.main()

    print("\n########## STEP 5: FIGURES & TABLES ##########")
    figures.main()

    print("\nDone.")


if __name__ == "__main__":
    main()
