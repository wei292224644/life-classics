#!/usr/bin/env python3
"""
使用示例脚本
演示如何使用个人知识库系统
"""
import requests
import json

BASE_URL = "http://localhost:8000/api"


def upload_document(file_path: str, description: str = None):
    """上传文档示例"""
    url = f"{BASE_URL}/documents/upload"
    
    with open(file_path, "rb") as f:
        files = {"file": (file_path.split("/")[-1], f, "application/pdf")}
        data = {}
        if description:
            data["description"] = description
        
        response = requests.post(url, files=files, data=data)
        print(f"上传结果: {response.json()}")


def query_knowledge_base(query: str, top_k: int = 5):
    """查询知识库示例"""
    url = f"{BASE_URL}/query/"
    
    payload = {
        "query": query,
        "top_k": top_k
    }
    
    response = requests.post(url, json=payload)
    result = response.json()
    
    print(f"\n查询: {query}")
    print(f"答案: {result['answer']}")
    print(f"\n来源 ({len(result['sources'])} 个):")
    for i, source in enumerate(result['sources'], 1):
        print(f"\n{i}. {source.get('text', '')[:100]}...")
        print(f"   元数据: {source.get('metadata', {})}")


def get_document_info():
    """获取知识库信息示例"""
    url = f"{BASE_URL}/documents/info"
    
    response = requests.get(url)
    print(f"知识库信息: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    print("个人知识库系统使用示例")
    print("=" * 50)
    
    # 1. 获取知识库信息
    print("\n1. 获取知识库信息:")
    get_document_info()
    
    # 2. 上传文档（需要先准备一个PDF文件）
    # print("\n2. 上传文档:")
    # upload_document("example.pdf", "示例文档")
    
    # 3. 查询知识库
    print("\n3. 查询知识库:")
    query_knowledge_base("什么是机器学习？", top_k=3)
    
    print("\n" + "=" * 50)
    print("示例完成！")

