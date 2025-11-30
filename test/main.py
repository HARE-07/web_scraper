import requests
from bs4 import BeautifulSoup
import time
import re

# Set headers to mimic a real browser
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0.0.0 Safari/537.36"
    )
}

# Get product name from user
product_name = input("Enter the product name: ").replace(" ", "+")
search_url = f"https://www.flipkart.com/search?q={product_name}"

# Fetch search results page
response = requests.get(search_url, headers=HEADERS)
soup = BeautifulSoup(response.text, 'html.parser')

# Extract product containers (skip first 3 irrelevant ones)
product_containers = soup.find_all("div", class_="lvJbLV col-12-12")[3:]

# Extract product links
product_links = []
for container in product_containers:
    link_tag = container.find("a")
    if link_tag and link_tag.has_attr("href"):
        full_url = "https://www.flipkart.com" + link_tag["href"]
        product_links.append(full_url)

print("\n🔗 Found Product Links:")
for link in product_links:
    print(link)

# Visit each product page and extract reviews
print("\n📝 Extracting reviews...\n")
seen_reviewers = set()

for link in product_links:
    try:
        time.sleep(2)
        product_response = requests.get(link, headers=HEADERS)
        product_soup = BeautifulSoup(product_response.text, 'html.parser')

        review_blocks = product_soup.find_all("div", class_="col x_CUu6")

        for block in review_blocks:
            # ⭐ Extract rating
            rating_tag = block.find("div", class_="MKiFS6 ojKpP6") or block.find("div", class_="MKiFS6 ojKpP6")
            rating = rating_tag.get_text(strip=True) if rating_tag else None

            # 💬 Extract comment
            comment_container = block.find("div", class_="G4PxIA") or block.find("div", class_="G4PxIA")
            comment_divs = comment_container.find_all("div") if comment_container else []
            comment = None
            for div in comment_divs:
                text = div.get_text(strip=True)
                if text and "READ MORE" not in text:
                    comment = text.replace("READ MORE", "").strip()
                    break

            # 👤 Extract reviewer name
            reviewer_tag = block.find("div", class_=re.compile(r"row f6dnIR"))
            if not reviewer_tag:
                fallback = block.find("div", class_="row gHqwa8")
                if fallback:
                    reviewer_tag = fallback.find("p", class_=re.compile(r"zJ1ZGa ZDi3w2"))
            reviewer = reviewer_tag.get_text(strip=True) if reviewer_tag else None

            # Skip if all are missing
            if not reviewer and not rating and not comment:
                continue

            # Fallbacks
            reviewer = reviewer or "Anonymous"
            rating = rating or "No rating"
            comment = comment or "No comment found"

            # Avoid duplicate reviewer entries
            if reviewer in seen_reviewers and comment == "No comment found":
                continue
            seen_reviewers.add(reviewer)

            # 🖨️ Print review
            print(f"👤 Reviewer: {reviewer} ")
            if rating == "5":
                print(f"⭐ Rating: {rating} ⭐⭐⭐⭐⭐")
            elif rating =="4":
                print(f"⭐ Rating: {rating} ⭐⭐⭐⭐")
            elif rating == "3":
                print(f"⭐ Rating: {rating} ⭐⭐⭐")
            elif rating =="2":
                print(f"⭐ Rating: {rating} ⭐⭐")
            else:
                print(f"⭐ Rating:⭐ ")
            print(f"💬 Comment: {comment}")
            print("-" * 60)

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching {link}: {e}")