-- ============================================================================
-- База данных MySQL для микросервисной системы бутика одежды «MAD FASHION»
-- Для запуска в Open Server и просмотра в DBeaver
-- ============================================================================

CREATE DATABASE IF NOT EXISTS `mad_fashion_db`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `mad_fashion_db`;

-- 1. Таблица пользователей (Покупатели и Администратор)
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `login` VARCHAR(64) NOT NULL UNIQUE COMMENT 'Номер телефона (логин)',
    `country` VARCHAR(64) NOT NULL DEFAULT 'Беларусь',
    `password` VARCHAR(128) NOT NULL COMMENT 'Пароль пользователя',
    `name` VARCHAR(128) NOT NULL DEFAULT '',
    `email` VARCHAR(128) NOT NULL DEFAULT '',
    `role` ENUM('user', 'admin') NOT NULL DEFAULT 'user' COMMENT 'Роль: user или admin',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Таблица адресов доставки покупателей
CREATE TABLE IF NOT EXISTS `user_addresses` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_login` VARCHAR(64) NOT NULL,
    `address_text` VARCHAR(255) NOT NULL,
    `is_primary` TINYINT(1) NOT NULL DEFAULT 0,
    CONSTRAINT `fk_addr_user` FOREIGN KEY (`user_login`) REFERENCES `users`(`login`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Таблица каталога товаров (Catalog Microservice :8001)
CREATE TABLE IF NOT EXISTS `products` (
    `id` VARCHAR(32) PRIMARY KEY,
    `sku` VARCHAR(64) NOT NULL,
    `brand` VARCHAR(128) NOT NULL,
    `name` VARCHAR(255) NOT NULL,
    `gender` VARCHAR(32) NOT NULL DEFAULT 'ДЛЯ НЕЁ',
    `category` VARCHAR(128) NOT NULL,
    `subcategory` VARCHAR(128) NOT NULL DEFAULT '',
    `collection` VARCHAR(128) NOT NULL DEFAULT 'Осень 2026',
    `retail_price` DECIMAL(10, 2) NOT NULL COMMENT 'Розничная цена в BYN',
    `sizes_json` TEXT NOT NULL COMMENT 'JSON-массив доступных размеров',
    `color` VARCHAR(64) NOT NULL DEFAULT 'Черный',
    `is_new` TINYINT(1) NOT NULL DEFAULT 1,
    `image_main` TEXT NOT NULL,
    `image_model` TEXT NOT NULL,
    `brand_story` TEXT,
    `description` TEXT,
    `care` TEXT,
    `boutique_name` VARCHAR(128) DEFAULT 'Бутик «PATRIZIA PEPE»',
    `boutique_address` VARCHAR(255) DEFAULT 'САЛОН «PATRIZIA PEPE» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Таблица партий поставок на склад (Warehouse Microservice :8002)
CREATE TABLE IF NOT EXISTS `supply_batches` (
    `batch_id` VARCHAR(32) PRIMARY KEY,
    `product_id` VARCHAR(32) NOT NULL,
    `product_name` VARCHAR(255) NOT NULL,
    `size` VARCHAR(32) NOT NULL,
    `supplier_name` VARCHAR(255) NOT NULL,
    `purchase_price` DECIMAL(10, 2) NOT NULL COMMENT 'Закупочная цена у поставщика (BYN)',
    `initial_quantity` INT NOT NULL,
    `remaining_quantity` INT NOT NULL,
    `arrival_date` DATE NOT NULL,
    `expiry_date` DATE NOT NULL COMMENT 'Срок окончания сезонной реализации'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Таблица актов списания (просрочка сезона / брак)
CREATE TABLE IF NOT EXISTS `writeoffs` (
    `writeoff_id` VARCHAR(32) PRIMARY KEY,
    `batch_id` VARCHAR(32) NOT NULL,
    `product_id` VARCHAR(32) NOT NULL,
    `product_name` VARCHAR(255) NOT NULL,
    `size` VARCHAR(32) NOT NULL,
    `supplier_name` VARCHAR(255) NOT NULL,
    `quantity` INT NOT NULL,
    `purchase_price` DECIMAL(10, 2) NOT NULL,
    `total_loss` DECIMAL(10, 2) NOT NULL,
    `reason` VARCHAR(32) NOT NULL COMMENT 'EXPIRED или DEFECT',
    `reason_label` VARCHAR(255) NOT NULL,
    `comment` VARCHAR(255) DEFAULT '',
    `date` DATE NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Таблица заказов покупателей (Order Microservice :8003)
CREATE TABLE IF NOT EXISTS `orders` (
    `order_id` VARCHAR(32) PRIMARY KEY,
    `product_id` VARCHAR(32) NOT NULL,
    `product_name` VARCHAR(255) NOT NULL,
    `size` VARCHAR(32) NOT NULL,
    `quantity` INT NOT NULL,
    `unit_retail_price` DECIMAL(10, 2) NOT NULL,
    `total_revenue` DECIMAL(10, 2) NOT NULL,
    `total_supplier_cost` DECIMAL(10, 2) NOT NULL,
    `gross_profit` DECIMAL(10, 2) NOT NULL,
    `customer_name` VARCHAR(128) NOT NULL,
    `city` VARCHAR(128) DEFAULT 'Минск, Минская область, Беларусь',
    `delivery_method` VARCHAR(128) DEFAULT 'Доставка курьером',
    `payment_method` VARCHAR(128) DEFAULT 'Картой при получении',
    `email` VARCHAR(128) DEFAULT '',
    `phone` VARCHAR(64) DEFAULT '',
    `address` VARCHAR(255) DEFAULT '',
    `comment` TEXT,
    `sale_date` DATE NOT NULL,
    `allocations_json` TEXT COMMENT 'JSON с партиями поставщиков (FIFO)'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Стартовые пользователи (Админ и Покупатель)
INSERT IGNORE INTO `users` (`login`, `country`, `password`, `name`, `email`, `role`) VALUES
('375291111111', 'Беларусь', 'admin123', 'Администратор MAD FASHION', 'admin@madfashion.by', 'admin'),
('375445658384', 'Беларусь', '123', 'Анна Ковалева', 'client@madfashion.by', 'user');
