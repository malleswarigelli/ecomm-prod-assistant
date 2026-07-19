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

    def get_product_details_and_reviews(self, product_url, count=2):
        """Visits the product page to extract reviews, and acts as a fallback for ratings/reviews."""
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--headless=new")  # Use modern headless engine to bypass bot detection
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        driver = uc.Chrome(version_main=147, options=options, use_subprocess=True)
        
        details = {
            "rating": "N/A",
            "total_reviews": "N/A",
            "reviews": "No reviews found"
        }

        if not product_url.startswith("http"):
            driver.quit()
            return details

        try:
            driver.get(product_url)
            time.sleep(4)
            
            try:
                driver.find_element(By.XPATH, "//button[contains(text(), '✕')]").click()
                time.sleep(1)
            except Exception:
                pass

            # Scroll down incrementally to trigger lazy-loaded reviews
            for _ in range(3):
                driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(1)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # --- FALLBACK 1: Extract Rating from Product Page ---
            rating_el = soup.select_one("div.XQDdHH, div._3LWZlK")
            if rating_el:
                details["rating"] = rating_el.get_text(strip=True)

            # --- FALLBACK 2: Extract Total Reviews from Product Page ---
            reviews_el = soup.select_one("span.Wphh3N, span._2_R_DZ")
            if reviews_el:
                reviews_text = reviews_el.get_text(strip=True)
                match_rev = re.search(r"(\d[\d,]*)\s+(Reviews|Ratings)", reviews_text, re.IGNORECASE)
                if match_rev:
                    details["total_reviews"] = match_rev.group(1)

            # --- Extract Top Reviews ---
            review_blocks = soup.select("div.ZmyHe8, div.EPCmJX, div._6K-7Co, div._27M-vq, div.col._2wzgFH")
            seen = set()
            reviews = []

            for block in review_blocks:
                text = block.get_text(separator=" ", strip=True)
                text = re.sub(r'\s*Read More\s*$', '', text, flags=re.IGNORECASE)
                text = re.sub(r'\s+', ' ', text)
                
                if text and len(text) > 15 and text not in seen:
                    reviews.append(text)
                    seen.add(text)
                if len(reviews) >= count:
                    break
            
            if reviews:
                details["reviews"] = " || ".join(reviews)

        except Exception as e:
            print(f"   --> Error fetching product page details: {e}")

        driver.quit()
        return details
    
    def scrape_flipkart_products(self, query, max_products=1, review_count=2):
        """Scrape Flipkart products based on a search query."""
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
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
        driver.quit()  

        # Find all product containers (handles both list and grid layouts)
        items = soup.find_all("div", attrs={"data-id": True})
        print(f"Found {len(items)} raw product containers on the page.")

        products = []
        processed_count = 0

        for idx, item in enumerate(items):
            if processed_count >= max_products:
                break

            try:
                # 1. Extract Product Link & ID
                link_el = item.select_one("a[href*='/p/']")
                if not link_el:
                    continue  
                
                href = link_el.get("href")
                product_link = href if href.startswith("http") else "https://www.flipkart.com" + href
                
                product_id = "N/A"
                match = re.search(r"/p/(itm[0-9A-Za-z]+)", product_link)
                if match:
                    product_id = match.group(1)

                # 2. Extract Title
                title = "Unknown Product Title"
                title_el = item.select_one("div.KzDlHZ, a.wjcEIp, div._4rR01T, a.IRpwZg, a.CGtC98, div.yKfS8Y")
                if title_el:
                    title = title_el.get_text(strip=True)
                else:
                    for tag in ["a", "div"]:
                        for el in item.find_all(tag):
                            if not el.find("div"):  
                                txt = el.get_text(strip=True)
                                if 15 < len(txt) < 100 and "₹" not in txt and any(word.lower() in txt.lower() for word in query.split()):
                                    title = txt
                                    break
                        if title != "Unknown Product Title":
                            break

                # 3. Extract Price
                price = "N/A"
                price_el = item.select_one("div.Nx9bqj, div._30jeq3, div._10g97Y")
                if price_el:
                    price = price_el.get_text(strip=True)
                else:
                    price_text = item.find(string=re.compile(r"₹"))
                    if price_text:
                        price = price_text.strip()

                # 4. Extract Rating (Initial attempt from search page)
                rating = "N/A"
                rating_el = item.select_one("div.XQDdHH, div._3LWZlK, span.Y10E2D")
                if rating_el:
                    rating = rating_el.get_text(strip=True)

                # 5. Extract Total Reviews Count (Initial attempt from search page)
                total_reviews = "N/A"
                reviews_el = item.select_one("span.Wphh3N, span._2_R_DZ")
                if reviews_el:
                    reviews_text = reviews_el.get_text(strip=True)
                    match_rev = re.search(r"(\d[\d,]*)\s+(Reviews|Ratings)", reviews_text, re.IGNORECASE)
                    if match_rev:
                        total_reviews = match_rev.group(1)

                print(f"[{processed_count+1}/{max_products}] Found on search page: {title} | Price: {price}")

                # 6. Fetch details and reviews from the product page
                top_reviews = "No reviews found"
                if "flipkart.com" in product_link:
                    print(f"   --> Opening product page for details & reviews...")
                    page_details = self.get_product_details_and_reviews(product_link, count=review_count)
                    
                    # If search page missed rating or reviews (due to grid layout), use the product page data
                    if rating == "N/A":
                        rating = page_details["rating"]
                    if total_reviews == "N/A":
                        total_reviews = page_details["total_reviews"]
                    
                    top_reviews = page_details["reviews"]

                print(f"   --> Finalized: Rating: {rating} | Total Reviews: {total_reviews}")
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