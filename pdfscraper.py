import asyncio
import argparse
import json
from pathlib import Path
import pandas as pd
import ssl
import urllib

from classes import PDFScraper

def run():
    # Hack for windows
    ssl._create_default_https_context = ssl._create_unverified_context

    # Parse args for program
    parser = argparse.ArgumentParser(prog="pdfscraper", description="Scrapes a website for annual report PDFs.")
    parser.add_argument(
        "-i", "--id",
        type=str, 
        required=False, 
        help="The ID of the company to scrape."
    )
    parser.add_argument(
        "-a", "--all",
        action="store_true",
        required=False, 
        help="Scrape all companies found in config.json. Ignored when --id is present."
    )
    parser.add_argument(
        "-l", "--get_links",
        action="store_true",
        required=False, 
        help="Only crawl for PDF links from the website."
    )
    parser.add_argument(
        "-p", "--parse_links",
        action="store_true",
        required=False, 
        help="Only find annual reports from the PDF links."
    )
    parser.add_argument(
        "-d", "--download_pdfs",
        action="store_true",
        required=False, 
        help="Only download annual reports from the PDF links."
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
        print(f"Running scraper on ids: {to_run}")

    # Figure out what operation we're running
    get_links = args.get('get_links')
    parse_links = args.get('parse_links')
    download_pdfs = args.get('download_pdfs')
    run_all = not (get_links or parse_links or download_pdfs)

    # Run and save data
    pdfscraper = PDFScraper(verbose=verbose)
    for id in to_run:
        id_config = config[id]
        id_path = f"data\\{id}"
        Path(id_path).mkdir(parents=True, exist_ok=True)
        
        # Scrape all PDF links and save
        if run_all or get_links:
            links = asyncio.run(pdfscraper.get_pdf_links_from_url(id_config['crawler']['root_url'], id_config['crawler']['deep'], id_config['crawler']['url_depth']))
            links.to_csv(f"{id_path}\\links.csv")

        # Use LLM to get a table of annual reports from all candidate PDFs
        if run_all or parse_links:
            try:
                links = pd.read_csv(f"{id_path}\\links.csv", index_col=0).to_dict('records')
                pdfs = pdfscraper.find_annual_reports_from_pdf_links(links=links, special_instructions=id_config['link_parser']['special_instructions'])
                pdfs.to_csv(f"{id_path}\\pdfs.csv")
            except FileNotFoundError:
                print(f"Links not scraped for for {id}")
        
        # Download PDFs from PDF links
        if run_all or download_pdfs:
            try:
                pdfs = pd.read_csv(f"{id_path}\\pdfs.csv", index_col=0)
                for y, row in pdfs.iterrows():
                    report_path = f"{id_path}\\{y}"
                    Path(report_path).mkdir(parents=True, exist_ok=True)
                    try:
                        urllib.request.urlretrieve(row['url'], report_path+f"\\{row['filename']}")
                    except Exception as e:
                        print(f"Error getting data for year {y}:")
                        print(e)
            except FileNotFoundError:
                print(f"PDF links not parsed for {id}")

    return
