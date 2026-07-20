from utils.file_scanner import scan_folder
from loaders.loader_manager import load_document


def main():

    print("=" * 60)
    print("LocalDocs AI Assistant")
    print("=" * 60)

    # Scan the data folder
    files = scan_folder("data")

    if not files:
        print("No supported documents found.")
        return

    documents = []

    # Load each document safely
    for file in files:
        try:
            document = load_document(file)

            if document:
                documents.append(document)
                print(f"✅ Loaded: {file.name}")

        except Exception as e:
            print(f"❌ Failed to load {file.name}")
            print(f"   Error: {e}\n")

    # Summary
    print("\n" + "=" * 60)
    print(f"Successfully Loaded {len(documents)} Documents")
    print("=" * 60)

    # Display a preview of each document
    for document in documents:

        print("\n" + "-" * 60)
        print(f"📄 File: {document['filename']}")
        print("-" * 60)

        preview = document["content"][:300]

        if preview.strip():
            print(preview)
        else:
            print("No readable text found.")

        print()


if __name__ == "__main__":
    main()