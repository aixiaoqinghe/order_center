import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document 

load_dotenv()

FAQ_PATH = "docs/faq.txt"
CHROMA_DIR = "data/chroma"

def parse_faq(path: str) -> list[Document]:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    # 按【标题】分块，每个标题到下一个标题之间为一块
    blocks = text.split("【")
    docs = []
    for i, block in enumerate(blocks):
        block = block.strip()
        if not block:
            continue
        # 补回【, 保持原文
        content = "【" +  block 
        # 取标题做 metadata (第一条可能是空或前言，取不到就用序号)
        title = block.split("】")[0] if "】" in block else f"faq_{i}"
        docs.append(Document(page_content=content, metadata={"title": title, "source": "faq.txt"}))
    return docs

def main():
    docs = parse_faq(FAQ_PATH)
    print(f"解析到 {len(docs)} 条 FAQ")

    embedding = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-zh-v1.5",
        encode_kwargs={"normalize_embeddings": True},
        model_kwargs={"local_files_only": True},
    )

    # 先清空旧库 (重建)
    if os.path.exists(CHROMA_DIR):
        import shutil
        shutil.rmtree(CHROMA_DIR)

    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embedding,
        persist_directory=CHROMA_DIR,
    )
    print(f"已写入 {CHROMA_DIR}")

if __name__ == "__main__":
    main()