# Runner API: Endpoint для проверки наличия CV

> Версия: 1.0
> Дата: 2026-01-13
> Репозиторий: HHH Runner API
> Связанная задача: [cv-check-before-apply.md](./cv-check-before-apply.md)

---

## Задача

Добавить REST endpoint для проверки наличия загруженного CV пользователя.

**Зачем:** Telegram бот должен проверять наличие CV **до** начала процесса создания отклика, чтобы не тратить время пользователя на ввод URL вакансии.

---

## Endpoint Specification

### GET /api/cv/{user_id}

**Описание:** Проверить наличие загруженного CV для указанного пользователя.

#### Request

```http
GET /api/cv/{user_id} HTTP/1.1
Host: runner-api-host
X-API-Key: <api_key>
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | integer | Yes | Telegram user ID |

**Headers:**
| Header | Type | Required | Description |
|--------|------|----------|-------------|
| `X-API-Key` | string | Yes | API key для авторизации |

#### Response: 200 OK

CV загружено и доступно.

```json
{
  "user_id": 123456,
  "has_cv": true,
  "cv_filename": "resume.pdf",
  "uploaded_at": "2026-01-13T10:30:00Z"
}
```

**Response Schema:**
```typescript
{
  user_id: number;       // Telegram user ID
  has_cv: true;          // Всегда true для 200 OK
  cv_filename: string;   // Имя файла CV
  uploaded_at: string;   // ISO 8601 timestamp
}
```

#### Response: 404 Not Found

CV не найдено для указанного пользователя.

```json
{
  "detail": "CV not found for user 123456"
}
```

#### Response: 401 Unauthorized

Неверный или отсутствующий API ключ.

```json
{
  "detail": "Invalid API key"
}
```

#### Response: 500 Internal Server Error

Ошибка сервера.

```json
{
  "detail": "Internal server error"
}
```

---

## Примеры использования

### cURL

```bash
# Проверка CV пользователя 123456
curl -X GET "https://runner-api/api/cv/123456" \
  -H "X-API-Key: your-api-key"

# Успешный ответ (CV есть)
# HTTP/1.1 200 OK
# {
#   "user_id": 123456,
#   "has_cv": true,
#   "cv_filename": "john_doe_resume.pdf",
#   "uploaded_at": "2026-01-13T10:30:00Z"
# }

# CV не найдено
# HTTP/1.1 404 Not Found
# {
#   "detail": "CV not found for user 123456"
# }
```

### Python (httpx)

```python
import httpx

