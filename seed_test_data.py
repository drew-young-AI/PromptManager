from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, UTC

def seed_data():
    client = MongoClient('mongodb://192.168.137.232:27017/')
    db = client['prompt_manager']
    collection = db['prompt_hierarchy']
    
    # 清空現有資料
    collection.delete_many({})
    
    # 建立測試資料
    test_doc = {
        "type": "clinical",
        "categories": [
            {
                "name": "triage",
                "prompts": [
                    {
                        "name": "adult-intake",
                        "channels": {
                            "production": 1,
                            "beta": 1
                        },
                        "versions": [
                            {
                                "version": 1,
                                "data": {
                                    "role_character": "You are a professional triage nurse.",
                                    "content": "Analyze the following patient symptoms: {symptoms}",
                                    "notes": "Initial test version"
                                },
                                "created_at": datetime.now(UTC).isoformat(),
                                "created_by": "system-seed"
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    collection.insert_one(test_doc)
    print("✅ 測試資料已成功植入 MongoDB")

if __name__ == "__main__":
    try:
        seed_data()
    except Exception as e:
        print(f"❌ 植入失敗: {e}")
