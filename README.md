# Overview
This program generates structured financial statement data from annual reports,
using AI.

Two CLI programs are included in the package:

1. pdfscraper
2. reportparser

pdfscraper crawls a company website, and downloads all annual reports into the
./data/<company_name>/<year> directories.

reportparser uses the OpenAI API to parse balance sheet, income statement, and
cash flow statements into structured dicts, and then consolidates the data for
multiple years into tables.


# Setup and Initialization
The python package manager used in development is uv. This should be compatible
with all venv managers. Initialize the project with:

    uv init
    uv pip install -e .

This will make the CLI commands pdfscraper and reportparser available within the
venv.

This program requires an OpenAI API key. To set this up create a file called secret.py in the root folder, and add the variable

    openai_key = "your_openai_api_key"


# Usage

To do end to end webscraping and data structuring, configure a company in
config.json and run the following commands:

    pdfscraper --id volkswagen
    reportparser --id volkswagen

This will download all annual reports, parse them using AI, and create CSVs for
the balance sheet, income statement, and cash flow statements.

## pdfscraper
pdfscraper has 3 independent functions, which can be run independently via CLI or all at once:

1. get_links - webcrawling for PDF links
2. parse_links - sorts out which PDFs are annual reports
3. download_pdfs - downloads PDFs to disk

__1. get_links__

    pdfscraper --id volkswagen --get_links

Saves to ./data/\<company>/links.csv

The crawler must be configured with a root_url, and an option to deep crawl.
With deep crawl enabled, the crawler will search for URLs within URLs to a
specified url_depth. It is recommended to find the webpage that links all the
annual reports together, to save time.

__2. parse_links__

    pdfscraper --id volkswagen --parse_links

Saves to ./data/\<company>/pdfs.csv

The link parser can be configured with special_instructions to help the AI
figure out which links are annual reports. For example, some companies will
publish GAAP adjusted and non-GAAP adjusted reports. A special instruction in
this case may be "In case of duplicates, prefer GAAP adjusted".


__3. download_pdfs__

    pdfscraper --id volkswagen --download_pdfs

Saves to ./data/\<company>/\<year>/

The end result should be a folder structure with the following:

    ./data/volkswagen/2024/Annual_Financial_Statements_of_Volkswagen_AG_as_of_December_31_2024.pdf
    ./data/volkswagen/2023/Annual_Financial_Statements_of_Volkswagen_AG_as_of_December_31_2023.pdf
    ./data/volkswagen/2022/Annual_Financial_Statements_of_Volkswagen_AG_as_of_December_31_2022.pdf
    ./data/volkswagen/2021/Annual_Financial_Statement.pdf
    ./data/volkswagen/2020/Y_2020_e.pdf
    ./data/volkswagen/2019/Y_2019_e.pdf
    ...

As you can see, over the years, companies change the naming convention for these reports. This is where AI is used to sort out where the reports are.

## reportparser

reportparser has 2 independent functions, which can be run independently via CLI or all at once:

1. parse - gets the financial statements from annual reports
2. consolidate - combines the financial statements over multiple years into a data tables

__1. parse__

    reportparser --id volkswagen --parse
    reportparser --id volkswagen --parse --year 2019

This uses OpenAI to read and parse an annual report for the given year's balance
sheet, income statement, and cash flow statement in json format.

The result is saved to ./data/\<company>/\<year>/output.json

In case a PDF exceeds the size or page limits of the OpenAI API, the PDF will be
split up into 3. For example, the file \_balance_sheet_<pdf_name>.pdf will be
generated, which will do a search for the string "balance sheet" and concatenate
all pages + 2 additional pages for each page containing the string.

