#!/usr/bin/env python3
"""
验证数据库配置修复脚本
检查 .env 文件配置和实际数据库连接
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

def main():
    print("🔍 验证数据库配置修复...")
    
    # 加载 .env 文件
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print(f"❌ .env 文件不存在: {env_path}")
        return False
    
    load_dotenv(env_path)
    print(f"✅ 成功加载 .env 文件: {env_path}")
    
    # 检查环境变量
    mongodb_database = os.getenv("MONGODB_DATABASE")
    mongodb_connection_string = os.getenv("MONGODB_CONNECTION_STRING")
    
    print(f"📊 MONGODB_DATABASE: {mongodb_database}")
    print(f"🔗 MONGODB_CONNECTION_STRING: {mongodb_connection_string}")
    
    if mongodb_database != "tradingagents":
        print(f"❌ 数据库名称错误，期望: tradingagents, 实际: {mongodb_database}")
        return False
    
    if not mongodb_connection_string or "tradingagents" not in mongodb_connection_string:
        print(f"❌ 连接字符串错误或不包含正确的数据库名称")
        return False
    
    # 测试数据库连接
    try:
        print("🔄 测试 MongoDB 连接...")
        client = MongoClient(mongodb_connection_string, serverSelectionTimeoutMS=5000)
        
        # 测试连接
        client.admin.command('ping')
        print("✅ MongoDB 连接成功")
        
        # 检查数据库
        db = client[mongodb_database]
        collections = db.list_collection_names()
        print(f"📚 数据库 '{mongodb_database}' 包含 {len(collections)} 个集合")
        
        if collections:
            print("📋 集合列表:")
            for collection in collections:
                count = db[collection].count_documents({})
                print(f"  - {collection}: {count} 条记录")
        
        client.close()
        
        print("✅ 数据库配置修复验证成功！")
        return True
        
    except Exception as e:
        print(f"❌ MongoDB 连接失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)