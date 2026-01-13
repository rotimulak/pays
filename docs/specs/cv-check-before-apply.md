# Спецификация: Проверка наличия CV перед откликом

> Версия: 1.0
> Статус: Draft
> Дата: 2026-01-13

---

## 1. Обзор

Добавление проверки наличия загруженного CV **до** начала процесса создания отклика на вакансию.

### Текущая проблема

Сейчас при использовании команды `/apply`:
1. Пользователь вводит команду `/apply`
2. Бот показывает форму для ввода URL вакансии
3. Пользователь вводит URL
4. Только **после** ввода URL бот проверяет наличие CV
5. Если CV нет → показывается ошибка `ERROR_NO_CV`

**Это плохой UX:** пользователь тратит время на ввод URL, а потом узнает что нужно сначала загрузить CV.

### Целевое поведение

При использовании команды `/apply`:
1. Пользователь вводит команду `/apply`
2. Бот **сразу** проверяет наличие CV
3. Если CV нет → показывается `ERROR_NO_CV` без запроса URL
4. Если CV есть → показывается форма для ввода URL вакансии

---

## 2. Архитектура

### 2.1 Изменения в Runner API

Нужно добавить endpoint для проверки наличия CV пользователя.

```
┌─────────────────────────────────────────────┐
│         Telegram Bot (pays)                 │
│  /apply command handler                     │
└─────────────────────────────────────────────┘
                    │
                    │ 1. GET /api/cv/{user_id}
                    ▼
┌─────────────────────────────────────────────┐
│         HHH Runner API                      │
│  - GET  /api/cv/{user_id}                  │
│    → 200 OK: CV exists                     │
│    → 404 Not Found: CV not uploaded        │
└─────────────────────────────────────────────┘
```

### 2.2 Изменения в Telegram Bot

```python
# backend/src/bot/handlers/apply.py

async def _start_apply_flow():
    # ... существующие проверки ...

    # НОВАЯ ПРОВЕРКА: наличие CV
    apply_service = _get_apply_service(session, message.bot)
    has_cv = await apply_service.check_cv_exists(user_id)

    if not has_cv:
        await message.answer(ERROR_NO_CV)
        return

    # Показываем форму для ввода URL
    await state.set_state(ApplyStates.waiting_for_url)
    await message.answer(PROMPT.format(cost=APPLY_COST))
```

---

## 3. Runner API: Новый endpoint

### 3.1 Endpoint: GET /api/cv/{user_id}

**Цель:** Проверить наличие загруженного CV для пользователя.

#### Request

```http
GET /api/cv/{user_id} HTTP/1.1
Host: runner-api-host
X-API-Key: <api_key>
```

**Path Parameters:**
- `user_id` (int, required) - Telegram user ID

**Headers:**
- `X-API-Key` (string, required) - API ключ для авторизации

#### Response: 200 OK (CV exists)

```json
{
  "user_id": 123456,
  "has_cv": true,
  "cv_filename": "resume.pdf",
  "uploaded_at": "2026-01-13T10:30:00Z"
}
```

#### Response: 404 Not Found (CV not uploaded)

```json
{
  "detail": "CV not found for user 123456"
}
```

#### Response: 401 Unauthorized (invalid API key)

```json
{
  "detail": "Invalid API key"
}
```

### 3.2 Реализация в Runner API

#### Псевдокод

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
    """Проверить наличие CV пользователя."""
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

#### Storage Interface

```python
# runner/storage/cv_storage.py

from dataclasses import dataclass
from datetime import datetime

@dataclass
class CVInfo:
    user_id: int
    filename: str
    file_path: str
    uploaded_at: datetime

class CVStorage:
    """Абстракция для хранения CV."""

    async def get_cv_info(self, user_id: int) -> CVInfo | None:
        """Получить информацию о CV пользователя."""
        # Реализация зависит от текущего storage в Runner
        # Варианты: filesystem, S3, database
        pass

    async def save_cv(self, user_id: int, file_data: bytes, filename: str) -> CVInfo:
        """Сохранить CV пользователя."""
        pass

    async def delete_cv(self, user_id: int) -> bool:
        """Удалить CV пользователя."""
        pass
```

---

## 4. Telegram Bot: Изменения

### 4.1 RunnerClient: Новый метод

```python
# backend/src/services/runner/client.py

class BaseRunnerClient(ABC):
    """Абстрактный клиент для Runner API."""

    @abstractmethod
    async def check_cv_exists(self, user_id: int) -> bool:
        """Проверить наличие CV пользователя.

        Returns:
            True если CV загружено, False иначе
        """
        pass


class RunnerClient(BaseRunnerClient):
    """HTTP клиент для HHH Runner API."""

    async def check_cv_exists(self, user_id: int) -> bool:
        """Проверить наличие CV через GET /api/cv/{user_id}."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/cv/{user_id}",
                    headers={"X-API-Key": self.api_key},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        return True
                    elif response.status == 404:
                        return False
                    else:
                        logger.error(f"CV check failed: HTTP {response.status}")
                        return False
        except Exception as e:
            logger.error(f"CV check error: {e}")
            return False
```

