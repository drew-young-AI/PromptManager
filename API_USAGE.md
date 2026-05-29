# API 使用說明

本文件說明 DataProvider 專案目前提供的 API、輸入參數、回傳格式與測試範例。

## 基本資訊

- Base URL：`http://aai.cych.org.tw:8080`
- Content-Type：`application/json`
- 目前 API：
  - `POST /getPatientList/`
  - `POST /fetchData/`

## 統一回傳格式

所有 API 皆回傳以下 JSON 結構：

```json
{
  "success": true,
  "message": "Request completed successfully.",
  "data": {},
  "errors": null,
  "traceId": "..."
}
```

欄位說明：

- `success`：是否成功。
- `message`：執行結果訊息。
- `data`：實際資料內容。
- `errors`：錯誤或驗證訊息。
- `traceId`：追蹤識別碼。

## POST /getPatientList/

用途：

- 依病房、住院日期與系統別，整合 `HISDB` 與 `MEDIATORDB` 回傳病人清單。

### Request Body

```json
{
  "station": "6D",
  "admitDateTime": "2026-05-01",
  "systemKind": "01"
}
```

### 參數說明

- `station`：病房代碼，例如 `6D`。
- `admitDateTime`：日期字串，格式固定為 `yyyy-MM-dd`。
- `systemKind`：系統別，例如 `01`。

### systemKind 對應表

- `01`：`AdmissionNote`
- `02`：`ProgressNote`
- `03`：`SpecialNote`
- `04`：`DischargeSummary`

### 回傳資料

`data` 為陣列，每筆資料格式如下：

```json
{
  "mongoDbId": "69f3c41756710a4aaaaaaf3b",
  "patientNo": "00000093",
  "patientName": "陳心寶"
}
```

### curl 範例

```bash
curl -X POST http://aai.cych.org.tw:8080/getPatientList/ \
  -H "Content-Type: application/json" \
  -d '{
    "station": "6D",
    "admitDateTime": "2026-05-01",
    "systemKind": "01"
  }'
```

## POST /fetchData/

用途：

- 依 `systemKind` 對應 MongoDB collection，並用 `fetchId` 查詢 `_id` 符合的文件集合。

### Request Body

```json
{
  "systemKind": "01",
  "fetchId": [
    "69f3c41756710a4aaaaaaf3b",
    "69f3e0c756710a4aaaaaaf3d",
    "69f3bbf856710a4aaaaaaf3a"
  ]
}
```

### 參數說明

- `systemKind`：決定 MongoDB collection 的代碼。
- `fetchId`：MongoDB `_id` 字串陣列，每個值都必須是有效的 `ObjectId`。

### systemKind 對應表

- `01`：`AdmissionNote`
- `02`：`ProgressNote`
- `03`：`SpecialNote`
- `04`：`DischargeSummary`

### 回傳資料

`data` 為 MongoDB 文件陣列，文件內容會依 collection 實際欄位而不同。

### curl 範例

```bash
curl -X POST http://aai.cych.org.tw:8080/fetchData/ \
  -H "Content-Type: application/json" \
  -d '{
    "systemKind": "01",
    "fetchId": [
      "69f3c41756710a4aaaaaaf3b",
      "69f3e0c756710a4aaaaaaf3d",
      "69f3bbf856710a4aaaaaaf3a"
    ]
  }'
```

## 串接測試範例

可先呼叫 `/getPatientList/` 取得 `mongoDbId`，再將其作為 `/fetchData/` 的 `fetchId`。

## 常見錯誤

### 400 Validation failed.

可能原因：

- 缺少必要欄位。
- `systemKind` 不在支援範圍內。
- `fetchId` 中包含不是有效 `ObjectId` 的字串。

### 500 Request processing failed.

可能原因：

- SQL Server 連線失敗。
- MongoDB 連線失敗。
- 查詢資料來源超時或資料格式異常。

## 建議測試順序

1. 先測 `POST /getPatientList/`
2. 再取出回傳的 `mongoDbId`
3. 用這些 `mongoDbId` 測 `POST /fetchData/`