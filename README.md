#  MONROE — Микросервисная система управления бутиком брендовой одежды и интернет-магазином

Веб-приложение на базе **микросервисной архитектуры** (4 независимых сервиса на Python FastAPI + MySQL 8.4) для автоматизации работы мультибрендового бутика дизайнерской одежды **MONROE** (Республика Беларусь, цены в **BYN**):
* витрина с женским (**«ДЛЯ НЕЁ»**) и мужским (**«ДЛЯ НЕГО»**) разделами, фильтрацией и отображением **точных остатков по каждому размеру** (`XS`, `S`, `M`, `L`, `XL`, `XXL`);
* **персональная Корзина (`users_cart`)**, **персональное Избранное (`users_favorites`)**, **личная история заказов** и редактирование **Ф.И.О.** с сохранением в БД и приветствием `«Здравствуйте, <Ф.И.О.>»`;
* складской учет: партии товаров создаются автоматически при добавлении модели администратором, на витрине отображаются точные остатки каждого размера, при продаже остаток списывается, а при отмене или возврате товар возвращается на склад;
* честная модель оплаты и возвратов: разделение статусов **«Оплачен» (`PAID`)** для онлайн-оплаты и **«Ожидает оплаты» (`UNPAID`)** для оплаты курьеру при получении, подтверждение оплаты администратором, отмена неоплаченных заказов (`CANCELLED`) и возврат оплаченных заказов с возвратом средств (`REFUNDED`) и автоматическим возвратом качественного товара на склад (`+1` к размеру);
* панель администратора с добавлением новых моделей и указанием **точного количества единиц по каждому размеру**, управлением ценами и заказами клиентов.

> 📄 Полная академическая спецификация бизнес-требований, сценариев использования (Use Cases), анализа рисков и UML-моделирования также оформлена в файле **[`docs/BUSINESS_REQUIREMENTS.md`](docs/BUSINESS_REQUIREMENTS.md)**.

---

