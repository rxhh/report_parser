import os
import asyncio
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.deep_crawling import BestFirstCrawlingStrategy
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
from openai import OpenAI
import pandas as pd
import PyPDF2
from secret import openai_key

class PDFScraper():
    def __init__(self, verbose):
        self.verbose = verbose
        self.client = OpenAI(api_key=openai_key)
        return
    
    async def get_pdf_links_from_url(self, root_url, deep=False, url_depth=1):
        """
        Crawls a root_url for all pdf links.
        With deep=True, crawling occurs on found links, with a depth of url_depth.
        """
        browser_config = BrowserConfig(
            browser_type='chromium',
            headless=True,
            verbose=self.verbose
            )

        deep_crawl_strategy = None
        if deep:
            scorer = KeywordRelevanceScorer(
            keywords=["annual", "financial", "report", "pdf", "download", "investor", "publication"],
            weight=0.7
            )
            deep_crawl_strategy = BestFirstCrawlingStrategy(
                max_depth=url_depth,
                url_scorer=scorer,
                include_external=False
                )

        crawl_config = CrawlerRunConfig(deep_crawl_strategy=deep_crawl_strategy)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(
                url=root_url,
                config=crawl_config,
            )

        if type(result) is list:
            pdfs = []
            for r in result:
                for l in r.links.get("internal", []):
                    if '.pdf' in l['href']:
                        pdfs.append(l)
                for l in r.links.get("external", []):
                    if '.pdf' in l['href']:
                        pdfs.append(l)
        else:
            pdfs = []
            for l in result.links.get("internal", []):
                if '.pdf' in l['href']:
                    pdfs.append(l)
            for l in result.links.get("external", []):
                if '.pdf' in l['href']:
                    pdfs.append(l)
        if self.verbose:
            print(pdfs)
        return pd.DataFrame(pdfs)

    def find_annual_reports_from_pdf_links(self, links, special_instructions):
        system_prompt = f"""
        You are a utility which picks out the relevant annual reports from a list of URLs.
        """

        prompt = f"""
        Get the annual reports from a list of candidate PDF URLs. There must be only one
        annual report per year. Are are looking for the one with financial statements.

        Make sure the year is correct. If a date is present in a URL or filename, it
        might be an upload date. To resolve this, note that the annual report is always
        uploaded after the year its for.

        Sort the output by year descending.
    
        If there are missing years between the newest and oldest year, there's a high
        likelihood that data isn't missing. Try to ensure those gaps are filled.

        Special instructions: {special_instructions}
        Dataset: {links}
        """

        schema = {
            "type": "object",
            "properties": {
                "annual_reports": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "year": {
                                "type": "integer",
                                "description": "The fiscal year of the report."
                            },
                            "filename": {
                                "type": "string",
                                "description": "The name of the PDF file."
                            },
                            "url": {
                                "type": "string",
                                "description": "The URL linking to the annual report PDF."
                            }
                        },
                        "required": ["year", "filename", "url"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["annual_reports"],
            "additionalProperties": False
        }

        if self.verbose:
            print("Querying ChatGPT to find annual reports from PDF links...")
        response = self.client.responses.create(
            model="o3-mini",
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "annual_report",
                    "schema": schema,
                    "strict": True
                }
            }
        )
        annual_reports = pd.DataFrame(json.loads(response.output_text)['annual_reports']).set_index('year')
        if self.verbose:
            print(annual_reports)
            suspicious_years = []
            for year in range(1980, 2025):
                if (str(year) in json.dumps(links)) and (not year in annual_reports.index.values):
                    suspicious_years.append(year)
            if len(suspicious_years) > 0:
                print(f"Warning: years found in links without annual reports: {suspicious_years}")

        return annual_reports
    
