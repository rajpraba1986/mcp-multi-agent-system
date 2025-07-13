-- Sample Database Setup Script for MCP Toolbox Integration
-- This script creates sample tables and data for demonstrating the MCP Toolbox integration

-- Drop existing tables if they exist
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS categories CASCADE;

-- Create categories table
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create customers table
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(20),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(50),
    country VARCHAR(100) DEFAULT 'USA',
    postal_code VARCHAR(20),
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Create products table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category_id INTEGER REFERENCES categories(id),
    price DECIMAL(10, 2) NOT NULL,
    cost DECIMAL(10, 2),
    sku VARCHAR(100) UNIQUE,
    stock_quantity INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create orders table
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending',
    total_amount DECIMAL(10, 2) NOT NULL,
    tax_amount DECIMAL(10, 2) DEFAULT 0,
    shipping_amount DECIMAL(10, 2) DEFAULT 0,
    discount_amount DECIMAL(10, 2) DEFAULT 0,
    payment_method VARCHAR(50),
    shipping_address TEXT,
    billing_address TEXT,
    notes TEXT
);

-- Create order_items table
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL
);

-- Insert sample categories
INSERT INTO categories (name, description) VALUES
    ('Electronics', 'Electronic devices and gadgets'),
    ('Clothing', 'Apparel and fashion items'),
    ('Books', 'Books and educational materials'),
    ('Home & Garden', 'Home improvement and gardening supplies'),
    ('Sports', 'Sports equipment and accessories'),
    ('Toys', 'Toys and games for children'),
    ('Health', 'Health and wellness products'),
    ('Automotive', 'Car parts and automotive accessories');

-- Insert sample customers
INSERT INTO customers (first_name, last_name, email, phone, address, city, state, postal_code, registration_date) VALUES
    ('John', 'Doe', 'john.doe@email.com', '+1-555-0101', '123 Main St', 'New York', 'NY', '10001', '2023-01-15'),
    ('Jane', 'Smith', 'jane.smith@email.com', '+1-555-0102', '456 Oak Ave', 'Los Angeles', 'CA', '90210', '2023-02-20'),
    ('Bob', 'Johnson', 'bob.johnson@email.com', '+1-555-0103', '789 Pine Rd', 'Chicago', 'IL', '60601', '2023-03-10'),
    ('Alice', 'Williams', 'alice.williams@email.com', '+1-555-0104', '321 Elm St', 'Houston', 'TX', '77001', '2023-04-05'),
    ('Charlie', 'Brown', 'charlie.brown@email.com', '+1-555-0105', '654 Maple Dr', 'Phoenix', 'AZ', '85001', '2023-05-12'),
    ('Diana', 'Davis', 'diana.davis@email.com', '+1-555-0106', '987 Cedar Ln', 'Philadelphia', 'PA', '19101', '2023-06-18'),
    ('Edward', 'Miller', 'edward.miller@email.com', '+1-555-0107', '147 Birch Way', 'San Antonio', 'TX', '78201', '2023-07-22'),
    ('Fiona', 'Wilson', 'fiona.wilson@email.com', '+1-555-0108', '258 Spruce St', 'San Diego', 'CA', '92101', '2023-08-30'),
    ('George', 'Moore', 'george.moore@email.com', '+1-555-0109', '369 Willow Ave', 'Dallas', 'TX', '75201', '2023-09-14'),
    ('Helen', 'Taylor', 'helen.taylor@email.com', '+1-555-0110', '741 Ash Blvd', 'San Jose', 'CA', '95101', '2023-10-08');

