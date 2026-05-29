"""
遠端 API 客戶端 - 用於串接 aai.cych.org.tw 的醫療資料 API
"""

import json
import logging
import os
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


class RemoteAPIError(Exception):
    """遠端 API 呼叫失敗"""
    pass


class RemoteAPIClient:
    """aai.cych.org.tw API 客戶端"""
    
    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
        timeout: int = None,
    ):
        self.base_url = (base_url or os.environ.get('REMOTE_API_BASE_URL', 'http://aai.cych.org.tw:8080')).rstrip('/')
        self.api_key = api_key or os.environ.get('REMOTE_API_KEY', '')
        self.timeout = timeout or int(os.environ.get('REMOTE_API_TIMEOUT', '30'))
        
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
        if self.api_key:
            self.session.headers.update({'Authorization': f'Bearer {self.api_key}'})
    
    def get_patient_list(
        self,
        station: str,
        admit_date: str,
        system_kind: str,
    ) -> list[dict[str, Any]]:
        """
        取得病人清單
        
        Args:
            station: 病房代碼，如 '6D'
            admit_date: 入院日期，格式 'yyyy-MM-dd'
            system_kind: 系統別 ('01'=AdmissionNote, '02'=ProgressNote, '03'=SpecialNote, '04'=DischargeSummary)
        
        Returns:
            病人清單 [{'mongoDbId': '...', 'patientNo': '...', 'patientName': '...'}, ...]
        
        Raises:
            RemoteAPIError: API 呼叫失敗
        """
        endpoint = f'{self.base_url}/getPatientList/'
        payload = {
            'station': station,
            'admitDateTime': admit_date,
            'systemKind': system_kind,
        }
        
        try:
            logger.info(f'Calling {endpoint} with station={station}, date={admit_date}, system={system_kind}')
            response = self.session.post(endpoint, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            self._check_api_response(result)
            
            data = result.get('data', [])
            logger.info(f'Retrieved {len(data)} patients')
            return data
        
        except requests.RequestException as exc:
            msg = f'Failed to call /getPatientList/: {exc}'
            logger.error(msg)
            raise RemoteAPIError(msg) from exc
    
    def fetch_data(
        self,
        system_kind: str,
        fetch_ids: list[str],
    ) -> list[dict[str, Any]]:
        """
        取得醫療資料文件
        
        Args:
            system_kind: 系統別 ('01'=AdmissionNote, '02'=ProgressNote, '03'=SpecialNote, '04'=DischargeSummary)
            fetch_ids: MongoDB _id 字串陣列
        
        Returns:
            MongoDB 文件清單
        
        Raises:
            RemoteAPIError: API 呼叫失敗
        """
        endpoint = f'{self.base_url}/fetchData/'
        payload = {
            'systemKind': system_kind,
            'fetchId': fetch_ids,
        }
        
        try:
            logger.info(f'Calling {endpoint} with system={system_kind}, {len(fetch_ids)} IDs')
            response = self.session.post(endpoint, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            self._check_api_response(result)
            
            data = result.get('data', [])
            logger.info(f'Retrieved {len(data)} documents')
            return data
        
        except requests.RequestException as exc:
            msg = f'Failed to call /fetchData/: {exc}'
            logger.error(msg)
            raise RemoteAPIError(msg) from exc
    
    @staticmethod
    def _check_api_response(response: dict[str, Any]) -> None:
        """檢查 API 回應是否成功"""
        if not response.get('success'):
            message = response.get('message', 'Unknown error')
            errors = response.get('errors')
            trace_id = response.get('traceId', 'N/A')
            
            error_detail = f'{message} (TraceId: {trace_id})'
            if errors:
                error_detail += f' | Errors: {errors}'
            
            raise RemoteAPIError(error_detail)
    
    def health_check(self) -> bool:
        """檢查 API 服務是否可用"""
        try:
            # 試著呼叫一個需要最少參數的端點
            response = self.session.get(
                f'{self.base_url}/health',
                timeout=5,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False


def get_remote_api_client(
    base_url: str = None,
    api_key: str = None,
    timeout: int = None,
) -> RemoteAPIClient:
    """建立或取得遠端 API 客戶端實例"""
    return RemoteAPIClient(base_url=base_url, api_key=api_key, timeout=timeout)