class DataParser():
    def __init__(self, verbose):
        self.verbose = verbose
        self.client = OpenAI(api_key=openai_key)
        return
    
    def parse_report_for_year(self, report_path, report_name, year, special_instructions=""):
        pdf_path = f"{report_path}\\{report_name}"
        filesize = os.path.getsize(pdf_path)/1024**2
        final_dict = None
        if self.verbose:
            print(f"Processing {pdf_path} for {year}")

        expected_balance_sheet = [
            "total_assets", "current_assets", "non_current_assets",
            "total_liabilities", "current_liabilities", "non_current_liabilities",
            "total_shareholders_equity", "share_capital", "retained_earnings"
            ]
        expected_income_statement = [
            "total_revenue", "total_expenses", "net_gains", "net_losses",
            "net_income", "earnings_per_share"
            ]
        
        expected_cash_flow_statement = [
            "cash_and_cash_equivalents_at_beginning_of_period",
            "cash_and_cash_equivalents_at_end_of_period",

            ]

        with open(pdf_path, "rb") as infile:
            reader = PyPDF2.PdfReader(infile)
            num_pages = len(reader.pages)

            # Split too large PDFs
            if filesize > 32 or num_pages > 100:
                print(f"File {pdf_path} too large for a single request. Splitting the PDF.")

                balance_sheet_pages = []
                income_statement_pages = []
                cash_flow_statement_pages = []
                    
                for i in range(num_pages):
                    page = reader.pages[i]
                    text = page.extract_text()
                    if text and 'balance sheet' in text.lower():
                        for j in range(i, min(i + 3, num_pages)):
                            if j not in balance_sheet_pages:
                                balance_sheet_pages.append(j)
                    if text and 'income statement' in text.lower():
                        for j in range(i, min(i + 3, num_pages)):
                            if j not in income_statement_pages:
                                income_statement_pages.append(j)
                    if text and 'cash flow statement' in text.lower():
                        for j in range(i, min(i + 3, num_pages)):
                            if j not in income_statement_pages:
                                cash_flow_statement_pages.append(j)
                    
                balance_sheet_pdf = f"{report_path}\\_balance_sheet_{report_name}"
                income_statement_pdf = f"{report_path}\\_income_statement_{report_name}"
                cash_flow_statement_pdf = f"{report_path}\\_cash_flow_statement_{report_name}"
                self.save_reduced_pdf(pdf_path, balance_sheet_pdf, balance_sheet_pages)
                self.save_reduced_pdf(pdf_path, income_statement_pdf, income_statement_pages)
                self.save_reduced_pdf(pdf_path, cash_flow_statement_pdf, cash_flow_statement_pages)

                balance_sheet_dict = self.parse_reduced_file(balance_sheet_pdf, 'balance sheet', year, special_instructions, expected_balance_sheet)
                income_statement_dict = self.parse_reduced_file(income_statement_pdf, 'income statement', year, special_instructions, expected_income_statement)
                cash_flow_statement_dict = self.parse_reduced_file(cash_flow_statement_pdf, 'cash flow statement', year, special_instructions, expected_cash_flow_statement)

                final_dict = {
                    'year': year,
                    'balance_sheet': balance_sheet_dict,
                    'income_statement': income_statement_dict,
                    'cash_flow_statement': cash_flow_statement_dict
                }
                
            # Parse a small PDF
            else:
                if self.verbose:
                    print(f"Parsing {report_name} for all data.")
                    print(f"Uploading to openai...")
                openai_file = self.client.files.create(
                    file=open(pdf_path, "rb"),
                    purpose="user_data"
                )

                if self.verbose:
                    print(f"Data parsing with openai...")

                instruction = f"""
                    From the given annual report, extract the balance sheet, income statement, and 
                    cash flow statement data for the current year. The current year is {year}.

                    Your response should simply be a JSON dictionary, ready to load into json.loads (no headers).
                    The top level dict keys must be balance_sheet, income_statement, and
                    cash_flow_statement. The values for these keys is another dict, where the items
                    are the relevant data you find. Do not nest another dictionary beyond this
                    level. Make sure there are no duplicate keys. I would like dict keys in
                    lowercase_with_underscores.

                    I am expecting the following keys for the balance sheet: {expected_balance_sheet}
                    I am expecting the following keys for the income statement: {expected_income_statement}
                    I am expecting the following keys for the cash flow statement: {expected_cash_flow_statement}
                    These are the minimum required sets, additional keys are expected. Include all data you can,
                    while maintaining accuracy in data categorization.

                    Special instructions: {special_instructions}
                    """
                response = self.client.responses.create(
                    model="o1",
                    input=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_file",
                                    "file_id": openai_file.id,
                                },
                                {
                                    "type": "input_text",
                                    "text": instruction,
                                },
                            ]
                        }
                    ]
                )
                output = json.loads(response.output_text)
                if self.verbose:
                    print(f"Result:")
                    print(output)
    
                final_dict = {'year':year}
                final_dict.update(output)

        if final_dict:
            if self.verbose:
                print(f"Saving result...")
            with open(f"{report_path}\\output.json", 'w') as f:
                    json.dump(final_dict, f)

    def parse_reduced_file(self, file, find_str, year, special_instructions, expected_columns):
        if self.verbose:
            print(f"Parsing {file} for {find_str}.")
            print(f"Uploading {find_str} to openai...")
        openai_file = self.client.files.create(
            file=open(file, "rb"),
            purpose="user_data"
        )

        if self.verbose:
            print(f"Data parsing with openai...")
        instruction = f"""
        From the given annual report, extract the {find_str} data for the current
        year. The current year is {year}.

        Your response should simply be a JSON dictionary, ready to load into json.loads (no headers).
        Dict items are the relevant data you find. Make sure there are no duplicate
        keys. Do not give a nested dictionary. I would like dict keys in
        lowercase_with_underscores.

        I am expecting the following keys at minimum: {expected_columns}
        Additional keys are expected. Include all data you can, while maintaining accuracy in data categorization.

        Special instructions: {special_instructions}
        """
        response = self.client.responses.create(
            model="o1",
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "file_id": openai_file.id,
                        },
                        {
                            "type": "input_text",
                            "text": instruction,
                        },
                    ]
                }
            ]
        )
        try:
            output = json.loads(response.output_text)
            if self.verbose:
                print(f"Result:")
                print(output)
            return output
        
        except Exception as e:
            print(f"Failed to extract {find_str} from {file}. AI response:")
            print(f"{response.output_text}")
            print(e)
            return {}

    def save_reduced_pdf(self, input_pdf_path, output_pdf_path, page_numbers):
        """
        Create a reduced PDF from the input_pdf_path containing only the pages listed in page_numbers.
        
        Parameters:
            input_pdf_path (str): Path to the original PDF.
            output_pdf_path (str): Path where the reduced PDF will be saved.
            page_numbers (list): A list of page numbers (0-indexed) to include in the new PDF.
        """
        with open(input_pdf_path, "rb") as infile:
            reader = PyPDF2.PdfReader(infile)
            writer = PyPDF2.PdfWriter()
            
            # Iterate through the list of page numbers
            for page_num in page_numbers:
                # Check if the page number is within the range of available pages
                if page_num < len(reader.pages):
                    writer.add_page(reader.pages[page_num])
                else:
                    print(f"Page {page_num + 1} is out of range. Skipping.")
            
            # Save the reduced PDF
            with open(output_pdf_path, "wb") as outfile:
                writer.write(outfile)
            print(f"Reduced PDF saved as: {output_pdf_path}")
    
    def consolidate_reports(self, data, data_str, special_instructions, model):
        instruction = f"""
            Consolidate the given data.

            Each item in the given list is a {data_str} for a given year.

            The keys need to be consolidated across the years.

            You may leave some keys as None if there is no matching data for a given year.
            However, try your best to leave as little data gaps as possible. If there is a
            reported figure for a given year, it is likely in all years, or subsequent
            years. For example, "assets" may change to "total_assets", but these should be
            merged. There should be no nesting of dictionaries; the data for a given year
            should be numbers.

            Use your knowledge about the common items occurring in a {data_str}.

            Your output should be json.loads ready (no headers).

            Special instructions:
            {special_instructions}

            Data:
            {data}
            """
        if self.verbose:
            print(f"{data_str}.")
        response = self.client.responses.create(
            model=model,
            input=instruction
        )

        result = pd.DataFrame(json.loads(response.output_text)).set_index('year')
        if self.verbose:
            print(result)

        return result