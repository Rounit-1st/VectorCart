from typing import List, Dict
from mcp.server.fastmcp import FastMCP
import ast
from pydantic import BaseModel
from utils import (
    load_database,
    load_models,
    get_query_embedding_image_search,
    get_score,
    get_query_embedding_text_search,
    # extract_inventory_metadata
)

  
class Product(BaseModel):
    id: int
    url:str
    brand: str
    category: str
    sub_category: str
    gender: str
    description: str
    price: float
    size: str
    image_url: str


mcp = FastMCP("shop")

data = load_database("output.json")
clip_model, clip_processor, text_model = load_models()

# metdata = extract_inventory_metadata(data)
# with open('inventory/meta.json', 'w') as file:
#     file.write(json.dumps(metdata, indent=4))


image_embeddings = []
text_embeddings = []

for product in data:
    image_embeddings.append(ast.literal_eval(product.pop('image_embedding')))
    text_embeddings.append(ast.literal_eval(product.pop('text_embedding')))

@mcp.resource(
    uri="file:///inventory/meta.json",
    name="Product Inventory Metadata",
    mime_type="application/json",
    description="Contains available product genders, sub-categories, sizes, etc."
)
def get_inventory() -> dict:
    try:
        with open("inventory/meta.json", mode="r") as f:
            return f.read()
        
    except FileNotFoundError:
        return "Log file not found."

# --- Tool 1: Get Product by ID ---
@mcp.tool(structured_output=True)
def get_product(product_id: int) -> Product:
    """
    Retrieve detailed information for a specific product by its ID.
    """
    for product in data:
        if product['id'] == product_id:
            product_data = product
            break
    if not product_data:
        return None

    return Product(**product_data)

# --- Tool 2: Text-toImage Search ---
@mcp.tool(structured_output=True)
def text_to_image_search(query: str)->List[Product]:
    """
    Search products based on image feature similarity.
    """
    query_embedding = get_query_embedding_image_search(query, clip_model, clip_processor)
    score = get_score(query_embedding, image_embeddings)
    result = [Product(**data[idx]) for idx in score]
    return result


# --- Tool 3: Text-to-Text Search ---
@mcp.tool(structured_output=True)
def text_to_text_search(query: str)->List[Product]:
    """
    Search products based on textual feature similarity.
    """
    query_embedding = get_query_embedding_text_search(query, text_model)
    score = get_score(query_embedding, text_embeddings)
    result = [Product(**data[idx]) for idx in score]
    return result


# --- Tool 4: Filter Products ---
@mcp.tool(structured_output=True)
def filter_products(products: List[dict], filters: Dict) -> List[Product]:
    """
    Filters a list of products based on provided criteria.
    
    Args:
        products (List[dict]): List of product dictionaries.
        filters (Dict): Dictionary with optional keys:
            - brand (str)
            - category (str)
            - sub_category (str)
            - gender (str)
            - price (float)
            - size (str)
    
    Returns:
        List[dict]: Filtered list of product dictionaries.
    """
    def matches(product: dict) -> bool:
        if 'brand' in filters and product['brand'].lower() != filters['brand'].lower():
            return False
        if 'category' in filters and product['category'].lower() != filters['category'].lower():
            return False
        if 'sub_category' in filters and product['sub_category'].lower() != filters['sub_category'].lower():
            return False
        if 'gender' in filters and product['gender'].lower() != filters['gender'].lower():
            return False
        if 'price' in filters and product['price'] > filters['price']:
            return False
        if 'size' in filters:
            available_sizes = [s.strip().lower() for s in product['size'].split(',')]
            if filters['size'].lower() not in available_sizes:
                return False
        return True

    return [product for product in products if matches(product)]
if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='streamable-http')