### 4.2 ApplyService: Новый метод

```python
# backend/src/services/apply_service.py

class ApplyService:
    """Сервис создания отклика на вакансию."""

    def __init__(
        self,
        token_service: TokenService,
        apply_analyzer: ApplyAnalyzer,
        bot: Bot,
    ):
        self.token_service = token_service
        self.apply_analyzer = apply_analyzer
        self.bot = bot
        self.runner_client = apply_analyzer.runner_client  # Доступ к клиенту

    async def check_cv_exists(self, user_id: int) -> bool:
        """Проверить наличие загруженного CV.

        Returns:
            True если CV загружено, False иначе
        """
        return await self.runner_client.check_cv_exists(user_id)
```

### 4.3 Bot Handler: Проверка CV

```python
# backend/src/bot/handlers/apply.py

async def _start_apply_flow(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Общая логика запуска создания отклика."""
    apply_service = _get_apply_service(session, message.bot)

    # Отменяем предыдущий отклик
    await apply_service.cancel(message.from_user.id)

    # Проверяем доступ (подписка/баланс)
    can_access, _ = await apply_service.check_access(message.from_user.id)
    if not can_access:
        await message.answer(
            "У вас не активирована подписка.\n\n"
            "Воспользуйтесь пополнением баланса /balance\n\n"
            "Если у вас есть промокод введите его /promo"
        )
        return

    # НОВАЯ ПРОВЕРКА: наличие CV
    has_cv = await apply_service.check_cv_exists(message.from_user.id)
    if not has_cv:
        await message.answer(ERROR_NO_CV)
        return

    # Показываем форму для ввода URL
    await state.set_state(ApplyStates.waiting_for_url)
    await message.answer(PROMPT.format(cost=APPLY_COST), parse_mode="HTML")
```

---

## 5. Тестирование

### 5.1 Runner API Tests

```python
# runner/tests/test_cv_endpoint.py

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_check_cv_exists_success(client: AsyncClient):
    """CV загружено → 200 OK."""
    user_id = 123456

    # Upload CV first
    await upload_test_cv(client, user_id)

    # Check CV
    response = await client.get(
        f"/api/cv/{user_id}",
        headers={"X-API-Key": "test-key"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user_id
    assert data["has_cv"] is True
    assert "cv_filename" in data

@pytest.mark.asyncio
async def test_check_cv_not_found(client: AsyncClient):
    """CV не загружено → 404 Not Found."""
    user_id = 999999

    response = await client.get(
        f"/api/cv/{user_id}",
        headers={"X-API-Key": "test-key"}
    )

    assert response.status_code == 404
    data = response.json()
    assert "CV not found" in data["detail"]

@pytest.mark.asyncio
async def test_check_cv_unauthorized(client: AsyncClient):
    """Неверный API ключ → 401 Unauthorized."""
    response = await client.get(
        "/api/cv/123",
        headers={"X-API-Key": "invalid-key"}
    )

    assert response.status_code == 401
```

### 5.2 Telegram Bot Tests

```python
# backend/tests/bot/test_apply_cv_check.py

import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_apply_without_cv_shows_error(mock_message, mock_state, mock_session):
    """Команда /apply без CV → показывается ERROR_NO_CV."""
    with patch("src.services.runner.client.RunnerClient.check_cv_exists") as mock_check:
        mock_check.return_value = False

        await cmd_apply(mock_message, mock_state, mock_session)

        # Проверяем что показалась ошибка
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]
        assert "Резюме не найдено" in call_args

        # Состояние не должно измениться
        mock_state.set_state.assert_not_called()

@pytest.mark.asyncio
async def test_apply_with_cv_shows_prompt(mock_message, mock_state, mock_session):
    """Команда /apply с CV → показывается форма для URL."""
    with patch("src.services.runner.client.RunnerClient.check_cv_exists") as mock_check:
        mock_check.return_value = True

        await cmd_apply(mock_message, mock_state, mock_session)

        # Проверяем что показалась форма
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]
        assert "Отклик на вакансию" in call_args

        # Состояние должно измениться
        mock_state.set_state.assert_called_once_with(ApplyStates.waiting_for_url)
```

---

## 6. План реализации

### Приоритет 1: Runner API

1. ✅ **Спецификация** (этот документ)
2. ⬜ **Storage interface** - `CVStorage.get_cv_info(user_id)`
3. ⬜ **Endpoint** - `GET /api/cv/{user_id}`
4. ⬜ **Tests** - Unit + Integration тесты
5. ⬜ **Deploy** - Раскатка на сервер Runner API

### Приоритет 2: Telegram Bot

1. ✅ **Спецификация** (этот документ)
2. ⬜ **RunnerClient.check_cv_exists()** - Метод для проверки CV
3. ⬜ **ApplyService.check_cv_exists()** - Обёртка над клиентом
4. ⬜ **apply.py handler** - Проверка CV перед показом формы
5. ⬜ **Tests** - Unit тесты хендлера
6. ⬜ **Deploy** - Раскатка бота

