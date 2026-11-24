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
import balance_metrics
import clean_cbt
import counterfactual_playoffs
import simulate
import simulation_figures


def main():
    print("########## STEP 1: CLEAN ##########")
    clean.main()

    print("\n########## STEP 1b: CLEAN PAYROLL ##########")
    clean_payroll.main()

    print("\n########## STEP 1c: CBT PAYROLL ##########")
    clean_cbt.main()

    print("\n########## STEP 2: MERGE ##########")
    merge.main()

    print("\n########## STEP 3: ANALYSIS ##########")
    analysis.main()

    print("\n########## STEP 4: SALARY -> WAR -> WINS ##########")
    salary_analysis.main()

    print("\n########## STEP 5: FIGURES & TABLES ##########")
    figures.main()

    print("\n########## STEP 6: COMPETITIVE BALANCE ##########")
    balance_metrics.main()

    print("\n########## STEP 7: SIMULATION ##########")
    simulate.main()

    print("\n########## STEP 8: SIMULATION FIGURES ##########")
    simulation_figures.main()

    print("\n########## STEP 9: COUNTERFACTUAL PLAYOFFS ##########")
    counterfactual_playoffs.main()

    print("\nDone.")


if __name__ == "__main__":
    main()
