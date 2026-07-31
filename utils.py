import torch
from typing import List, Tuple
from transformers import CLIPProcessor, CLIPModel
from sentence_transformers import SentenceTransformer
import numpy as np
import json

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_database(filepath:str):
    try:
        with open(filepath, 'r') as file:
            data = json.load(file)
        return data
    except Exception as e:
        raise RuntimeError(f"Error loading Database from given path: {e}")
    

def load_models() -> Tuple[CLIPModel, CLIPProcessor]:
    try:
        clip_model = CLIPModel.from_pretrained("patrickjohncyh/fashion-clip", cache_dir='hf_models').to(device)
        clip_processor = CLIPProcessor.from_pretrained("patrickjohncyh/fashion-clip", cache_dir='hf_models', use_fast=False)
        text_model = SentenceTransformer(
            'sentence-transformers/multi-qa-MiniLM-L6-cos-v1', 
            cache_folder='hf_models', device=device
        )
        return clip_model, clip_processor, text_model
    except Exception as e:
        raise RuntimeError(f"Error loading HF(Clip) models: {e}")

def get_query_embedding_image_search(query: str, model: CLIPModel, processor: CLIPProcessor) -> List[float]:
    with torch.no_grad():
        inputs = processor(text=query, return_tensors="pt").to(device)
        text_features = model.get_text_features(**inputs)
        text_features = torch.nn.functional.normalize(text_features, p=2, dim=1).cpu().numpy()[0]

    return text_features

def get_score(query_embedding:List, data_embeddings:List, k:int=10)->List[int]:
    similarities = np.dot(data_embeddings, query_embedding)
    sorted_indices = np.argsort(similarities)[::-1]
    return sorted_indices[:k]

def get_query_embedding_text_search(query: str, text_model:SentenceTransformer)->List[float]:
    query_emb = text_model.encode(query, normalize_embeddings=True)
    return query_emb

def extract_inventory_metadata(products: List[dict]) -> dict:
    return {
        "genders": sorted(set(p["gender"] for p in products)),
        "sub_categories": sorted(set(p["sub_category"] for p in products)),
        "brands": sorted(set(p["brand"] for p in products)),
        "categories": sorted(set(p["category"] for p in products)),
        "sizes": sorted(set(s.strip() for p in products for s in p["size"].split(",")))
    }