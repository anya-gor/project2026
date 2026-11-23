-- ============================================================================
-- База данных MySQL для микросервисной системы интернет-магазина «MONROE»
-- Для запуска в Open Server и просмотра в DBeaver (4 основные таблицы)
-- ============================================================================

CREATE DATABASE IF NOT EXISTS `monroe_db`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `monroe_db`;

-- Удаляем старые неиспользуемые складские таблицы, если они были созданы ранее
DROP TABLE IF EXISTS `writeoffs`;
DROP TABLE IF EXISTS `supply_batches`;

-- 1. Таблица пользователей (Покупатели и Администратор)
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `login` VARCHAR(64) NOT NULL UNIQUE COMMENT 'Номер телефона (логин)',
    `country` VARCHAR(64) NOT NULL DEFAULT 'Беларусь',
    `password` VARCHAR(128) NOT NULL COMMENT 'Пароль пользователя',
    `name` VARCHAR(128) NOT NULL DEFAULT '',
    `email` VARCHAR(128) NOT NULL DEFAULT '',
    `role` ENUM('user', 'admin') NOT NULL DEFAULT 'user' COMMENT 'Роль: user (покупатель) или admin (администратор)',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Таблица адресов доставки покупателей (вкладка «Адрес доставки» в Личном кабинете)
CREATE TABLE IF NOT EXISTS `user_addresses` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_login` VARCHAR(64) NOT NULL COMMENT 'Номер телефона владельца адреса',
    `address_text` VARCHAR(255) NOT NULL COMMENT 'Адрес доставки',
    `is_primary` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1 - Основной адрес, 0 - Дополнительный',
    CONSTRAINT `fk_addr_user` FOREIGN KEY (`user_login`) REFERENCES `users`(`login`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Таблица каталога товаров (Catalog Microservice :8001)
CREATE TABLE IF NOT EXISTS `products` (
    `id` VARCHAR(32) PRIMARY KEY,
    `sku` VARCHAR(64) NOT NULL COMMENT 'Артикул товара',
    `brand` VARCHAR(128) NOT NULL COMMENT 'Бренд (PATRIZIA PEPE, GIUSEPPE DI MORABITO)',
    `name` VARCHAR(255) NOT NULL COMMENT 'Название модели одежды или аксессуара',
    `gender` VARCHAR(32) NOT NULL DEFAULT 'ДЛЯ НЕЁ' COMMENT 'Раздел: ДЛЯ НЕЁ или ДЛЯ НЕГО',
    `category` VARCHAR(128) NOT NULL COMMENT 'Категория (Платья, Верхняя одежда, Брюки, Сумки и т.д.)',
    `subcategory` VARCHAR(128) NOT NULL DEFAULT '',
    `collection` VARCHAR(128) NOT NULL DEFAULT 'Осень 2026',
    `retail_price` DECIMAL(10, 2) NOT NULL COMMENT 'Розничная цена в BYN',
    `sizes_json` TEXT NOT NULL COMMENT 'Доступные размеры и остатки по размерам (XS, S, M, L, XL)',
    `color` VARCHAR(64) NOT NULL DEFAULT 'Черный',
    `is_new` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '1 - Показывать в блоке НОВИНКИ на главной странице',
    `image_main` TEXT NOT NULL COMMENT 'Основное фото товара',
    `image_model` TEXT NOT NULL COMMENT 'Фото на модели',
    `brand_story` TEXT COMMENT 'Блок О БРЕНДЕ',
    `description` TEXT COMMENT 'Описание товара',
    `care` TEXT COMMENT 'Уход и детали',
    `boutique_name` VARCHAR(128) DEFAULT 'Бутик «MONROE»',
    `boutique_address` VARCHAR(255) DEFAULT 'САЛОН «MONROE» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Таблица заказов покупателей (Order Microservice :8003)
CREATE TABLE IF NOT EXISTS `orders` (
    `order_id` VARCHAR(32) PRIMARY KEY,
    `product_id` VARCHAR(32) NOT NULL COMMENT 'ID купленного товара',
    `product_name` VARCHAR(255) NOT NULL COMMENT 'Название купленного товара',
    `size` VARCHAR(32) NOT NULL COMMENT 'Выбранный размер (XS, S, M, L, XL)',
    `quantity` INT NOT NULL COMMENT 'Количество купленных штук',
    `unit_retail_price` DECIMAL(10, 2) NOT NULL COMMENT 'Цена за 1 шт. (BYN)',
    `total_revenue` DECIMAL(10, 2) NOT NULL COMMENT 'Итоговая сумма заказа (BYN)',
    `customer_name` VARCHAR(128) NOT NULL COMMENT 'ФИО покупателя',
    `city` VARCHAR(128) DEFAULT 'Минск, Минская область, Беларусь',
    `delivery_method` VARCHAR(128) DEFAULT 'Доставка курьером',
    `payment_method` VARCHAR(128) DEFAULT 'Картой при получении',
    `email` VARCHAR(128) DEFAULT '',
    `phone` VARCHAR(64) DEFAULT '',
    `address` VARCHAR(255) DEFAULT '',
    `comment` TEXT,
    `sale_date` DATE NOT NULL COMMENT 'Дата оформления заказа'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Стартовые пользователи (Админ и Покупатель)
INSERT IGNORE INTO `users` (`login`, `country`, `password`, `name`, `email`, `role`) VALUES
('375291111111', 'Беларусь', 'admin123', 'Администратор MONROE', 'admin@monroe.by', 'admin'),
('375445658384', 'Беларусь', '123', 'Анна Ковалева', 'client@monroe.by', 'user');

-- Стартовые адреса доставки
INSERT IGNORE INTO `user_addresses` (`id`, `user_login`, `address_text`, `is_primary`) VALUES
(1, '375445658384', 'г. Минск, пр. Победителей, д. 65, кв. 12', 1),
(2, '375445658384', 'г. Минск, ул. М. Танка, д. 69, кв. 5', 0);
