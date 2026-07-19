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
        options.add_argument("--headless")  # Run headless for faster review scraping
        driver = uc.Chrome(version_main=147, options=options, use_subprocess=True)

        if not product_url.startswith("http"):
            driver.quit()
            return "No reviews found"

        try:
            driver.get(product_url)
            time.sleep(3)
            try:
                driver.find_element(By.XPATH, "//button[contains(text(), '✕')]").click()
                time.sleep(1)
            except Exception:
                pass

            for _ in range(2):
                ActionChains(driver).send_keys(Keys.END).perform()
                time.sleep(1)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            # Multiple fallback classes for review blocks
            review_blocks = soup.select("div._27M-vq, div.col.EPCmJX, div._6K-7Co, div.ZmyHe8")
            seen = set()
            reviews = []

            for block in review_blocks:
                text = block.get_text(separator=" ", strip=True)
                if text and text not in seen:
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
        driver = uc.Chrome(version_main=147, options=options, use_subprocess=True)
        search_url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"
        driver.get(search_url)
        time.sleep(4)

        try:
            driver.find_element(By.XPATH, "//button[contains(text(), '✕')]").click()
        except Exception:
            pass

        time.sleep(2)
        products = []

        # Find product containers (supports both list and grid layouts)
        items = driver.find_elements(By.CSS_SELECTOR, "div[data-id]")
        print(f"Found {len(items)} raw product containers on the page.")

        items = items[:max_products]
        for idx, item in enumerate(items):
            try:
                # 1. Extract Title (with Fallbacks)
                title = None
                for selector in ["div.KzDlHZ", "a.wjcEIp", "a.IRpwZg", "div._4rR01T", "a.CGtC98"]:
                    try:
                        title = item.find_element(By.CSS_SELECTOR, selector).text.strip()
                        if title: break
                    except:
                        continue
                if not title:
                    title = "Unknown Product Title"

                # 2. Extract Price (with Fallbacks)
                price = "N/A"
                for selector in ["div.Nx9bqj", "div._30jeq3", "div._10g97Y"]:
                    try:
                        price = item.find_element(By.CSS_SELECTOR, selector).text.strip()
                        if price: break
                    except:
                        continue

                # 3. Extract Rating (with Fallbacks)
                rating = "N/A"
                for selector in ["div.XQDdHH", "div._3LWZlK", "span.Y10E2D"]:
                    try:
                        rating = item.find_element(By.CSS_SELECTOR, selector).text.strip()
                        if rating: break
                    except:
                        continue

                # 4. Extract Total Reviews (with Fallbacks)
                total_reviews = "N/A"
                reviews_text = ""
                for selector in ["span.Wphh3N", "span._2_R_DZ"]:
                    try:
                        reviews_text = item.find_element(By.CSS_SELECTOR, selector).text.strip()
                        if reviews_text: break
                    except:
                        continue
                if reviews_text:
                    match = re.search(r"(\d[\d,]*)\s+Reviews", reviews_text)
                    total_reviews = match.group(1) if match else "N/A"

                # 5. Extract Product Link
                product_link = ""
                try:
                    link_el = item.find_element(By.CSS_SELECTOR, "a[href*='/p/']")
                    href = link_el.get_attribute("href")
                    product_link = href if href.startswith("http") else "https://www.flipkart.com" + href
                except:
                    pass

                # Extract Product ID from Link
                product_id = "N/A"
                if product_link:
                    match = re.findall(r"/p/(itm[0-9A-Za-z]+)", product_link)
                    product_id = match[0] if match else "N/A"

                print(f"[{idx+1}/{max_products}] Scraped: {title} | Price: {price} | Rating: {rating}")

                # Fetch reviews if link is valid
                top_reviews = "No reviews found"
                if "flipkart.com" in product_link:
                    top_reviews = self.get_top_reviews(product_link, count=review_count)

                products.append([product_id, title, rating, total_reviews, price, top_reviews])

            except Exception as e:
                print(f"Error processing item index {idx}: {e}")
                continue

        driver.quit()
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