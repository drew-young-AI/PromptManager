"""
Django 管理指令 - 測試遠端 API 連接
"""

import json
import logging

from django.core.management.base import BaseCommand, CommandError

from prompts.remote_api_client import RemoteAPIClient, RemoteAPIError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '測試遠端 aai.cych.org.tw API 連接'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--check-health',
            action='store_true',
            help='只檢查 API 服務可用性',
        )
        parser.add_argument(
            '--station',
            type=str,
            default='6D',
            help='病房代碼，預設為 "6D"',
        )
        parser.add_argument(
            '--date',
            type=str,
            default='2026-05-01',
            help='入院日期，格式 yyyy-MM-dd，預設為 "2026-05-01"',
        )
        parser.add_argument(
            '--system-kind',
            type=str,
            default='01',
            help='系統別，預設為 "01" (AdmissionNote)',
        )
    
    def handle(self, *args, **options):
        client = RemoteAPIClient()
        
        if options['check_health']:
            self.stdout.write('🔍 檢查 API 健康狀態...')
            if client.health_check():
                self.stdout.write(self.style.SUCCESS('✓ API 服務可用'))
            else:
                self.stdout.write(self.style.ERROR('✗ API 服務不可用'))
            return
        
        station = options['station']
        date = options['date']
        system_kind = options['system_kind']
        
        self.stdout.write(f'📋 取得病人清單: station={station}, date={date}, system={system_kind}')
        
        try:
            patients = client.get_patient_list(station, date, system_kind)
            self.stdout.write(self.style.SUCCESS(f'✓ 成功取得 {len(patients)} 筆病人資料'))
            
            for idx, patient in enumerate(patients[:5], 1):
                self.stdout.write(f'  {idx}. {patient.get("patientName")} (ID: {patient.get("mongoDbId")})')
            
            if len(patients) > 5:
                self.stdout.write(f'  ... 及 {len(patients) - 5} 筆其他資料')
                
                # 試著取得第一個病人的詳細資料
                mongo_id = patients[0].get('mongoDbId')
                if mongo_id:
                    self.stdout.write(f'\n📄 試著取得第一個病人的詳細資料 (ID: {mongo_id})...')
                    data = client.fetch_data(system_kind, [mongo_id])
                    self.stdout.write(self.style.SUCCESS(f'✓ 成功取得 {len(data)} 筆詳細資料'))
                    if data:
                        self.stdout.write(f'  範例欄位: {list(data[0].keys())[:5]}')
        
        except RemoteAPIError as exc:
            raise CommandError(f'API 呼叫失敗: {exc}')