For example:

    >> reportparser --id volkswagen  --year 2017 --parse --verbose

    Running parser on ids: ['volkswagen']
    Processing data\volkswagen\2017\Y_2017_e.pdf for 2017
    File data\volkswagen\2017\Y_2017_e.pdf too large for a single request. Splitting the PDF.
    Reduced PDF saved as: data\volkswagen\2017\_balance_sheet_Y_2017_e.pdf
    Reduced PDF saved as: data\volkswagen\2017\_income_statement_Y_2017_e.pdf
    Reduced PDF saved as: data\volkswagen\2017\_cash_flow_statement_Y_2017_e.pdf
    Parsing data\volkswagen\2017\_balance_sheet_Y_2017_e.pdf for balance sheet.
    Uploading to openai...
    Data parsing with openai...
    Result:
    {'intangible_assets': 63419, 'property_plant_and_equipment': 55243, 'lease_assets': 39254, 'investment_property': 468, 'equity_accounted_investments': 8205, 'other_equity_investments': 1318, 'financial_services_receivables_noncurrent': 73249, 'other_financial_assets_noncurrent': 8455, 'other_receivables_noncurrent': 2252, 'tax_receivables_noncurrent': 407, 'deferred_tax_assets': 9810, 'noncurrent_assets': 262081, 'inventories': 40415, 'trade_receivables': 13357, 'financial_services_receivables_current': 53145, 'other_financial_assets_current': 11998, 'other_receivables_current': 5346, 'tax_receivables_current': 1339, 'marketable_securities': 15939, 'cash_cash_equivalents_and_time_deposits': 18457, 'assets_held_for_sale': 115, 'current_assets': 160112, 'total_assets': 422193, 'subscribed_capital': 1283, 'capital_reserves': 14551, 'retained_earnings': 81367, 'other_reserves': 560, 'equity_attributable_to_volkswagen_ag_hybrid_capital_investors': 11088, 'noncontrolling_interests': 229, 'equity': 109077, 'financial_liabilities_noncurrent': 81628, 'other_financial_liabilities_noncurrent': 2665, 'other_liabilities_noncurrent': 6199, 'deferred_tax_liabilities': 5636, 'provisions_for_pensions': 32730, 'provisions_for_taxes_noncurrent': 3030, 'other_provisions_noncurrent': 20839, 'noncurrent_liabilities': 152726, 'put_options_and_compensation_rights_granted_to_noncontrolling_interest_shareholders': 3795, 'financial_liabilities_current': 81844, 'trade_payables': 23046, 'tax_payables': 430, 'other_financial_liabilities_current': 8570, 'other_liabilities_current': 15961, 'provisions_for_taxes_current': 1397, 'other_provisions_current': 25347, 'current_liabilities': 160389, 'total_equity_and_liabilities': 422193}
    Parsing data\volkswagen\2017\_income_statement_Y_2017_e.pdf for income statement.
    Uploading to openai...
    Data parsing with openai...
    Result:
    {'sales_revenue': 230682, 'cost_of_sales': 188140, 'gross_result': 42542, 'distribution_expenses': 22710, 'administrative_expenses': 8254, 'other_operating_income': 14500, 'other_operating_expenses': 12259, 'operating_result': 13818, 'share_of_the_result_of_equity_accounted_investments': 3482, 'interest_income': 951, 'interest_expenses': 2317, 'other_financial_result': -2022, 'financial_result': 94, 'earnings_before_tax': 13913, 'income_tax_expense': 2275, 'earnings_after_tax': 11638, 'noncontrolling_interests': 
    10, 'earnings_attributable_to_volkswagen_ag_hybrid_capital_investors': 274, 'earnings_attributable_to_volkswagen_ag_shareholders': 11354}
    Parsing data\volkswagen\2017\_cash_flow_statement_Y_2017_e.pdf for cash flow statement.
    Uploading to openai...
    Data parsing with openai...
    Result:
    {'cash_and_cash_equivalents_at_beginning_of_period': 18833, 'earnings_before_tax': 13913, 'income_taxes_paid': -3664, 'dep_amort_impairment_intangible_ppe_investment_property': 10562, 'amort_impairment_capitalized_development_costs': 3734, 'impairment_losses_equity_investments': 136, 'depreciation_impairment_lease_assets': 7734, 'gain_loss_on_disposal_of_noncurrent_assets_equity_investments': -25, 'share_of_result_of_equity_accounted_investments': 274, 'other_noncash_expense_income': -480, 'change_in_inventories': -4198, 'change_in_receivables_excl_financial_services': -1660, 'change_in_liabilities_excl_financial_liabilities': 5302, 'change_in_provisions': -9443, 'change_in_lease_assets': -11478, 'change_in_financial_services_receivables': -11891, 'cash_flows_from_operating_activities': -1185, 'investments_intangible_assets_property_plant_equipment_investment_property': -13052, 'additions_to_capitalized_development_costs': -5260, 'acquisition_of_subsidiaries': -277, 'acquisition_of_other_equity_investments': -561, 'disposal_of_subsidiaries': 496, 'disposal_of_other_equity_investments': 24, 'proceeds_from_disposal_of_intangible_assets_ppe_investment_property': 411, 'change_in_investments_in_securities': 1376, 'change_in_loans_and_time_deposits': 335, 'cash_flows_from_investing_activities': -16508, 'capital_contributions': 3473, 'dividends_paid': -1332, 'capital_transactions_with_noncontrolling_interest_shareholders': 0, 'proceeds_from_issuance_of_bonds': 30279, 'repayments_of_bonds': -17877, 'changes_in_other_financial_liabilities': 3109, 'lease_payments': -28, 'cash_flows_from_financing_activities': 17625, 'effect_of_exchange_rate_changes_on_cash_and_cash_equivalents': -727, 'net_change_in_cash_and_cash_equivalents': -796, 'cash_and_cash_equivalents_at_end_of_period': 18038, 'securities_loans_and_time_deposits': 26291, 'gross_liquidity': 44329, 'total_third_party_borrowings': -163472, 'net_liquidity': -119143}
    Saving result...


__2. consolidate__

    reportparser --id volkswagen --consolidate

This uses OpenAI to consolidate all the data generated above into CSVs by year. The following files will be generated:

    ./data/\<company>/balance_sheet.csv
    ./data/\<company>/cash_flow_statement.csv
    ./data/\<company>/income_statement.csv


# Configuration

Example:

    {
    "volkswagen": {
            "company_name": "Volkswagen",
            "crawler": {
                "root_url":"https://www.volkswagen-group.com/en/financial-reports-18134",
                "deep":false,
                "url_depth":0
                },
            "link_parser": {
                "special_instructions": "Prefer files named like Y_<year>_e"
                },
            "report_parser": {
                "special_instructions": "Only keep volkswagen division data. Ignore the automotive and financial services divisions."
            },
            "data_consolidator":
            {
                "model": "o3-mini",
                "balance_sheet_special_instructions": "",
                "income_statement_special_instructions": "",
                "cash_flow_statement_special_instructions": ""
            }
        }
    }

Info:

    crawler:
        root_url:       URL to start webcrawler from for PDF links
        deep:           option for deep crawling
        url_depth:      depth for deep crawling
    
    link_parser:
        special_instructions: optional instructions to the AI for identifying annual reports
    
    report_parser:
        special_instructions: optional instructions to the AI for parsing data from the annual reports
    
    data_consolidator:
        model: which OpenAI model to run
        balance_sheet_special_instructions: optional instructions to the AI for parsing balance sheet data
        income_statement_special_instructions: optional instructions to the AI for parsing income statement data
        cash_flow_statement_special_instructions: optional instructions to the AI for parsing cash flow statement sheet data    