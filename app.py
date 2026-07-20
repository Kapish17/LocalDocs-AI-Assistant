from utils.file_scanner import scan_folder
from loaders.loader_manager import load_document
from rag.chunking import split_documents


def main():

    print("=" * 60)
    print("LocalDocs AI Assistant")
    print("=" * 60)

    files = scan_folder("data")

    if not files:
        print("No supported documents found.")
        return

    documents = []

    for file in files:
        try:
            document = load_document(file)

            if document:
                documents.append(document)
                print(f"✅ Loaded {file.name}")

        except Exception as e:
            print(f"❌ Failed to load {file.name}")
            print(f"Error: {e}")

    print("\nSplitting documents...\n")

    # Debug loaded documents
    print("=" * 60)
    print("DOCUMENT DEBUG")
    print("=" * 60)

    print("Total Documents:", len(documents))

    if documents:
        print("First document type:", type(documents[0]))
        print("First document:")
        print(documents[0])

    chunks = split_documents(documents)

    print("\n" + "=" * 60)
    print("CHUNK DEBUG")
    print("=" * 60)

    print("Total Chunks:", len(chunks))

    if chunks:
        print("First chunk type:", type(chunks[0]))
        print("First chunk:")
        print(chunks[0])

    # Stop here for debugging
    return


if __name__ == "__main__":
    main()