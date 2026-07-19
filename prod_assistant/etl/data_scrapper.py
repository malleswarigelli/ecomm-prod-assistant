import csv
import time
import re
import os
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

class FlipkartScraper:
    def __init__(self, output_dir="data"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def extract_details_from_product_page(self, driver, product_url, count=2):
        """Uses the active driver session to extract ratings, reviews, and total reviews."""
        details = {
            "rating": "N/A",
            "total_reviews": "N/A",
            "reviews": "No reviews found"
        }
        
        try:
            driver.get(product_url)
            time.sleep(3.5)  # Allow page to load

            # Scroll down incrementally to trigger lazy-loaded reviews
            for _ in range(3):
                driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(0.8)

            soup = BeautifulSoup(driver.page_source, "html.parser")

            # 1. Extract Rating from Product Page
            rating_el = soup.select_one("div.XQDdHH, div._3LWZlK, div.ip75Yp")
            if rating_el:
                details["rating"] = rating_el.get_text(strip=True)

            # 2. Extract Total Reviews Count from Product Page
            # Look for elements containing "Ratings" and "Reviews"
            for span in soup.find_all("span"):
                txt = span.get_text(strip=True)
                if "Ratings" in txt and "Reviews" in txt:
                    match_rev = re.search(r"(\d[\d,]*)\s+Reviews", txt, re.IGNORECASE)
                    if match_rev:
                        details["total_reviews"] = match_rev.group(1)
                        break
                    # Fallback to general digit extraction if "Reviews" text is split
                    match_any = re.findall(r"[\d,]+", txt)
                    if len(match_any) >= 2:
                        details["total_reviews"] = match_any[1]
                        break

            # 3. Extract Top Reviews
            review_blocks = soup.select("div.ZmyHe8, div.EPCmJX, div._6K-7Co, div._27M-vq, div.col._2wzgFH, div.t-y3g2")
            seen = set()
            reviews = []

            for block in review_blocks:
                text = block.get_text(separator=" ", strip=True)
                # Strip out common UI elements like "Read More" or "Certified Buyer"
                text = re.sub(r'\s*Read More\s*$', '', text, flags=re.IGNORECASE)
                text = re.sub(r'\s*Certified Buyer\s*.*$', '', text, flags=re.IGNORECASE)
                text = re.sub(r'\s+', ' ', text).strip()
                
                if text and len(text) > 15 and text not in seen:
                    reviews.append(text)
                    seen.add(text)
                if len(reviews) >= count:
                    break

            if reviews:
                details["reviews"] = " || ".join(reviews)

        except Exception as e:
            print(f"   --> Error parsing product page: {e}")

        return details
    
    def scrape_flipkart_products(self, query, max_products=1, review_count=2):
        """Scrape Flipkart products using a single persistent browser session."""
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        # Start a single headed browser session
        driver = uc.Chrome(version_main=147, options=options, use_subprocess=True)
        search_url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"
        
        print(f"Opening search URL: {search_url}")
        driver.get(search_url)
        time.sleep(5)  

        try:
            driver.find_element(By.XPATH, "//button[contains(text(), '✕')]").click()
        except Exception:
            pass

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Find all product containers
        items = soup.find_all("div", attrs={"data-id": True})
        print(f"Found {len(items)} raw product containers on the search page.")

        raw_products = []
        processed_count = 0

        # Pass 1: Gather all product links, titles, and prices from the search page
        for item in items:
            if processed_count >= max_products:
                break

            try:
                link_el = item.select_one("a[href*='/p/']")
                if not link_el:
                    continue  
                
                href = link_el.get("href")
                product_link = href if href.startswith("http") else "https://www.flipkart.com" + href
                
                product_id = "N/A"
                match = re.search(r"/p/(itm[0-9A-Za-z]+)", product_link)
                if match:
                    product_id = match.group(1)

                # Extract Title
                title = "Unknown Product Title"
                title_el = item.select_one("div.KzDlHZ, a.wjcEIp, div._4rR01T, a.IRpwZg, a.CGtC98, div.yKfS8Y")
                if title_el:
                    title = title_el.get_text(strip=True)

                # Extract Price
                price = "N/A"
                price_el = item.select_one("div.Nx9bqj, div._30jeq3, div._10g97Y")
                if price_el:
                    price = price_el.get_text(strip=True)

                raw_products.append({
                    "id": product_id,
                    "title": title,
                    "price": price,
                    "link": product_link
                })
                processed_count += 1

            except Exception as e:
                print(f"Error parsing search item: {e}")
                continue

        # Pass 2: Visit each product page using the SAME driver session to get ratings & reviews
        final_products = []
        for idx, prod in enumerate(raw_products):
            print(f"[{idx+1}/{len(raw_products)}] Visiting product page: {prod['title'][:40]}...")
            
            page_details = self.extract_details_from_product_page(driver, prod["link"], count=review_count)
            
            final_products.append([
                prod["id"],
                prod["title"],
                page_details["rating"],
                page_details["total_reviews"],
                prod["price"],
                page_details["reviews"]
            ])
            
            print(f"   --> Rating: {page_details['rating']} | Reviews Count: {page_details['total_reviews']}")
            time.sleep(1.5)  # Polite delay between page loads

        driver.quit()  # Safely close the browser session
        return final_products
    
    def save_to_csv(self, data, filename="product_reviews.csv"):
        """Save the scraped product reviews to a CSV file."""
        if os.path.isabs(filename):
            path = filename
        elif os.path.dirname(filename):
            path = filename
            os.makedirs(os.path.dirname(path), exist_ok=True)
        else:
            path = os.path.join(self.output_dir, filename)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["product_id", "product_title", "rating", "total_reviews", "price", "top_reviews"])
            writer.writerows(data)