## 📋 Содержание
1. [Бизнес-требования и описание предметной области](#-1-бизнес-требования-и-описание-предметной-области)
2. [Функциональные и нефункциональные требования](#-2-функциональные-и-нефункциональные-требования)
3. [Анализ рисков и матрица управления рисками](#-3-анализ-рисков-и-матрица-управления-рисками)
4. [UML-моделирование системы (7 диаграмм Mermaid)](#-4-uml-моделирование-системы)
   - [4.1. Диаграмма вариантов использования (Use Case Diagram)](#41-uml-диаграмма-вариантов-использования-use-case-diagram)
   - [4.2. Диаграмма микросервисной архитектуры (Component Diagram)](#42-диаграмма-микросервисной-архитектуры-component-diagram)
   - [4.3. Диаграмма последовательности: оформление заказа и списание остатков (Sequence Diagram)](#43-uml-диаграмма-последовательности-sequence-diagram-оформление-заказа-и-списание-остатков)
   - [4.4. Диаграмма последовательности: оплата курьеру, возврат товара и возврат средств (Sequence Diagram)](#44-uml-диаграмма-последовательности-sequence-diagram-оплата-курьеру-возврат-и-возврат-средств)
   - [4.5. Диаграмма состояний заказа (Statechart Diagram — Order Lifecycle)](#45-uml-диаграмма-состояний-заказа-statechart-diagram--order-lifecycle)
   - [4.6. Диаграмма состояний единицы товара в партии (Statechart Diagram — Stock Item)](#46-uml-диаграмма-состояний-единицы-товара-в-партии-statechart-diagram--stock-item)
   - [4.7. Диаграмма классов предметной области и сущностей БД (Class Diagram)](#47-uml-диаграмма-классов-предметной-области-class-diagram)
5. [Описание микросервисов и схема БД MySQL (`monroe_db`)](#-5-описание-микросервисов-и-схема-бд-mysql-monroe_db)
6. [Быстрый запуск проекта и тестовые аккаунты](#-6-быстрый-запуск-проекта-и-тестовые-аккаунты)

---

## 🎯 1. Бизнес-требования и описание предметной области

### 1.1. Проблематика бизнеса
Мультибрендовый бутик одежды (**MONROE**, Беларусь, расчеты в **BYN**) закупает коллекции дизайнерских брендов (*PATRIZIA PEPE*, *GIUSEPPE DI MORABITO* и др.) партиями у нескольких европейских поставщиков и дистрибьюторов. В работе бутика возникают 4 ключевые бизнес-проблемы:
1. **Учет остатков по каждому размеру:** и покупатель на витрине, и администратор должны видеть точное количество единиц по каждому размеру (`XS`, `S`, `M`, `L`, `XL`, `XXL`).
2. **Разделение способа оплаты и факта оплаты:** оплата «Онлайн картой на сайте» / E-POS / ЕРИП дает статус **`PAID` (Оплачен)** сразу, тогда как «Картой / наличными при получении» означает статус **`UNPAID` (Ожидает оплаты)** до тех пор, пока курьер не передаст оплату и администратор не подтвердит её.
3. **Разделение отмены и возврата:** неоплаченный заказ (`UNPAID`) можно только **отменить** (`CANCELLED`, товар возвращается на склад без движения денег). Оплаченный заказ (`PAID`) можно **вернуть** по заявке (`RETURN_REQUESTED`): при одобрении администратором клиенту возвращаются деньги (`REFUNDED`), а качественный товар возвращается в продажу (`+1` к размеру; брак списывается и на витрину не возвращается).
4. **Персонализация данных клиентов:** у каждого покупателя должны быть собственные Ф.И.О. в профиле и приветствии, собственная корзина (`users_cart`), собственное избранное (`users_favorites`) и только своя история заказов.

### 1.2. Роли пользователей (Акторы)
* **Покупатель (Клиент):** просматривает разделы «ДЛЯ НЕЁ» / «ДЛЯ НЕГО», фильтрует каталог, видит остатки по размерам, пользуется личным Избранным и личной Корзиной, редактирует Ф.И.О. и адреса доставки, оформляет заказы, отменяет неоплаченные заказы и подает заявки на возврат оплаченных заказов. Видит только свои заказы.
* **Администратор:** управляет каталогом (добавление новых товаров с указанием количества штук по каждому размеру `XS`–`XXL`, изменение цен в BYN, удаление моделей) и заказами всех клиентов (подтверждение оплаты при получении «💵 Отметить оплаченным», одобрение или отклонение заявок на возврат).

> ⚙️ В системе только **2 роли**. Отдельной роли «Кладовщик» нет: складские операции (создание партий при добавлении товара, списание остатка при заказе, возврат товара на склад) выполняются микросервисами автоматически.

---

## ⚙️ 2. Функциональные и нефункциональные требования

### 2.1. Функциональные требования (FR)
* **FR-01. Каталог и витрина:** разделы «ДЛЯ НЕЁ» и «ДЛЯ НЕГО» с гендерно-зависимыми категориями одежды и аксессуаров, размерными сетками, фильтрацией по бренду/цвету/размеру/цене, сортировкой и поиском.
* **FR-02. Персональная Корзина и Избранное в MySQL:** хранение корзины каждого пользователя в таблице `users_cart` (`GET/PUT /api/user/{login}/cart`) и избранного в таблице `users_favorites` (`GET/POST/DELETE /api/user/{login}/favorites*`).
* **FR-03. Личный кабинет и профиль пользователя:** авторизация и регистрация по номеру телефона, восстановление пароля через SMS-код, сохранение Ф.И.О. в таблицу `users` MySQL (`POST /api/auth/update-profile`) и приветствие пользователя по Ф.И.О. (`«Здравствуйте, Олег»`).
* **FR-04. Статусы оплаты заказа:**
  * онлайн-способы оплаты («Онлайн картой на сайте», E-POS, ЕРИП) → `payment_status = PAID`;
  * оплата при получении («Картой при получении», «Наличными при получении») → `payment_status = UNPAID` с последующим подтверждением администратором (`POST /orders/{id}/mark-paid`).
* **FR-05. Отмена и возврат заказов:**
  * отмена неоплаченного заказа покупателем (`POST /orders/{id}/cancel`) → `CANCELLED` + возврат размера на склад;
  * заявка на возврат оплаченного заказа (`POST /orders/{id}/return-request`) и решение администратора (`POST /orders/{id}/return-decision`) → при одобрении `payment_status = REFUNDED`, качественный товар возвращается на склад (`+1`), брак списывается.
* **FR-06. Изоляция истории заказов:** покупатель видит во вкладках «Текущие заказы» и «История заказов» только свои заказы; администратор во вкладке «Заказы клиентов» видит заказы всех покупателей.
* **FR-07. Панель администратора с вводом остатков по размерам:** добавление товара с указанием количества единиц по размерам `XS`, `S`, `M`, `L`, `XL`, `XXL` (автоматическое создание партий на складе), изменение цен и удаление товаров.

### 2.2. Нефункциональные требования (NFR)
* **NFR-01. Микросервисная архитектура:** 4 независимых сервиса (`Gateway :8000`, `Catalog :8001`, `Warehouse :8002`, `Order :8003`), взаимодействующих по HTTP/REST.
* **NFR-02. Хранение данных (MySQL 8.4 + JSON Fallback):** основная СУБД — **MySQL 8.4** (Open Server, `127.0.1.31:3306`, база `monroe_db`, 7 таблиц) с автоматическим резервированием в JSON-файлы.
* **NFR-03. Мониторинг здоровья (Health-check):** верхняя панель сайта в реальном времени опрашивает `/api/system-status` и отображает статус всех микросервисов и подключения к MySQL.

---

## ⚠️ 3. Анализ рисков и матрица управления рисками

| ID | Категория | Описание риска | Вероятность | Влияние | Меры минимизации (Mitigation) в системе |
|:---:|:---|:---|:---:|:---:|:---|
| **R-01** | Бизнес / Склад | **Продажа отсутствующего размера (Overselling):** оформление заказа на закончившийся размер. | Средняя | Высокое | Синхронная проверка и атомарное списание размера в `Warehouse Service` перед подтверждением заказа. |
| **R-02** | Бизнес / Финансы | **Возврат денег по неоплаченному заказу:** попытка оформить возврат до фактической оплаты курьеру. | Средняя | Среднее | Возврат (`return-request`) разрешен строго для `PAID`; для `UNPAID` доступна только отмена (`CANCELLED`) без возврата денег. |
| **R-03** | Бизнес / Склад | **Потеря товара при возврате или попадание брака обратно на витрину.** | Средняя | Высокое | Эндпоинт `POST /stock/return-item` возвращает `+1` на склад только при `is_defect = false`; брак не возвращается в продажу. |
| **R-04** | Безопасность / Данные | **Смешивание корзин, избранного и истории заказов разных пользователей.** | Средняя | Высокое | Персональные таблицы `users_cart` и `users_favorites` в MySQL, фильтрация заказов по логину/телефону пользователя, изоляция ключей `localStorage`. |
| **R-05** | Технический | **Отказ отдельного микросервиса или остановка MySQL в Open Server.** | Средняя | Среднее | Изоляция процессов, таймауты HTTP-запросов, health-check панель в шапке сайта и автоматический JSON-fallback. |

---

## 📊 4. UML-моделирование системы

### 4.1. UML-диаграмма вариантов использования (Use Case Diagram)

```mermaid
﻿flowchart LR
    subgraph Actors ["Роли пользователей (Акторы)"]
        Customer(["👤 Покупатель"])
        Admin(["💼 Администратор"])
    end

    subgraph MONROE_System ["Микросервисная система бутика одежды MONROE"]
        UC1("Просмотр каталога «ДЛЯ НЕЁ» / «ДЛЯ НЕГО»\nи точных остатков по размерам")
        UC2("Фильтрация и поиск по бренду,\nкатегории, размеру, цвету и цене")
        UC3("Управление личным Избранным\n(таблица users_favorites)")
        UC4("Управление личной Корзиной\n(таблица users_cart)")
        UC5("Оформление заказа с выбором\nспособа оплаты и доставки")
        UC6("Редактирование Ф.И.О. и адресов\nв Личном кабинете (таблица users)")
        UC7("Просмотр личных текущих заказов\nи личной истории заказов")
        UC8("Отмена неоплаченного заказа (UNPAID -> CANCELLED)")
        UC9("Подача заявки на возврат\nоплаченного заказа (PAID -> RETURN_REQUESTED)")
        UC10("Авторизация, регистрация и\nвосстановление пароля по SMS-коду")

        UC11("Добавление товара с указанием\nколичества по размерам (XS..XXL)")
        UC12("Изменение розничных цен (BYN)\nи удаление моделей из каталога")
        UC13("Подтверждение оплаты курьеру\n(UNPAID -> PAID)")
        UC14("Одобрение / отклонение возврата\n(возврат средств REFUNDED + возврат на склад)")

        UC15("Автоматическое создание складской партии\nпри добавлении товара (система)")
    end

    Customer --> UC1
    Customer --> UC2
    Customer --> UC3
    Customer --> UC4
    Customer --> UC5
    Customer --> UC6
    Customer --> UC7
    Customer --> UC8
    Customer --> UC9
    Customer --> UC10

    Admin --> UC10
    Admin --> UC11
    Admin --> UC12
    Admin --> UC13
    Admin --> UC14

    UC11 -.->|"«include» создание партий"| UC15
    UC9 -.->|"«extend» решение админа"| UC14
```

---

### 4.2. Диаграмма микросервисной архитектуры (Component Diagram)

```mermaid
flowchart TB
    Browser["🌐 Браузер клиента / администратора\n(SPA-интерфейс MONROE: Витрина, Личный кабинет, Админ-панель)"]

    subgraph GatewayLayer ["Единая точка входа (Port 8000)"]
        Gateway["🚪 API Gateway & Web UI\n(FastAPI + Static SPA)\nПрофиль, Авторизация, Избранное, Корзина, Прокси /api/*"]
    end

    subgraph Microservices ["Слой бизнес-микросервисов"]
        Catalog["👕 Catalog Service (:8001)\nМодели одежды, бренды, разделы\n«ДЛЯ НЕЁ» / «ДЛЯ НЕГО», цены BYN"]
        Warehouse["🏭 Warehouse Service (:8002)\nПартии поставщиков, остатки по размерам,\nсписание при продаже, возврат на склад, списания"]
        Order["🛍️ Order Service (:8003)\nОформление заказов, статусы оплаты\n(UNPAID/PAID/REFUNDED/CANCELLED), возвраты"]
    end

    subgraph Storage ["Слой хранения данных (MySQL 8.4 + JSON Fallback)"]
        MySQL[("🗄️ MySQL 8.4 (Open Server)\nmonroe_db @ 127.0.1.31:3306\n7 таблиц: users, user_addresses, products,\norders, order_returns, users_favorites, users_cart")]
        DB1[("catalog_db.json")]
        DB2[("warehouse_db.json")]
        DB3[("orders_db.json")]
        DB4[("users_db.json")]
    end

    Browser <-->|"HTTP / REST (JSON)"| Gateway
    Gateway <-->|"REST API"| Catalog
    Gateway <-->|"REST API"| Warehouse
    Gateway <-->|"REST API"| Order

    Order -->|"1. Проверка модели и цены"| Catalog
    Order -->|"2. Списание размера"| Warehouse
    Order -->|"3. Возврат товара при отмене/возврате"| Warehouse

    Gateway --- MySQL
    Gateway --- DB4
    Catalog --- MySQL
    Catalog --- DB1
    Warehouse --- DB2
    Order --- MySQL
    Order --- DB3
```

---

### 4.3. UML-диаграмма последовательности (Sequence Diagram): Оформление заказа и списание остатков

```mermaid
sequenceDiagram
    autonumber
    actor Client as 👤 Покупатель
    participant GW as 🚪 Gateway UI (:8000)
    participant OS as 🛍️ Order Service (:8003)
    participant CS as 👕 Catalog Service (:8001)
    participant WS as 🏭 Warehouse Service (:8002)
    participant DB as 🗄️ MySQL (monroe_db)

    Client->>GW: Добавляет товар (размер S) в корзину
    GW->>DB: PUT /api/user/{login}/cart (таблица users_cart)
    Client->>GW: Заполняет доставку, выбирает способ оплаты и нажимает «Подтвердить заказ»
    GW->>OS: POST /orders/checkout (items, user_login, payment_method, address)
    OS->>CS: GET /products/{product_id}
    CS-->>OS: Данные модели и розничная цена (1 050 BYN)
    OS->>WS: POST /stock/deduct-sale (product_id, size="S", quantity=1)
    Note over WS: Списание нужного количества размера S со складского остатка
    WS-->>OS: 200 OK (размер S списан, остаток уменьшен)
    alt Онлайн-оплата (Картой на сайте / E-POS / ЕРИП)
        Note over OS: payment_status = "PAID"
    else Оплата при получении (Картой / Наличными курьеру)
        Note over OS: payment_status = "UNPAID"
    end
    OS->>DB: INSERT INTO orders (order_id, phone=user_login, payment_status, ...)
    OS-->>GW: 201 Created (Заказ оформлен, статус оплаты)
    GW->>DB: Очистка личной корзины пользователя в users_cart
    GW-->>Client: Переход в Личный кабинет -> «Текущие заказы»
```

---

### 4.4. UML-диаграмма последовательности (Sequence Diagram): Оплата курьеру, возврат и возврат средств

```mermaid
sequenceDiagram
    autonumber
    actor Client as 👤 Покупатель
    actor Admin as 💼 Администратор
    participant GW as 🚪 Gateway UI (:8000)
    participant OS as 🛍️ Order Service (:8003)
    participant WS as 🏭 Warehouse Service (:8002)
    participant DB as 🗄️ MySQL (monroe_db)

    Note over Client,DB: 1. Курьер доставил заказ, клиент оплатил при получении
    Admin->>GW: Нажимает «💵 Отметить оплаченным» в «Заказы клиентов»
    GW->>OS: POST /orders/{id}/mark-paid
    OS->>DB: UPDATE orders SET payment_status='PAID', paid_at=CURDATE()
    OS-->>GW: 200 OK (payment_status = PAID)

    Note over Client,DB: 2. Через день клиент оформляет заявку на возврат
    Client->>GW: Выбирает причину и нажимает «Оформить возврат»
    GW->>OS: POST /orders/{id}/return-request
    OS->>DB: UPDATE orders SET return_status='RETURN_REQUESTED' + INSERT INTO order_returns
    OS-->>GW: 200 OK (Заявка на рассмотрении)

    Note over Client,DB: 3. Администратор одобряет возврат
    Admin->>GW: Нажимает «✓ Одобрить возврат»
    GW->>OS: POST /orders/{id}/return-decision (APPROVE)
    alt Причина НЕ брак («Не подошел размер / фасон»)
        OS->>WS: POST /stock/return-item (is_defect=false)
        WS-->>OS: RESTOCKED (+1 шт. размера на склад)
    else Причина — «Обнаружен производственный брак»
        OS->>WS: POST /stock/return-item (is_defect=true)
        WS-->>OS: DEFECT_NOT_RESTOCKED (списано в брак)
    end
    OS->>DB: UPDATE orders SET return_status='RETURN_APPROVED', payment_status='REFUNDED'
    OS-->>GW: 200 OK (Возврат средств выполнен)
    GW-->>Client: Статус «Возврат средств» + «✓ Возврат одобрен»
```

---

### 4.5. UML-диаграмма состояний заказа (Statechart Diagram — Order Lifecycle)

```mermaid
stateDiagram-v2
    [*] --> UNPAID : Заказ с оплатой при получении
    [*] --> PAID : Заказ с онлайн-оплатой (карта / E-POS / ЕРИП)

    UNPAID --> PAID : Админ «Отметить оплаченным»
    UNPAID --> CANCELLED : Покупатель «Отменить заказ» (товар +1 на склад)

    PAID --> RETURN_REQUESTED : Покупатель «Оформить возврат»
    RETURN_REQUESTED --> REFUNDED : Админ одобрил (деньги возвращены,\nтовар +1 на склад если не брак)
    RETURN_REQUESTED --> PAID : Админ отклонил (return_status = RETURN_REJECTED)

    CANCELLED --> [*]
    REFUNDED --> [*]
```

---

### 4.6. UML-диаграмма состояний единицы товара в партии (Statechart Diagram — Stock Item)

```mermaid
stateDiagram-v2
    [*] --> ПринятаНаСклад : Поступление партии (POST /batches)
    ПринятаНаСклад --> ВПродаже : Срок реализации активен
    ВПродаже --> СкороКонецСезона : До конца срока <= 14 дней
    СкороКонецСезона --> ПроданаПокупателю : Оформлен заказ
    ВПродаже --> ПроданаПокупателю : Оформлен заказ
    ПроданаПокупателю --> ВПродаже : Отмена заказа или одобрен возврат (не брак)
    ПроданаПокупателю --> СписанаБрак : Одобрен возврат по браку (is_defect = true)
    СкороКонецСезона --> СрокИстек : Наступила дата expiry_date
    СрокИстек --> СписанаПоСроку : Акт списания просрочки
    ВПродаже --> СписанаБрак : Обнаружен брак
    СписанаПоСроку --> [*]
    СписанаБрак --> [*]
```

---

### 4.7. UML-диаграмма классов предметной области (Class Diagram)

```mermaid
classDiagram
    class User {
        +String login
        +String country
        +String password
        +String name
        +String email
        +String role
    }

    class UserAddress {
        +Int id
        +String user_login
        +String address_text
        +Bool is_primary
    }

    class UserFavorite {
        +Int id
        +String user_login
        +String product_id
        +String product_name
    }

    class UserCartItem {
        +Int id
        +String user_login
        +String product_id
        +String size
        +Int quantity
    }

    class Product {
        +String id
        +String sku
        +String brand
        +String name
        +String gender
        +String category
        +String color
        +String collection
        +Float retail_price
        +List~String~ sizes
    }

    class SupplyBatch {
        +String batch_id
        +String product_id
        +String size
        +String supplier_name
        +Float purchase_price
        +Int initial_quantity
        +Int remaining_quantity
        +Date arrival_date
        +Date expiry_date
    }

    class WriteOffRecord {
        +String writeoff_id
        +String batch_id
        +String product_id
        +String size
        +Int quantity
        +Float purchase_price
        +Float total_loss
        +String reason
        +Date date
    }

    class Order {
        +String order_id
        +String product_id
        +String product_name
        +String size
        +Int quantity
        +Float unit_retail_price
        +Float total_revenue
        +Float total_supplier_cost
        +Float gross_profit
        +String customer_name
        +String phone
        +String payment_method
        +String payment_status
        +String paid_at
        +String refunded_at
        +String return_status
        +String return_reason
        +Date sale_date
    }

    class OrderReturn {
        +String order_id
        +String reason
        +String status
        +Bool restocked_to_store
    }

    User "1" <-- "*" UserAddress : адреса доставки
    User "1" <-- "*" UserFavorite : личное избранное
    User "1" <-- "*" UserCartItem : личная корзина
    User "1" <-- "*" Order : личные заказы
    Product "1" <-- "*" UserFavorite : в избранном
    Product "1" <-- "*" UserCartItem : в корзине
    Product "1" <-- "*" SupplyBatch : поступает партиями
    SupplyBatch "1" <-- "*" WriteOffRecord : списывается из партии
    Product "1" <-- "*" Order : продается в заказе
    Order "1" <-- "0..1" OrderReturn : заявка на возврат
```

---

## 🧩 5. Описание микросервисов и схема БД MySQL (`monroe_db`)

### 5.1. Микросервисы

| Сервис | Порт | Папка | Назначение и ключевые эндпоинты |
|:---|:---:|:---|:---|
| **Gateway & Frontend** | `8000` | `gateway_frontend/` | Веб-интерфейс бутика и админ-панели, авторизация и сохранение Ф.И.О. (`/api/auth/update-profile`, `/api/user/{login}/profile`), персональное избранное (`/api/user/{login}/favorites*`), персональная корзина (`/api/user/{login}/cart`), мониторинг сервисов (`/api/system-status`). |
| **Catalog Service** | `8001` | `services/catalog_service/` | Управление моделями одежды, брендами, разделами («ДЛЯ НЕЁ» / «ДЛЯ НЕГО»), категориями и ценами (`GET/POST /products`, `PATCH/DELETE /products/{id}`). |
| **Warehouse Service** | `8002` | `services/warehouse_service/` | Приход партий по размерам (`POST /batches`), остатки по размерам (`GET /stock/summary`), списание остатка при продаже (`POST /stock/deduct-sale`), возврат товара на склад при отмене/возврате (`POST /stock/return-item`), списания (`POST /writeoffs`), истекающие партии (`GET /alerts/expiring`). |
| **Order Service** | `8003` | `services/order_service/` | Оформление заказов (`POST /orders/checkout`) со статусами оплаты (`UNPAID`/`PAID`/`REFUNDED`/`CANCELLED`), подтверждение оплаты при получении (`POST /orders/{id}/mark-paid`), отмена неоплаченного заказа (`POST /orders/{id}/cancel`), заявки и решения по возврату (`POST /orders/{id}/return-request`, `POST /orders/{id}/return-decision`). |

### 5.2. Таблицы базы данных `monroe_db` (MySQL 8.4)
SQL-скрипт для **DBeaver**: [`database/monroe_mysql.sql`](database/monroe_mysql.sql)

1. **`users`** — пользователи и администраторы (`login`, `password`, `name` — Ф.И.О., `email`, `role`).
2. **`user_addresses`** — адреса доставки покупателей (`user_login`, `address_text`, `is_primary`).
3. **`products`** — каталог товаров бутика с ценами в BYN и JSON-остатками по размерам.
4. **`orders`** — заказы с привязкой к клиенту (`phone`), себестоимостью проданного товара, статусом оплаты (`payment_status`, `paid_at`, `refunded_at`) и статусом возврата (`return_status`, `return_reason`).
5. **`order_returns`** — реестр заявок на возврат и решений администратора (`restocked_to_store`).
6. **`users_favorites`** — персональное избранное каждого покупателя (`user_login`, `product_id`).
7. **`users_cart`** — персональная корзина каждого покупателя (`user_login`, `product_id`, `size`, `quantity`).

---

## 🚀 6. Быстрый запуск проекта и тестовые аккаунты

### Вариант 1. Запуск одной командой на Windows / macOS / Linux (Рекомендуется)
1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
2. Запустите все 4 микросервиса одним скриптом:
   ```bash
   python run_all.py
   ```
   *(На Windows также можно дважды кликнуть по файлу **`start.bat`**).*
3. Откройте в браузере:
   * **Веб-приложение бутика MONROE:** [http://localhost:8000](http://localhost:8000)
   * **Swagger UI (Catalog Service):** [http://localhost:8001/docs](http://localhost:8001/docs)
   * **Swagger UI (Warehouse Service):** [http://localhost:8002/docs](http://localhost:8002/docs)
   * **Swagger UI (Order Service):** [http://localhost:8003/docs](http://localhost:8003/docs)

### Подключение MySQL 8.4 (Open Server + DBeaver)
* **Хост:** `127.0.1.31` | **Порт:** `3306` | **Пользователь:** `root` | **Пароль:** *(пустой)* | **База:** `monroe_db`

### Тестовые аккаунты
| Роль | Логин (телефон) | Пароль | Имя в профиле |
|:---|:---|:---|:---|
| Покупатель 1 | `375445658384` | `123` | Анна Ковалева |
| Покупатель 2 | `375447573540` | `123` | Олег |
| Администратор | `375291111111` (или `admin`) | `admin123` | Администратор MONROE |

### Вариант 2. Запуск в контейнерах Docker Compose
```bash
docker-compose up --build
```
