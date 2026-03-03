import csv
import os
import re
import time
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import keys
from selenium.webdriver.common.action_chains import ActionChains

class FlipkartScraper:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
    def get_top_reviews(self, product_url, count=2):
        pass
   
    def scrap_flipkart_products(self, query, max_products=1, review_count=2):
        pass

    def save_to_csv(self, data, filename="product_reviews.csv"):
        pass

if __name__ == "__main__":
    scraper = FlipkartScraper(output_dir="output")
    query = "laptop"
    scraper.scrap_flipkart_products(query=query, max_products=1, review_count=2)