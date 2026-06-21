#!/usr/bin/env python3
"""
测试MongoDB连接问题修复
验证MONGODB_CONNECTION_STRING配置是否正确解决了"未设置:27017"错误
"""

import os
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

def test_mongodb_connection():
    """测试MongoDB连接"""
    print("🔍 测试MongoDB连接修复...")
    
    # 1. 检查环境变量
    print("\n📋 检查环境变量:")
    mongodb_conn_str = os.getenv("MONGODB_CONNECTION_STRING")
    mongodb_host = os.getenv("MONGODB_HOST", "localhost")
    mongodb_port = os.getenv("MONGODB_PORT", "27017")
    mongodb_username = os.getenv("MONGODB_USERNAME", "")
    mongodb_password = os.getenv("MONGODB_PASSWORD", "")
    mongodb_database = os.getenv("MONGODB_DATABASE", "tradingagents")
    
    print(f"  MONGODB_CONNECTION_STRING: {mongodb_conn_str[:50]}..." if mongodb_conn_str and len(mongodb_conn_str) > 50 else f"  MONGODB_CONNECTION_STRING: {mongodb_conn_str}")
    print(f"  MONGODB_HOST: {mongodb_host}")
    print(f"  MONGODB_PORT: {mongodb_port}")
    print(f"  MONGODB_USERNAME: {mongodb_username}")
    print(f"  MONGODB_PASSWORD: {'***' if mongodb_password else '未设置'}")
    print(f"  MONGODB_DATABASE: {mongodb_database}")
    
    # 2. 测试连接字符串连接
    if mongodb_conn_str and mongodb_conn_str != "未设置":
        print(f"\n🔗 使用连接字符串测试连接...")
        try:
            client = MongoClient(mongodb_conn_str, serverSelectionTimeoutMS=5000)
            # 测试连接
            client.admin.command('ping')
            print("  ✅ 连接字符串连接成功!")
            
            # 测试数据库访问
            db = client[mongodb_database]
            collections = db.list_collection_names()
            print(f"  📊 数据库 '{mongodb_database}' 包含 {len(collections)} 个集合")
            
            if 'system_configs' in collections:
                count = db.system_configs.count_documents({})
                print(f"  📄 system_configs 集合包含 {count} 个文档")
            
            client.close()
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"  ❌ 连接字符串连接失败: {e}")
            return False
        except Exception as e:
            print(f"  ❌ 连接字符串连接出现未知错误: {e}")
            return False
    else:
        print(f"\n❌ MONGODB_CONNECTION_STRING 未设置或值为 '未设置'")
        return False

def test_app_config():
    """测试应用配置"""
    print(f"\n🔧 测试应用配置...")
    
    try:
        # 导入应用配置
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from app.core.config import settings
        
        print(f"  MONGO_URI: {settings.MONGO_URI[:50]}..." if len(settings.MONGO_URI) > 50 else f"  MONGO_URI: {settings.MONGO_URI}")
        print(f"  MONGO_DB: {settings.MONGO_DB}")
        
        # 检查URI是否包含"未设置"
        if "未设置" in settings.MONGO_URI:
            print("  ❌ 应用配置中仍包含'未设置'")
            return False
        else:
            print("  ✅ 应用配置正常")
            return True
            
    except Exception as e:
        print(f"  ❌ 应用配置测试失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("🔍 MongoDB连接问题修复验证")
    print("=" * 60)
    
    # 加载.env文件
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ .env 文件加载成功")
    except ImportError:
        print("⚠️ python-dotenv 未安装，跳过 .env 文件加载")
    except Exception as e:
        print(f"⚠️ .env 文件加载失败: {e}")
    
    # 执行测试
    connection_test = test_mongodb_connection()
    config_test = test_app_config()
    
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")
    print(f"  MongoDB连接测试: {'✅ 通过' if connection_test else '❌ 失败'}")
    print(f"  应用配置测试: {'✅ 通过' if config_test else '❌ 失败'}")
    
    if connection_test and config_test:
        print("\n🎉 所有测试通过！MongoDB连接问题已修复。")
        return 0
    else:
        print("\n❌ 部分测试失败，请检查配置。")
        return 1

if __name__ == "__main__":
    sys.exit(main())