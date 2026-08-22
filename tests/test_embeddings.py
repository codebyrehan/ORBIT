from orbit.core.embeddings import cosine_similarity, embed


def test_embedding_is_deterministic_and_normalized():
    vector = embed("ORBIT semantic retrieval", 384)
    assert len(vector) == 384
    assert vector == embed("ORBIT semantic retrieval", 384)
    assert abs(cosine_similarity(vector, vector) - 1.0) < 1e-6


def test_related_text_scores_above_unrelated_text():
    query = embed("local model inference")
    related = embed("local model inference runtime")
    unrelated = embed("banana orchard weather")
    assert cosine_similarity(query, related) > cosine_similarity(query, unrelated)
