from news_scraper import NewsScraper
from utils import get_config

def main():
    """
    Main entry point for the RPA process.

    This function coordinates the entire RPA workflow:
    1. Load the configuration using `get_config()`.
    2. Initialize the `NewsScraper` object with the loaded configuration.
    3. Perform a series of operations to scrape news data:
        - Open the site specified in the configuration.
        - Filter news articles by the specified category.
        - Extract the news data.
        - Save the extracted news data to an Excel file.
    4. Close the scraper once the process is complete.
    """
    config = get_config()
    scraper = NewsScraper(
        site_url=config["site_url"],
        search_phrase=config["search_phrase"],
        category=config["category"],
        headless=config.get("headless", True)
    )
    
    scraper.open_site()
    scraper.filter_news_by_category()
    news_data = scraper.extract_news_data()
    scraper.save_to_excel(news_data)
    scraper.close()
    
if __name__ == "__main__":
    main()
