from utils.file_scanner import scan_folder
from loaders.loader_manager import load_document
from rag.chunking import split_documents
from rag.vector_store import create_vector_store


def build_vector_store():
    """
    Scans the data folder, loads documents,
    splits them into chunks, and creates
    a fresh FAISS vector database.
    """

    files = scan_folder("data")

    if not files:
        print("❌ No supported documents found.")
        return

    documents = []

    print("\nLoading documents...\n")

    for file in files:
        try:
            document = load_document(file)

            if document:
                documents.append(document)
                print(f"✅ Loaded: {file.name}")

        except Exception as e:
            print(f"❌ Failed: {file.name}")
            print(e)

    print("\nSplitting documents...\n")

    chunks = split_documents(documents)

    print(f"📄 Documents : {len(documents)}")
    print(f"🧩 Chunks    : {len(chunks)}")

    create_vector_store(chunks)