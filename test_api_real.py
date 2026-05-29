#!/usr/bin/env python
"""
實際測試遠端 API - 顯示真實 JSON 資料傳輸
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from prompts.remote_api_client import RemoteAPIClient, RemoteAPIError


def test_get_patient_list():
    """測試取得病人清單"""
    print("\n" + "="*70)
    print("TEST 1: Get Patient List")
    print("="*70)
    
    client = RemoteAPIClient()
    
    # 請求參數
    print("\n[REQUEST]")
    request_payload = {
        "station": "6D",
        "admitDateTime": "2026-05-01",
        "systemKind": "01"
    }
    print(f"POST http://aai.cych.org.tw:8080/getPatientList/")
    print(f"Body: {json.dumps(request_payload, indent=2, ensure_ascii=False)}")
    
    try:
        patients = client.get_patient_list("6D", "2026-05-01", "01")
        
        print("\n[RESPONSE - Raw Data]")
        print(f"Status: 200 OK")
        print(f"Count: {len(patients)} records")
        
        print("\n[RESPONSE - JSON]")
        print(json.dumps(patients, indent=2, ensure_ascii=False))
        
        return patients
    
    except RemoteAPIError as e:
        print(f"\n[ERROR]")
        print(f"Status: FAILED")
        print(f"Message: {e}")
        return None


def test_fetch_data(mongo_ids):
    """測試取得詳細資料"""
    if not mongo_ids:
        print("\nNo patient IDs to fetch")
        return
    
    print("\n" + "="*70)
    print("TEST 2: Fetch Medical Data")
    print("="*70)
    
    client = RemoteAPIClient()
    
    # 只取前 2 個
    fetch_ids = mongo_ids[:2]
    
    print("\n[REQUEST]")
    request_payload = {
        "systemKind": "01",
        "fetchId": fetch_ids
    }
    print(f"POST http://aai.cych.org.tw:8080/fetchData/")
    print(f"Body: {json.dumps(request_payload, indent=2, ensure_ascii=False)}")
    
    try:
        data = client.fetch_data("01", fetch_ids)
        
        print("\n[RESPONSE - Raw Data]")
        print(f"Status: 200 OK")
        print(f"Count: {len(data)} records")
        
        print("\n[RESPONSE - Sample JSON (first record)]")
        if data:
            print(json.dumps(data[0], indent=2, ensure_ascii=False)[:1000] + "...")
        
        print("\n[ALL RESPONSE - Complete JSON]")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
    except RemoteAPIError as e:
        print(f"\n[ERROR]")
        print(f"Status: FAILED")
        print(f"Message: {e}")


def main():
    print("\n" + "#"*70)
    print("# REAL API TEST - NO MOCK, REAL DATA TRANSFER")
    print("#"*70)
    
    # Test 1: Get patient list
    patients = test_get_patient_list()
    
    # Test 2: Fetch detailed data
    if patients:
        mongo_ids = [p['mongoDbId'] for p in patients]
        test_fetch_data(mongo_ids)
    
    print("\n" + "#"*70)
    print("# TEST COMPLETE")
    print("#"*70 + "\n")


if __name__ == '__main__':
    main()