-- Insert sample products
INSERT INTO products (name, description, category_id, price, cost, sku, stock_quantity) VALUES
    ('Smartphone Pro', 'Latest flagship smartphone with advanced features', 1, 899.99, 450.00, 'PHONE-001', 50),
    ('Laptop Ultra', 'High-performance laptop for professionals', 1, 1299.99, 700.00, 'LAPTOP-001', 25),
    ('Wireless Headphones', 'Premium noise-canceling headphones', 1, 249.99, 120.00, 'AUDIO-001', 100),
    ('Smart Watch', 'Fitness tracking smartwatch', 1, 349.99, 180.00, 'WATCH-001', 75),
    ('Designer Jeans', 'Premium denim jeans', 2, 89.99, 35.00, 'CLOTH-001', 200),
    ('Cotton T-Shirt', 'Comfortable cotton t-shirt', 2, 24.99, 8.00, 'CLOTH-002', 300),
    ('Running Shoes', 'Professional running shoes', 2, 129.99, 60.00, 'SHOE-001', 150),
    ('Programming Guide', 'Complete guide to software development', 3, 49.99, 15.00, 'BOOK-001', 80),
    ('Cooking Basics', 'Essential cookbook for beginners', 3, 29.99, 10.00, 'BOOK-002', 120),
    ('Garden Tool Set', 'Complete set of gardening tools', 4, 79.99, 35.00, 'GARDEN-001', 60),
    ('LED Light Bulbs', 'Energy-efficient LED bulbs (4-pack)', 4, 19.99, 8.00, 'HOME-001', 400),
    ('Tennis Racket', 'Professional tennis racket', 5, 159.99, 80.00, 'SPORT-001', 40),
    ('Basketball', 'Official size basketball', 5, 39.99, 15.00, 'SPORT-002', 90),
    ('Board Game Classic', 'Classic family board game', 6, 34.99, 12.00, 'TOY-001', 70),
    ('Building Blocks', 'Educational building block set', 6, 59.99, 25.00, 'TOY-002', 110),
    ('Vitamin Supplements', 'Daily multivitamin supplements', 7, 24.99, 8.00, 'HEALTH-001', 200),
    ('Yoga Mat', 'Non-slip exercise yoga mat', 7, 39.99, 15.00, 'HEALTH-002', 85),
    ('Car Phone Mount', 'Universal smartphone car mount', 8, 19.99, 6.00, 'AUTO-001', 150),
    ('Motor Oil', 'Synthetic motor oil (5 quarts)', 8, 29.99, 12.00, 'AUTO-002', 100);

-- Insert sample orders
INSERT INTO orders (customer_id, order_date, status, total_amount, tax_amount, shipping_amount, payment_method) VALUES
    (1, '2024-01-15 10:30:00', 'completed', 949.98, 76.00, 15.99, 'credit_card'),
    (2, '2024-01-16 14:20:00', 'completed', 1379.98, 110.40, 19.99, 'paypal'),
    (3, '2024-01-17 09:15:00', 'shipped', 274.98, 22.00, 12.99, 'credit_card'),
    (4, '2024-01-18 16:45:00', 'completed', 139.98, 11.20, 9.99, 'debit_card'),
    (5, '2024-01-19 11:30:00', 'processing', 419.97, 33.60, 15.99, 'credit_card'),
    (6, '2024-01-20 13:20:00', 'completed', 79.98, 6.40, 8.99, 'paypal'),
    (7, '2024-01-21 15:10:00', 'shipped', 199.98, 16.00, 12.99, 'credit_card'),
    (8, '2024-01-22 12:40:00', 'completed', 64.98, 5.20, 7.99, 'debit_card'),
    (9, '2024-01-23 10:25:00', 'processing', 149.98, 12.00, 10.99, 'credit_card'),
    (10, '2024-01-24 14:50:00', 'completed', 89.98, 7.20, 8.99, 'paypal');

-- Insert sample order items
INSERT INTO order_items (order_id, product_id, quantity, unit_price, total_price) VALUES
    -- Order 1 (John Doe)
    (1, 1, 1, 899.99, 899.99),
    (1, 3, 1, 249.99, 249.99),
    
    -- Order 2 (Jane Smith)
    (2, 2, 1, 1299.99, 1299.99),
    (2, 4, 1, 349.99, 349.99),
    
    -- Order 3 (Bob Johnson)
    (3, 3, 1, 249.99, 249.99),
    (3, 6, 1, 24.99, 24.99),
    
    -- Order 4 (Alice Williams)
    (4, 7, 1, 129.99, 129.99),
    (4, 11, 1, 19.99, 19.99),
    
    -- Order 5 (Charlie Brown)
    (5, 12, 1, 159.99, 159.99),
    (5, 13, 1, 39.99, 39.99),
    (5, 16, 5, 24.99, 124.95),
    (5, 17, 1, 39.99, 39.99),
    
    -- Order 6 (Diana Davis)
    (6, 8, 1, 49.99, 49.99),
    (6, 9, 1, 29.99, 29.99),
    
    -- Order 7 (Edward Miller)
    (7, 12, 1, 159.99, 159.99),
    (7, 13, 1, 39.99, 39.99),
    
    -- Order 8 (Fiona Wilson)
    (8, 14, 1, 34.99, 34.99),
    (8, 9, 1, 29.99, 29.99),
    
    -- Order 9 (George Moore)
    (9, 7, 1, 129.99, 129.99),
    (9, 18, 1, 19.99, 19.99),
    
    -- Order 10 (Helen Taylor)
    (10, 5, 1, 89.99, 89.99);

