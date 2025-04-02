import asyncio
import argparse
import json
import os
from pathlib import Path
import pandas as pd

from classes import DataParser

def run():
    # Parse args for program
    parser = argparse.ArgumentParser(prog="reportparser", description="Scrapes a website for annual report PDFs.")
    parser.add_argument(
        "-i", "--id",
        type=str, 
        required=False, 
        help="The ID of the company to work on."
    )
    parser.add_argument(
        "-a", "--all",
        action="store_true",
        required=False, 
        help="Work on all companies found in config.json. Ignored when --id is present."
    )
    parser.add_argument(
        "-y", "--year",
        type=int,
        required=False,
        help="Work on a single year. Only valid when --parse."
    )
    parser.add_argument(
        "-p", "--parse",
        action="store_true",
        required=False,
        help="Only parse report(s). By default, parsing and consolidating are run."
    )
    parser.add_argument(
        "-c", "--consolidate",
        action="store_true",
        required=False,
        help="Only consolidate data for all reports. By default, parsing and consolidating are run."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        required=False, 
        help="Enable verbose mode"
    )
    args = vars(parser.parse_args())
    verbose = args.get('verbose')

     # Figure out which companies to run
    if (args.get('id') is None and args.get('all')==False):
        print("Must specify a company to scrape using --id or --all")
        return
    
    with open('config.json', 'r') as f:
        config = json.load(f)

    to_run = []
    if args.get('id'):
        if args.get('id') in config.keys():
            to_run.append(args.get('id'))
        else:
            print(f"No config found for {args.get('id')}")
    elif args.get('all'):
        to_run = list(config.keys())

    if verbose:
        print(f"Running parser on ids: {to_run}")

    # Figure out what operation we're running
    run_parse = args.get('parse')
    run_consolidate = args.get('consolidate')
    run_all = not (run_parse or run_consolidate)

    # Process reports
    dataparser = DataParser(verbose=verbose)
    for id in to_run:
        id_config = config[id]
        id_path = f"data\\{id}"

        # Parser
        if run_all or run_parse:
            pdfs = pd.read_csv(f"{id_path}\\pdfs.csv", index_col=0)
            if run_parse:
                years = [args.get('year')]
            else:
                years = pdfs.index.to_list()

            for y in years:
                report_path = f"{id_path}\\{y}"
                report_name = pdfs.loc[y]['filename']
                if os.path.exists(f"{report_path}\\{report_name}"):
                    dataparser.parse_report_for_year(report_path=report_path,
                                                     report_name=report_name,
                                                     year=y,
                                                     special_instructions=id_config['report_parser']['special_instructions'])
                else:
                    print(f"Report does not exist: {report_name}")
                    break
            if run_parse:
                return

        # Consolidation
        if run_all or run_consolidate:
            pdfs = pd.read_csv(f"{id_path}\\pdfs.csv", index_col=0)

            balance_sheet = []
            income_statement = []
            cash_flow_statement = []
            for y in pdfs.index:
                output_file = f"{id_path}\\{y}\\output.json"
                if os.path.exists(output_file):
                    with open(output_file) as f:
                        statement = json.load(f)
                        statement['balance_sheet'].update({'year':y})
                        balance_sheet.append(statement['balance_sheet'])

                        statement['income_statement'].update({'year':y})
                        income_statement.append(statement['income_statement'])

                        statement['cash_flow_statement'].update({'year':y})
                        cash_flow_statement.append(statement['cash_flow_statement'])

            df_balance_sheet = dataparser.consolidate_reports(balance_sheet, 'balance sheet', id_config['data_consolidator']['balance_sheet_special_instructions'], id_config['data_consolidator']['model']) 
            df_income_statement = dataparser.consolidate_reports(income_statement, 'income statement', id_config['data_consolidator']['income_statement_special_instructions'], id_config['data_consolidator']['model']) 
            df_cash_flow_statement = dataparser.consolidate_reports(cash_flow_statement, 'cash flow statement', id_config['data_consolidator']['cash_flow_statement_special_instructions'], id_config['data_consolidator']['model'])

            df_balance_sheet.to_csv(f"{id_path}\\balance_sheet.csv")
            df_income_statement.to_csv(f"{id_path}\\income_statement.csv")
            df_cash_flow_statement.to_csv(f"{id_path}\\cash_flow_statement.csv")

            return