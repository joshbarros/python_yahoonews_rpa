import os
import time
import re
import urllib.request
import pandas as pd
import logging

from datetime import datetime
from RPA.Browser.Selenium import Selenium
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class NewsScraper:
    def __init__(self, site_url, search_phrase, category, headless=True):
        """
        Initialize the NewsScraper object with the given parameters.

        Args:
            site_url (str): The URL of the news site to scrape.
            search_phrase (str): The phrase to search for within the news articles.
            category (str): The category of news to filter by.
            headless (bool): Whether to run the browser in headless mode. Default is True.
        
        Attributes:
            browser (Selenium): Instance of the Selenium RPA browser.
            timestamp (str): Timestamp for naming output files and directories.
            output_dir (str): Directory to store output files.
            images_dir (str): Directory to store downloaded images.
        """
        self.browser = Selenium()
        self.site_url = site_url
        self.search_phrase = search_phrase
        self.category = category
        self.headless = headless
        
        # Use a single timestamp for the entire session to avoid multiple directories
        self.timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        self.output_dir = self.create_output_directory()
        self.images_dir = os.path.join(self.output_dir, "images")
        os.makedirs(self.images_dir, exist_ok=True)
        logging.info("Initialized NewsScraper with URL: %s, Search Phrase: %s, Category: %s", 
                     site_url, search_phrase, category)
        
    def create_output_directory(self):
        """
        Create an output directory based on the current timestamp and category.

        Returns:
            str: The path to the created output directory.
        
        Logs:
            INFO: Directory creation status.
        """
        category_prefix = self.category.upper().replace(" ", "_")
        output_dir = os.path.join("output", f"{category_prefix}_{self.timestamp}")
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            logging.info("Created output directory: %s", output_dir)
        
        return output_dir
        
    def open_site(self):
        """
        Open the target news site in a browser using the specified URL and options.

        Logs:
            INFO: Browser opening status, including whether it is in headless mode.
        """
        options = {
            "arguments": [
                "--headless"
            ] if self.headless else []
        }
        logging.info("Opening site: %s with headless mode: %s", self.site_url, self.headless)
        self.browser.open_available_browser(self.site_url, options=options)
        
    def filter_news_by_category(self):
        """
        Filter the news articles by the specified category.

        Raises:
            ValueError: If the specified category is not found on the website.
        
        Logs:
            INFO: Category filtering status.
            ERROR: If the specified category is not found.
        """
        if self.category:
            logging.info("Filtering news by category: %s", self.category)
            category_locator = f"xpath://span[text()='{self.category}']"

            # Check if the category exists on the page
            if self.browser.is_element_visible(category_locator):
                self.browser.click_element(category_locator)

                # Wait for the page to reload with the filtered category
                WebDriverWait(self.browser.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h3"))
                )
            else:
                logging.error("Category '%s' not found on the site. Please check the category name.", self.category)
                raise ValueError(f"Category '{self.category}' not found.")
    
    def scroll_and_load(self):
        """
        Scroll the page and load more news articles until a sufficient number are loaded.

        Returns:
            list: A list of web elements representing the loaded news articles.
        
        Logs:
            INFO: Number of articles loaded after each scroll attempt.
            INFO: When no more articles are loaded, exiting the loop.
        """
        logging.info("Scrolling and loading news articles...")
        articles = []
        previous_count = 0
        
        while len(articles) < 20:
            self.browser.execute_javascript("window.scrollBy(0, document.body.scrollHeight/3);")
            time.sleep(4)  # Wait for content to load
            
            articles = self.browser.get_webelements(locator="css:li.stream-item")
            logging.info("Loaded %d articles...", len(articles))

            if len(articles) == previous_count:
                logging.info("No more articles loaded, exiting scroll loop.")
                break
            
            previous_count = len(articles)

        return articles[:20]  # Return only the first 20 items
    
    def extract_image_url(self, article):
        """
        Extract the image URL from a given article element.

        Args:
            article (WebElement): The web element representing a news article.

        Returns:
            str: The URL of the image, or None if the image cannot be found.
        
        Logs:
            INFO: Successfully extracted image URL.
            ERROR: Failed to extract image URL.
        """
        try:
            image_element = article.find_element(By.CSS_SELECTOR, "img")
            image_url = image_element.get_attribute("src")
            logging.info("Extracted image URL: %s", image_url)
            return image_url
        except Exception as e:
            logging.error("Failed to extract image URL: %s", e)
            return None

    def extract_news_data(self):
        """
        Extract data from the loaded news articles, including title, description, and metadata.

        Returns:
            list: A list of dictionaries, each containing data for a news article.
        
        Logs:
            INFO: Extraction status for each news item.
            ERROR: If an error occurs while extracting a particular article.
        """
        logging.info("Extracting news data...")
        articles = self.scroll_and_load()
        
        news_data = []
        for article in articles:
            try:
                title_element = article.find_element(By.CSS_SELECTOR, "h3.stream-item-title")
                
                # Use WebDriverWait to wait for the description to be present
                description_element = WebDriverWait(article, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "p[data-test-locator='stream-item-summary']"))
                )
                
                image_url = self.extract_image_url(article)
                
                news_item = {
                    "title": title_element.text,
                    "description": description_element.text if description_element else "No description available",
                    "date": time.strftime("%Y-%m-%d"),
                    "picture_filename": self.download_image(image_url, title_element.text),
                    "search_phrase_count": self.search_phrase_count(title_element.text, description_element.text if description_element else "")
                }
                news_data.append(news_item)
                logging.info("Extracted news item: %s", news_item)
            except Exception as e:
                logging.error("Error extracting article: %s", e)

        return news_data
    
    def search_phrase_count(self, title, description):
        """
        Count occurrences of the search phrase in the article title and description.

        Args:
            title (str): The title of the article.
            description (str): The description of the article.

        Returns:
            int: The number of times the search phrase appears in the title and description.
        
        Logs:
            INFO: The count of the search phrase in the title and description.
        """
        count = title.lower().count(self.search_phrase.lower()) + description.lower().count(self.search_phrase.lower())
        logging.info("Search phrase count in title '%s' and description '%s': %d", title, description, count)
        return count
    
    def download_image(self, image_url, title):
        """
        Download the image from the given URL and save it locally.

        Args:
            image_url (str): The URL of the image to download.
            title (str): The title of the article, used to generate the image filename.

        Returns:
            str: The filename of the downloaded image, or "placeholder.png" if the download fails.
        
        Logs:
            INFO: Successful image download and file path.
            ERROR: If the image download fails.
        """
        if not image_url:
            return "placeholder.png"

        try:
            title_sanitized = re.sub(r'\W+', '', title[:15])
            category_prefix = self.category.upper().replace(" ", "_")
            image_filename = f"{category_prefix}_{title_sanitized}_{self.timestamp}.jpg"
            image_path = os.path.join(self.images_dir, image_filename)

            urllib.request.urlretrieve(image_url, image_path)
            logging.info("Downloaded image to: %s", image_path)

            return image_filename
        except Exception as e:
            logging.error("Failed to download image: %s", e)
            return "placeholder.png"
    
    def save_to_excel(self, news_data):
        """
        Save the extracted news data to an Excel file.

        Args:
            news_data (list): A list of dictionaries containing news article data.
        
        Logs:
            INFO: The path to the saved Excel file.
        """
        category_prefix = self.category.upper().replace(" ", "_")
        file_name = os.path.join(self.output_dir, f"{category_prefix}_news_data_{self.timestamp}.xlsx")
        df = pd.DataFrame(news_data)
        df.to_excel(file_name, index=False)
        logging.info("Data saved to %s", file_name)
        self.save_scrape_log(news_data, file_name)
    
    def save_scrape_log(self, news_data, file_name):
        """
        Save a log of the scraping session, including metadata and a summary of extracted articles.

        Args:
            news_data (list): A list of dictionaries containing news article data.
            file_name (str): The path to the saved Excel file containing news data.
        
        Logs:
            INFO: The path to the saved scrape log file.
            ERROR: If saving the scrape log fails.
        """
        log_filename = os.path.join(self.output_dir, f"{self.category.upper().replace(' ', '_')}_scrape_log_{self.timestamp}.txt")
        try:
            with open(log_filename, 'w') as log_file:
                log_file.write(f"Scraping Report - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
                log_file.write(f"URL: {self.site_url}\n")
                log_file.write(f"Category: {self.category}\n")
                log_file.write(f"Search Phrase: {self.search_phrase}\n")
                log_file.write(f"Excel File: {file_name}\n\n")
                log_file.write("Extracted News Articles:\n")
                for news_item in news_data:
                    log_file.write(f"- Title: {news_item['title']}\n")
                    log_file.write(f"  Description: {news_item['description']}\n")
                    log_file.write(f"  Date: {news_item['date']}\n")
                    log_file.write(f"  Picture Filename: {news_item['picture_filename']}\n")
                    log_file.write(f"  Search Phrase Count: {news_item['search_phrase_count']}\n\n")
            logging.info("Scraping log saved to: %s", log_filename)
        except Exception as e:
            logging.error("Failed to save scraping log: %s", e)
    
    def close(self):
        """
        Close all open browsers.

        Logs:
            INFO: Browser closing status.
        """
        logging.info("Closing all browsers...")
        self.browser.close_all_browsers()