async def check_cv_exists(user_id: int, api_key: str) -> bool:
    """Проверить наличие CV пользователя."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://runner-api/api/cv/{user_id}",
            headers={"X-API-Key": api_key},
            timeout=10.0
        )
        return response.status_code == 200

# Использование
has_cv = await check_cv_exists(123456, "your-api-key")
if has_cv:
    print("CV загружено")
else:
    print("CV не найдено")
```

---

## Требования к реализации

### Функциональные требования

1. **FR-1:** Endpoint должен проверять наличие CV в storage (filesystem/S3/database)
2. **FR-2:** Возвращать 200 OK только если файл CV существует и доступен
3. **FR-3:** Возвращать 404 Not Found если CV не загружено или было удалено
4. **FR-4:** Авторизация через `X-API-Key` header (как в других endpoint'ах)
5. **FR-5:** Быстрый ответ (<100ms) без загрузки файла

### Нефункциональные требования

1. **NFR-1:** Не читать содержимое файла (проверка только существования)
2. **NFR-2:** Кэширование на уровне storage (если применимо)
3. **NFR-3:** Логирование всех запросов для аудита
4. **NFR-4:** Graceful degradation при ошибках storage

---

## Предлагаемая реализация

### Архитектура

```
GET /api/cv/{user_id}
         │
         ▼
┌────────────────────┐
│   API Route        │
│  cv_routes.py      │
└────────────────────┘
         │
         ▼
┌────────────────────┐
│  CV Storage        │
│  cv_storage.py     │
│  - get_cv_info()   │
└────────────────────┘
         │
         ▼
┌────────────────────┐
│  Storage Backend   │
│  (FS / S3 / DB)    │
└────────────────────┘
```

### Код (псевдокод FastAPI)

```python
# runner/api/routes/cv.py

from fastapi import APIRouter, HTTPException, Depends
from runner.storage import CVStorage
from runner.auth import verify_api_key

router = APIRouter(prefix="/api/cv", tags=["cv"])

@router.get("/{user_id}")
async def check_cv_exists(
    user_id: int,
    api_key: str = Depends(verify_api_key),
):
    """Проверить наличие CV пользователя.

    Args:
        user_id: Telegram user ID
        api_key: API ключ (из X-API-Key header)

    Returns:
        200 OK: CV информация
        404 Not Found: CV не найдено
    """
    cv_storage = CVStorage()

    cv_info = await cv_storage.get_cv_info(user_id)

    if not cv_info:
        raise HTTPException(
            status_code=404,
            detail=f"CV not found for user {user_id}"
        )

    return {
        "user_id": user_id,
        "has_cv": True,
        "cv_filename": cv_info.filename,
        "uploaded_at": cv_info.uploaded_at.isoformat(),
    }
```

### Storage Interface

```python
# runner/storage/cv_storage.py

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

@dataclass
class CVInfo:
    user_id: int
    filename: str
    file_path: Path
    uploaded_at: datetime

class CVStorage:
    """Абстракция для работы с CV файлами."""

    async def get_cv_info(self, user_id: int) -> CVInfo | None:
        """Получить информацию о CV пользователя.

        Args:
            user_id: Telegram user ID

        Returns:
            CVInfo если CV существует, None иначе
        """
        # Проверить существование файла
        cv_path = self._get_cv_path(user_id)

        if not cv_path.exists():
            return None

        # Получить метаданные
        stat = cv_path.stat()

        return CVInfo(
            user_id=user_id,
            filename=cv_path.name,
            file_path=cv_path,
            uploaded_at=datetime.fromtimestamp(stat.st_mtime)
        )

    def _get_cv_path(self, user_id: int) -> Path:
        """Получить путь к CV файлу пользователя."""
        # Реализация зависит от текущей логики хранения
        return Path(f"/storage/cv/{user_id}/resume.pdf")
```

---

## Тесты

### Unit Tests

```python
# runner/tests/unit/test_cv_storage.py

import pytest
from runner.storage import CVStorage, CVInfo

@pytest.mark.asyncio
async def test_get_cv_info_exists():
    """CV существует → возвращается CVInfo."""
    storage = CVStorage()

    # Setup: создать тестовый CV
    user_id = 123456
    await storage.save_test_cv(user_id, b"test content", "resume.pdf")

    # Act
    cv_info = await storage.get_cv_info(user_id)

    # Assert
    assert cv_info is not None
    assert cv_info.user_id == user_id
    assert cv_info.filename == "resume.pdf"

@pytest.mark.asyncio
async def test_get_cv_info_not_exists():
    """CV не существует → возвращается None."""
    storage = CVStorage()

    # Act
    cv_info = await storage.get_cv_info(999999)

    # Assert
    assert cv_info is None
```

### Integration Tests

```python
# runner/tests/integration/test_cv_endpoint.py

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_check_cv_exists_success(client: AsyncClient):
    """200 OK: CV загружено."""
    user_id = 123456

    # Setup: загрузить CV
    await upload_test_cv(client, user_id, "resume.pdf")

    # Act
    response = await client.get(
        f"/api/cv/{user_id}",
        headers={"X-API-Key": "test-key"}
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user_id
    assert data["has_cv"] is True
    assert data["cv_filename"] == "resume.pdf"
    assert "uploaded_at" in data

@pytest.mark.asyncio
async def test_check_cv_not_found(client: AsyncClient):
    """404 Not Found: CV не загружено."""
    response = await client.get(
        "/api/cv/999999",
        headers={"X-API-Key": "test-key"}
    )

    assert response.status_code == 404
    data = response.json()
    assert "CV not found" in data["detail"]

@pytest.mark.asyncio
async def test_check_cv_unauthorized(client: AsyncClient):
    """401 Unauthorized: неверный API ключ."""
    response = await client.get(
        "/api/cv/123456",
        headers={"X-API-Key": "invalid-key"}
    )

    assert response.status_code == 401
```

---

## Интеграция с Telegram Bot

После реализации endpoint'а, Telegram бот будет использовать его так:

```python
# bot/services/runner/client.py

class RunnerClient:
    async def check_cv_exists(self, user_id: int) -> bool:
        """Проверить наличие CV через GET /api/cv/{user_id}."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/api/cv/{user_id}",
                headers={"X-API-Key": self.api_key},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                return response.status == 200
```

---

## Вопросы и ответы

### Q: Зачем отдельный endpoint? Нельзя ли проверять при создании задачи?

**A:** Можно, но это плохой UX. Пользователь тратит время на ввод URL вакансии, а потом узнает что нужно сначала загрузить CV. С отдельным endpoint'ом ошибка показывается сразу.

### Q: Как часто будет вызываться этот endpoint?

**A:** При каждом использовании команды `/apply`. Ожидается ~10-100 запросов в день на начальном этапе.

### Q: Нужно ли кэшировать результат?

**A:** На стороне Runner - желательно (storage-level cache). На стороне бота - нет, так как CV может быть загружено/удалено в любой момент.

### Q: Что если CV было удалено пользователем?

**A:** Endpoint возвращает 404 Not Found. Бот показывает сообщение "Загрузите CV командой /cv".

### Q: Безопасность: можно ли проверить CV другого пользователя?

**A:** Да, если есть валидный API ключ. В текущей версии нет дополнительной авторизации на уровне пользователя. Если нужна - можно добавить в future версиях.

---

## Чеклист для реализации

- [ ] Создать `CVStorage.get_cv_info(user_id)` метод
- [ ] Создать route `GET /api/cv/{user_id}` в FastAPI
- [ ] Добавить авторизацию через `X-API-Key`
- [ ] Написать unit тесты для `CVStorage`
- [ ] Написать integration тесты для endpoint'а
- [ ] Обновить OpenAPI документацию
- [ ] Задеплоить на staging
- [ ] Провести ручное тестирование
- [ ] Задеплоить на production
- [ ] Уведомить команду бота о готовности

---

## Контакты

**Вопросы по спецификации:** [ссылка на issue tracker]

**Интеграция с ботом:** См. [cv-check-before-apply.md](./cv-check-before-apply.md)