---

## 7. Альтернативы

### Альтернатива 1: Проверка через API /apply

**Идея:** Не добавлять отдельный endpoint, а возвращать 404 сразу при создании задачи `/api/apply`.

**Минусы:**
- Нужно создавать задачу даже для проверки
- Нагрузка на очередь задач
- Медленнее (создание задачи занимает время)

### Альтернатива 2: Кэш в боте

**Идея:** Кэшировать факт загрузки CV на стороне бота после успешного анализа `/cv`.

**Минусы:**
- Десинхронизация: CV может быть удалено на Runner, но бот об этом не знает
- Сложность invalidation кэша

### Альтернатива 3: Локальное хранение метаданных

**Идея:** Хранить флаг `has_cv` в таблице `users` в базе бота.

**Минусы:**
- Дублирование данных
- Десинхронизация между Runner и ботом
- Single Source of Truth нарушен

---

## 8. Вопросы для решения

### Q1: Как долго хранится CV на Runner?

**Вопрос:** Есть ли TTL для загруженных CV? Удаляются ли они автоматически?

**Важность:** Если CV могут удаляться автоматически, нужен механизм уведомления пользователя.

### Q2: Можно ли перезаписать CV?

**Вопрос:** Если пользователь загружает CV повторно через `/cv`, старый файл перезаписывается или создается новая версия?

**Важность:** Влияет на UX и логику endpoint'а `/api/cv/{user_id}`.

### Q3: Доступ к CV других пользователей

**Вопрос:** Нужна ли дополнительная авторизация при запросе `/api/cv/{user_id}`?

**Текущее решение:** Проверка только через `X-API-Key`, без привязки к конкретному пользователю.

**Риск:** Если API ключ скомпрометирован, можно проверить наличие CV любого пользователя.

---

## 9. Документация для разработчиков

### Runner API Developer

**Задача:** Реализовать endpoint `GET /api/cv/{user_id}`

**Файлы:**
- `runner/api/routes/cv.py` - Новый роутер
- `runner/storage/cv_storage.py` - Storage interface (если нет)
- `runner/tests/test_cv_endpoint.py` - Тесты

**Референсы:**
- Аналог: `POST /api/apply` (для создания задачи)
- Auth: `X-API-Key` как в других endpoint'ах

### Telegram Bot Developer

**Задача:** Добавить проверку CV в команду `/apply`

**Файлы:**
- `backend/src/services/runner/client.py` - Метод `check_cv_exists()`
- `backend/src/services/apply_service.py` - Метод `check_cv_exists()`
- `backend/src/bot/handlers/apply.py` - Проверка перед показом формы
- `backend/tests/bot/test_apply_cv_check.py` - Тесты

**Референсы:**
- Аналог: `check_access()` в `ApplyService`
- Auth: используется `self.runner_client` из `ApplyAnalyzer`

---

## 10. Checklist для PR

### Runner API PR

- [ ] Endpoint `GET /api/cv/{user_id}` реализован
- [ ] Возвращает 200 OK если CV есть
- [ ] Возвращает 404 Not Found если CV нет
- [ ] Unit тесты покрывают happy path и edge cases
- [ ] Integration тесты проверяют реальные запросы
- [ ] Документация API обновлена (OpenAPI spec)

### Telegram Bot PR

- [ ] `RunnerClient.check_cv_exists()` реализован
- [ ] `ApplyService.check_cv_exists()` реализован
- [ ] Handler `/apply` проверяет CV перед показом формы
- [ ] Показывается `ERROR_NO_CV` если CV нет
- [ ] Unit тесты покрывают оба сценария (с CV и без)
- [ ] Документация обновлена

---

## 11. Метрики успеха

### Метрика 1: Сокращение ошибок после ввода URL

**До:** Пользователь получает ошибку "CV not found" после ввода URL вакансии

**После:** Пользователь получает ошибку **до** ввода URL

**Измерение:**
- Количество событий `ERROR_NO_CV` показано без ввода URL
- Количество событий `ERROR_NO_CV` показано после ввода URL

**Цель:** 100% ошибок показываются до ввода URL

### Метрика 2: Скорость отклика на ошибку

**До:** ~10-30 секунд (время ожидания ответа от Runner после ввода URL)

**После:** <1 секунда (проверка через `GET /api/cv/{user_id}`)

**Измерение:** Время от команды `/apply` до показа `ERROR_NO_CV`

### Метрика 3: Снижение нагрузки на Runner

**До:** Каждая попытка отклика без CV создает задачу в очереди

**После:** Задачи не создаются если CV нет

**Измерение:** Количество задач `/apply` с ошибкой 404 (должно стать 0)

---

## Changelog

| Версия | Дата       | Автор  | Изменения                     |
|--------|------------|--------|-------------------------------|
| 1.0    | 2026-01-13 | Claude | Первая версия спецификации    |
