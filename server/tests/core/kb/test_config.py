from api.config import Settings


def test_embedding_config_defaults():
    s = Settings()
    assert s.EMBEDDING_MODEL == "qwen3-embedding:4b"
    assert s.EMBEDDING_LLM_PROVIDER == "ollama"


def test_neo4j_config_defaults():
    s = Settings()
    assert s.NEO4J_URI == "bolt://localhost:7687"
    assert s.NEO4J_USERNAME == "neo4j"
    assert s.NEO4J_PASSWORD == "password"
