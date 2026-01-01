# Роли для AI-ассистентов

Набор специализированных промптов для работы с AI над проектом. Каждая роль содержит компетенции, контрольные вопросы и чек-листы.

## Роли

| Роль | Описание | Файл |
|------|----------|------|
| **Technical Writer** | Documentation First, структура документации, шаблоны | [technical-writer.md](./technical-writer.md) |
| **Fullstack Developer** | Python, aiogram, FastAPI, Docusaurus, паттерны кода | [fullstack-developer.md](./fullstack-developer.md) |
| **System Analyst** | Data modeling, ERD, state machines, спецификации сущностей | [system-analyst.md](./system-analyst.md) |
| **Business Analyst** | Требования, User Stories, BPMN, Use Cases | [business-analyst.md](./business-analyst.md) |
| **UX/Product** | User research, flows, wireframes, метрики | [ux-product.md](./ux-product.md) |
| **Business Tracker** | Unit-экономика, Lean Canvas, валидация гипотез | [business-tracker.md](./business-tracker.md) |

## Как использовать

1. Выбрать роль, соответствующую задаче
2. Скопировать содержимое файла в контекст AI
3. Использовать контрольные вопросы и чек-листы из роли

## Взаимодействие ролей

```
Business Tracker ──► Business Analyst ──► System Analyst
       │                    │                   │
       │                    ▼                   ▼
       │              UX/Product ──────► Fullstack Developer
       │                                        │
       └───────────────────────────────────────►│
                                                ▼
                                        Technical Writer
```

- **Business Tracker** — валидирует бизнес-модель
- **Business Analyst** — формализует требования
- **System Analyst** — проектирует модель данных
- **UX/Product** — проектирует интерфейсы
- **Fullstack Developer** — реализует код
- **Technical Writer** — документирует всё

## См. также

- [Документация проекта](../index.md)
