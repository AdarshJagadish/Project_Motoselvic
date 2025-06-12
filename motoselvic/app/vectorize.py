import pandas as pd
from sentence_transformers import SentenceTransformer
import numpy as np

# Initialize Sentence-BERT model
model = SentenceTransformer('all-MiniLM-L6-v2')

# ----------------- Review Processing -----------------
def process_reviews(reviews):
    """Vectorize a list or comma-separated string of reviews and return the average vector."""
    if reviews:
        review_list = reviews.split(',') if isinstance(reviews, str) else reviews
        review_vectors = model.encode(review_list)
        return np.mean(review_vectors, axis=0)
    return None

# ----------------- Search Processing -----------------
def process_search(search):
    """Vectorize a user search query (string with commas) and return average embedding."""
    if search:
        search_list = search.split(',')  # Support multiple terms
        search_vectors = model.encode(search_list)
        return np.mean(search_vectors, axis=0)
    return None

# ----------------- Product Vector Creation -----------------
def combine_product_with_reviews(product_data):
    """Combine product metadata and aggregated review embeddings."""
    combined_text = (
        f"Product Name: {product_data['name']}, "
        f"Rating: {product_data['rating']}, "
        f"Manufacturer: {product_data['manufacturer']}, "
        f"Description: {product_data['description']}, "
        f"Category: {product_data['category']}, "
        f"Subcategory: {product_data['subcategory']}"
    )

    product_vector = model.encode(combined_text)
    review_vector = process_reviews(product_data['reviews'])

    return product_vector + review_vector if review_vector is not None else product_vector

def vectorize_product_with_reviews(df):
    """Vectorize all products in a DataFrame by combining metadata and reviews."""
    return [combine_product_with_reviews(row) for _, row in df.iterrows()]

# ----------------- User + Search Vector Creation -----------------
def combine_user_with_search(user_data):
    """Combine user metadata and search queries into a single vector."""
    combined_text = f"user_id: {user_data['user_id']}, product: {user_data['product']}"
    user_vector = model.encode(combined_text)
    search_vector = process_search(user_data['search'])

    return user_vector + search_vector if search_vector is not None else user_vector

def vectorize_user_with_search(df):
    """Vectorize all user entries with search data."""
    return [combine_user_with_search(row) for _, row in df.iterrows()]