-- Create indexes for better query performance
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_registration_date ON customers(registration_date);
CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_order_date ON orders(order_date);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);

-- Create views for common queries
CREATE VIEW customer_order_summary AS
SELECT 
    c.id,
    c.first_name,
    c.last_name,
    c.email,
    COUNT(o.id) as total_orders,
    COALESCE(SUM(o.total_amount), 0) as total_spent,
    COALESCE(AVG(o.total_amount), 0) as avg_order_value,
    MAX(o.order_date) as last_order_date
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
GROUP BY c.id, c.first_name, c.last_name, c.email;

CREATE VIEW product_sales_summary AS
SELECT 
    p.id,
    p.name,
    p.sku,
    c.name as category_name,
    p.price,
    COALESCE(SUM(oi.quantity), 0) as total_sold,
    COALESCE(SUM(oi.total_price), 0) as total_revenue,
    p.stock_quantity
FROM products p
LEFT JOIN categories c ON p.category_id = c.id
LEFT JOIN order_items oi ON p.id = oi.product_id
GROUP BY p.id, p.name, p.sku, c.name, p.price, p.stock_quantity;

CREATE VIEW monthly_sales_summary AS
SELECT 
    DATE_TRUNC('month', o.order_date) as month,
    COUNT(o.id) as total_orders,
    SUM(o.total_amount) as total_revenue,
    AVG(o.total_amount) as avg_order_value,
    COUNT(DISTINCT o.customer_id) as unique_customers
FROM orders o
GROUP BY DATE_TRUNC('month', o.order_date)
ORDER BY month;

-- Add some analytical functions
CREATE OR REPLACE FUNCTION get_customer_lifetime_value(customer_id_param INTEGER)
RETURNS DECIMAL(10,2) AS $$
DECLARE
    clv DECIMAL(10,2);
BEGIN
    SELECT COALESCE(SUM(total_amount), 0)
    INTO clv
    FROM orders 
    WHERE customer_id = customer_id_param;
    
    RETURN clv;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_top_products_by_category(category_id_param INTEGER, limit_param INTEGER DEFAULT 5)
RETURNS TABLE(
    product_id INTEGER,
    product_name VARCHAR(255),
    total_sold BIGINT,
    total_revenue NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.name,
        COALESCE(SUM(oi.quantity), 0) as total_sold,
        COALESCE(SUM(oi.total_price), 0) as total_revenue
    FROM products p
    LEFT JOIN order_items oi ON p.id = oi.product_id
    WHERE p.category_id = category_id_param
    GROUP BY p.id, p.name
    ORDER BY total_revenue DESC
    LIMIT limit_param;
END;
$$ LANGUAGE plpgsql;

-- Insert additional historical data for better analytics
INSERT INTO orders (customer_id, order_date, status, total_amount, tax_amount, shipping_amount, payment_method) VALUES
    -- Additional orders from previous months
    (1, '2023-11-15 10:30:00', 'completed', 159.98, 12.80, 10.99, 'credit_card'),
    (2, '2023-11-20 14:20:00', 'completed', 89.99, 7.20, 8.99, 'paypal'),
    (3, '2023-12-05 09:15:00', 'completed', 249.99, 20.00, 12.99, 'credit_card'),
    (4, '2023-12-12 16:45:00', 'completed', 79.98, 6.40, 8.99, 'debit_card'),
    (5, '2023-12-20 11:30:00', 'completed', 199.97, 16.00, 12.99, 'credit_card');

-- Insert corresponding order items for the additional orders
INSERT INTO order_items (order_id, product_id, quantity, unit_price, total_price) VALUES
    (11, 12, 1, 159.99, 159.99),
    (12, 5, 1, 89.99, 89.99),
    (13, 3, 1, 249.99, 249.99),
    (14, 10, 1, 79.99, 79.99),
    (15, 7, 1, 129.99, 129.99),
    (15, 15, 1, 59.99, 59.99);

-- Final data verification
SELECT 'Database setup completed successfully!' as status;
SELECT 'Categories: ' || COUNT(*) as info FROM categories
UNION ALL
SELECT 'Customers: ' || COUNT(*) as info FROM customers
UNION ALL
SELECT 'Products: ' || COUNT(*) as info FROM products
UNION ALL
SELECT 'Orders: ' || COUNT(*) as info FROM orders
UNION ALL
SELECT 'Order Items: ' || COUNT(*) as info FROM order_items;
