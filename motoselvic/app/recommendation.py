import numpy as np
import json

def get_recommended_products(user_vector_json, products, top_n=5):
    if not user_vector_json:
        return []

    try:
        user_vec = np.array(json.loads(user_vector_json))
    except (json.JSONDecodeError, TypeError):
        return []

    if user_vec.size == 0 or np.linalg.norm(user_vec) == 0:
        return []

    # Filter products that have valid vector_data
    products_with_vectors = []
    for p in products:
        try:
            vec = np.array(json.loads(p.vector_data))
            if vec.size > 0:
                products_with_vectors.append((p, vec))
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue

    def cosine_similarity(a, b):
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0
        return np.dot(a, b) / (norm_a * norm_b)

    scored_products = []
    for product, vec in products_with_vectors:
        score = cosine_similarity(user_vec, vec)
        scored_products.append((score, product))

    scored_products.sort(key=lambda x: x[0], reverse=True)

    recommended = [prod for score, prod in scored_products if score > 0][:top_n]
    return recommended
