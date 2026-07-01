from pathlib import Path
from urllib.parse import urlparse

import lancedb
import pyarrow as pa

from app.core.config import settings


_db_connection = None


def _resolve_vector_db_uri(vector_db_url: str) -> str:
    parsed = urlparse(vector_db_url)
    if parsed.scheme == "file":
        return parsed.path
    if parsed.scheme:
        return vector_db_url
    return str(Path(vector_db_url).expanduser())


def get_vector_db():
    global _db_connection

    if _db_connection is None:
        _db_connection = lancedb.connect(_resolve_vector_db_uri(settings.VECTOR_DB_URL))

    return _db_connection


def _collection_schema(vector_dim: int) -> pa.Schema:
    return pa.schema(
        [
            pa.field("id", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), vector_dim)),
            pa.field("metadata", pa.string()),
        ]
    )


def ensure_collection(collection_name: str, vector_dim: int):
    db = get_vector_db()

    if collection_name in db.table_names():
        return db.open_table(collection_name)

    table = db.create_table(
        collection_name,
        schema=_collection_schema(vector_dim),
        mode="create",
    )
    return table


def upsert_vector(collection_name: str, id: str, vector: list[float], metadata: str):
    """Insert or overwrite a vector in the specified collection."""
    table = ensure_collection(collection_name, len(vector))
    try:
        # Delete existing entries with this ID if they exist to prevent duplicates
        table.delete(f"id = '{id}'")
    except Exception:
        pass
    table.add([{"id": id, "vector": vector, "metadata": metadata}])


def search_similarity(collection_name: str, query_vector: list[float], limit: int = 5) -> list[dict]:
    """Perform a similarity search on the vector collection."""
    db = get_vector_db()
    if collection_name not in db.table_names():
        return []
    table = db.open_table(collection_name)
    return table.search(query_vector).limit(limit).to_list()


def delete_vector(collection_name: str, id: str):
    """Delete a specific vector from the collection by ID."""
    db = get_vector_db()
    if collection_name in db.table_names():
        table = db.open_table(collection_name)
        try:
            table.delete(f"id = '{id}'")
        except Exception:
            pass


def init_vector_db() -> bool:
    get_vector_db()
    return True
