from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import time
import re
import csv
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- Database setup ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///reviews.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product = db.Column(db.String(200), nullable=False)
    reviewer = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.String(10), nullable=False)
    comment = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<Review {self.reviewer} - {self.rating}>"

# --- Scraper setup ---
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0.0.0 Safari/537.36"
    )
}

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        product_name = request.form.get("productname").replace(" ", "+")
        search_url = f"https://www.flipkart.com/search?q={product_name}"

        response = requests.get(search_url, headers=HEADERS)
        soup = BeautifulSoup(response.text, 'html.parser')

        product_containers = soup.find_all("div", class_="lvJbLV col-12-12")[3:]
        product_links = []
        for container in product_containers:
            link_tag = container.find("a")
            if link_tag and link_tag.has_attr("href"):
                full_url = "https://www.flipkart.com" + link_tag["href"]
                product_links.append(full_url)

        reviews = []
        seen_reviewers = set()

        for link in product_links:
            try:
                time.sleep(2)
                product_response = requests.get(link, headers=HEADERS)
                product_soup = BeautifulSoup(product_response.text, 'html.parser')

                review_blocks = product_soup.find_all("div", class_="col x_CUu6")

                for block in review_blocks:
                    rating_tag = block.find("div", class_="MKiFS6 ojKpP6")
                    rating = rating_tag.get_text(strip=True) if rating_tag else None

                    comment_container = block.find("div", class_="G4PxIA")
                    comment_divs = comment_container.find_all("div") if comment_container else []
                    comment = None
                    for div in comment_divs:
                        text = div.get_text(strip=True)
                        if text and "READ MORE" not in text:
                            comment = text.strip()
                            break

                    reviewer_tag = block.find("div", class_=re.compile(r"row f6dnIR"))
                    if not reviewer_tag:
                        fallback = block.find("div", class_="row gHqwa8")
                        if fallback:
                            reviewer_tag = fallback.find("p", class_=re.compile(r"zJ1ZGa ZDi3w2"))
                    reviewer = reviewer_tag.get_text(strip=True) if reviewer_tag else None

                    if not reviewer and not rating and not comment:
                        continue

                    reviewer = reviewer or "Anonymous"
                    rating = rating or "0"
                    comment = comment or "No comment found"

                    if reviewer in seen_reviewers and comment == "No comment found":
                        continue
                    seen_reviewers.add(reviewer)

                    # --- Save to list ---
                    reviews.append({
                        "reviewer": reviewer,
                        "rating": rating,
                        "comment": comment
                    })

                    # --- Save to DB ---
                    new_review = Review(
                        product=product_name.replace("+", " "),
                        reviewer=reviewer,
                        rating=rating,
                        comment=comment
                    )
                    db.session.add(new_review)
                    db.session.commit()

            except requests.exceptions.RequestException as e:
                print(f"❌ Error fetching {link}: {e}")

        # --- Save to CSV ---
        with open("reviews.csv", mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Product", "Reviewer", "Rating", "Comment"])
            for r in reviews:
                writer.writerow([product_name.replace("+", " "), r["reviewer"], r["rating"], r["comment"]])

        return render_template("results.html", reviews=reviews, product=product_name.replace("+", " "))

    return render_template("index.html")

@app.route("/export_csv")
def export_csv():
    reviews = Review.query.all()
    with open("reviews_export.csv", mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Product", "Reviewer", "Rating", "Comment"])
        for r in reviews:
            writer.writerow([r.product, r.reviewer, r.rating, r.comment])
    return "CSV export complete!"

if __name__ == "__main__":

        with app.app_context():
            db.create_all()
        app.run(debug=True)