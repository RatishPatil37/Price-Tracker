from flask import Flask, request, render_template, jsonify
import os
import logging
import re
from textblob import TextBlob
from apify_helper import fetch_reviews
from collections import Counter
import random

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

def clean_text(text):
    """Remove special characters and extra spaces"""
    return re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z0-9\s]', ' ', text)).strip()

def analyze_review(review_text):
    """Analyze a single review text and return sentiment details"""
    blob = TextBlob(review_text)
    polarity = blob.sentiment.polarity
    subjectivity = blob.sentiment.subjectivity
    
    # Determine sentiment category
    if polarity > 0.2:
        sentiment = "Positive"
    elif polarity < -0.2:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"
        
    # Extract key phrases (simple implementation)
    words = [word.lower() for word in blob.words if len(word) > 3]
    word_counts = Counter(words)
    key_phrases = [word for word, count in word_counts.most_common(5)]
    
    return {
        "polarity": round(polarity, 2),
        "subjectivity": round(subjectivity, 2),
        "sentiment": sentiment,
        "key_phrases": key_phrases
    }

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        url = request.form['product_url']
        logger.info(f"Received URL for analysis: {url}")
        
        if not url:
            return jsonify({"error": "Please enter an Amazon product URL"}), 400
            
        # Check for Amazon URL
        if not 'amazon.' in url.lower():
            return jsonify({"error": "Please enter a valid Amazon product URL"}), 400
        
        # Fetch reviews
        reviews = fetch_reviews(url)
        
        if not reviews:
            logger.warning(f"No reviews found for URL: {url}")
            return jsonify({"error": "No reviews found or error fetching reviews. Try a different product or check console logs."}), 404
        
        logger.info(f"Successfully fetched {len(reviews)} reviews")
        
        results = []
        overall_sentiment = {"Positive": 0, "Neutral": 0, "Negative": 0}
        
        for review in reviews:
            # Skip empty reviews
            if not review or len(review) < 10:
                continue
                
            # Clean the review text
            clean_review = clean_text(review)
            
            # Skip if cleaning removed too much
            if not clean_review or len(clean_review) < 10:
                continue
                
            # Analyze sentiment
            analysis = analyze_review(clean_review)
            
            # Count overall sentiment
            overall_sentiment[analysis["sentiment"]] += 1
            
            results.append({
                "text": clean_review[:300] + "..." if len(clean_review) > 300 else clean_review,
                "sentiment": analysis["sentiment"],
                "polarity": analysis["polarity"],
                "subjectivity": analysis["subjectivity"],
                "key_phrases": analysis["key_phrases"]
            })
        
        # If no valid reviews were processed
        if not results:
            logger.warning("No valid reviews after cleaning and processing")
            return jsonify({"error": "Could not process any valid reviews from this product"}), 404
        
        # Calculate sentiment percentages
        total_reviews = len(results)
        sentiment_stats = {
            "positive_percent": round((overall_sentiment["Positive"] / total_reviews) * 100 if total_reviews else 0),
            "neutral_percent": round((overall_sentiment["Neutral"] / total_reviews) * 100 if total_reviews else 0),
            "negative_percent": round((overall_sentiment["Negative"] / total_reviews) * 100 if total_reviews else 0),
            "total_reviews": total_reviews
        }
        
        logger.info(f"Analysis complete: {sentiment_stats}")
        
        return jsonify({
            "reviews": results, 
            "stats": sentiment_stats
        })
        
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}", exc_info=True)
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8080, use_reloader=False)