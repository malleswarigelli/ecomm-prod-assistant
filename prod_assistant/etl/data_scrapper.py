import csv
import time
import re
import os
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

class FlipkartScraper:
    def __init__(self, output_dir="data"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def get_top_reviews(self, product_url, count=2):
        """Get the top reviews for a product."""
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--headless")  
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36")
        
        driver = uc.Chrome(version_main=147, options=options, use_subprocess=True)

        if not product_url.startswith("http"):
            driver.quit()
            return "No reviews found"

        try:
            driver.get(product_url)
            time.sleep(3)
            
            # Dismiss login popups if any
            try:
                driver.find_element(By.XPATH, "//button[contains(text(), '✕')]").click()
                time.sleep(1)
            except Exception:
                pass

            # Scroll down to trigger lazy-loaded reviews
            for _ in range(2):
                ActionChains(driver).send_keys(Keys.END).perform()
                time.sleep(1)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # Target common review text containers on Flipkart product pages
            review_blocks = soup.find_all("div", class_=lambda c: c in ["ZmyHe8", "EPCmJX", "_6K-7Co", "_27M-vq"])
            
            seen = set()
            reviews = []

            for block in review_blocks:
                # Extract clean text from the review block
                text = block.get_text(separator=" ", strip=True)
                if text and text not in seen:
                    # Clean up double spaces or weird characters
                    text = re.sub(r'\s+', ' ', text)
                    reviews.append(text)
                    seen.add(text)
                if len(reviews) >= count:
                    break
        except Exception as e:
            print(f"Error fetching reviews: {e}")
            reviews = []

        driver.quit()
        return " || ".join(reviews) if reviews else "No reviews found"
    
    def scrape_flipkart_products(self, query, max_products=1, review_count=2):
        """Scrape Flipkart products based on a search query."""
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        driver = uc.Chrome(version_main=147, options=options, use_subprocess=True)
        search_url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"
        
        print(f"Opening search URL: {search_url}")
        driver.get(search_url)
        time.sleep(5)  # Give the page ample time to load completely

        try:
            driver.find_element(By.XPATH, "//button[contains(text(), '✕')]").click()
        except Exception:
            pass

        # Parse the page source with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()  # We can close the main driver early to save memory

        # Find all product containers
        items = soup.find_all("div", attrs={"data-id": True})
        print(f"Found {len(items)} raw product containers on the page.")

        products = []
        processed_count = 0

        for idx, item in enumerate(items):
            if processed_count >= max_products:
                break

            try:
                # 1. Extract Product Link & ID
                link_el = item.find("a", href=lambda h: h and "/p/" in h)
                if not link_el:
                    continue  # Skip containers that aren't actual product cards
                
                href = link_el.get("href")
                product_link = href if href.startswith("http") else "https://www.flipkart.com" + href
                
                product_id = "N/A"
                match = re.search(r"/p/(itm[0-9A-Za-z]+)", product_link)
                if match:
                    product_id = match.group(1)

                # 2. Extract Title (with robust fallbacks)
                title = "Unknown Product Title"
                title_el = item.find(class_=lambda c: c in ["KzDlHZ", "wjcEIp", "IRpwZg", "_4rR01T", "CGtC98"])
                if title_el:
                    title = title_el.get_text(strip=True)

                # 3. Extract Price
                price = "N/A"
                price_el = item.find(class_=lambda c: c in ["Nx9bqj", "_30jeq3", "_10g97Y"])
                if price_el:
                    price = price_el.get_text(strip=True)

                # 4. Extract Rating
                rating = "N/A"
                rating_el = item.find(class_=lambda c: c in ["XQDdHH", "_3LWZlK", "Y10E2D"])
                if rating_el:
                    rating = rating_el.get_text(strip=True)

                # 5. Extract Total Reviews Count
                total_reviews = "N/A"
                reviews_el = item.find(class_=lambda c: c in ["Wphh3N", "_2_R_DZ"])
                if reviews_el:
                    reviews_text = reviews_el.get_text(strip=True)
                    match_rev = re.search(r"(\d[\d,]*)\s+Reviews", reviews_text)
                    if match_rev:
                        total_reviews = match_rev.group(1)

                print(f"[{processed_count+1}/{max_products}] Found: {title} | Price: {price} | Rating: {rating}")

                # 6. Fetch individual reviews
                top_reviews = "No reviews found"
                if "flipkart.com" in product_link:
                    print(f"   --> Fetching reviews for: {title[:30]}...")
                    top_reviews = self.get_top_reviews(product_link, count=review_count)

                products.append([product_id, title, rating, total_reviews, price, top_reviews])
                processed_count += 1

            except Exception as e:
                print(f"Error processing item index {idx}: {e}")
                continue

        return products
    
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