-- Setup trial tariff and promo codes for production
-- Execute this on production database

-- 1. Create trial tariff (if not exists)
DO $$
DECLARE
    v_tariff_id UUID;
BEGIN
    -- Check if trial tariff exists
    SELECT id INTO v_tariff_id FROM tariffs WHERE slug = 'trial-30-7';

    IF v_tariff_id IS NULL THEN
        -- Create trial tariff
        INSERT INTO tariffs (
            id, slug, name, description,
            price, tokens, subscription_days,
            period_unit, period_value,
            subscription_fee, min_payment,
            is_active, sort_order, version,
            created_at, updated_at
        ) VALUES (
            gen_random_uuid(),
            'trial-30-7',
            'Пробный тариф',
            'Пробный период для новых пользователей: 30 токенов + 8 дней подписки',
            0.01, -- минимальная цена для соблюдения constraint
            30,   -- tokens
            0,    -- legacy subscription_days
            'day',
            8,    -- period_value (день активации + 7 дней)
            0,    -- subscription_fee
            0.01, -- min_payment
            false, -- не показывать в списке тарифов
            999,
            1,
            NOW(),
            NOW()
        ) RETURNING id INTO v_tariff_id;

        RAISE NOTICE 'Created trial tariff with ID: %', v_tariff_id;
    ELSE
        RAISE NOTICE 'Trial tariff already exists with ID: %', v_tariff_id;
    END IF;

    -- 2. Create promo codes (if not exist)
    -- TRIAL2025
    IF NOT EXISTS (SELECT 1 FROM promo_codes WHERE code = 'TRIAL2025') THEN
        INSERT INTO promo_codes (
            id, code, discount_type, discount_value,
            max_uses, uses_count,
            valid_from, valid_until,
            tariff_id, is_active,
            created_at, updated_at
        ) VALUES (
            gen_random_uuid(),
            'TRIAL2025',
            'bonus_tokens',
            1, -- минимальное значение (не используется в логике)
            100,
            0,
            NOW(),
            NULL,
            v_tariff_id,
            true,
            NOW(),
            NOW()
        );
        RAISE NOTICE 'Created promo code: TRIAL2025';
    ELSE
        RAISE NOTICE 'Promo code TRIAL2025 already exists';
    END IF;

    -- WELCOME100
    IF NOT EXISTS (SELECT 1 FROM promo_codes WHERE code = 'WELCOME100') THEN
        INSERT INTO promo_codes (
            id, code, discount_type, discount_value,
            max_uses, uses_count,
            valid_from, valid_until,
            tariff_id, is_active,
            created_at, updated_at
        ) VALUES (
            gen_random_uuid(),
            'WELCOME100',
            'bonus_tokens',
            1,
            50,
            0,
            NOW(),
            NULL,
            v_tariff_id,
            true,
            NOW(),
            NOW()
        );
        RAISE NOTICE 'Created promo code: WELCOME100';
    ELSE
        RAISE NOTICE 'Promo code WELCOME100 already exists';
    END IF;

    -- FRIENDLY
    IF NOT EXISTS (SELECT 1 FROM promo_codes WHERE code = 'FRIENDLY') THEN
        INSERT INTO promo_codes (
            id, code, discount_type, discount_value,
            max_uses, uses_count,
            valid_from, valid_until,
            tariff_id, is_active,
            created_at, updated_at
        ) VALUES (
            gen_random_uuid(),
            'FRIENDLY',
            'bonus_tokens',
            1,
            100,
            0,
            NOW(),
            NULL,
            v_tariff_id,
            true,
            NOW(),
            NOW()
        );
        RAISE NOTICE 'Created promo code: FRIENDLY';
    ELSE
        RAISE NOTICE 'Promo code FRIENDLY already exists';
    END IF;

    -- TESTCODE
    IF NOT EXISTS (SELECT 1 FROM promo_codes WHERE code = 'TESTCODE') THEN
        INSERT INTO promo_codes (
            id, code, discount_type, discount_value,
            max_uses, uses_count,
            valid_from, valid_until,
            tariff_id, is_active,
            created_at, updated_at
        ) VALUES (
            gen_random_uuid(),
            'TESTCODE',
            'bonus_tokens',
            1,
            10,
            0,
            NOW(),
            NULL,
            v_tariff_id,
            true,
            NOW(),
            NOW()
        );
        RAISE NOTICE 'Created promo code: TESTCODE';
    ELSE
        RAISE NOTICE 'Promo code TESTCODE already exists';
    END IF;
END $$;

-- 3. Verify setup
SELECT 'Trial Tariff:' as info;
SELECT id, slug, name, tokens, period_value, period_unit FROM tariffs WHERE slug = 'trial-30-7';

SELECT '' as info;
SELECT 'Promo Codes:' as info;
SELECT pc.code, pc.max_uses, pc.uses_count, t.slug as tariff_slug
FROM promo_codes pc
JOIN tariffs t ON pc.tariff_id = t.id
WHERE t.slug = 'trial-30-7'
ORDER BY pc.code;
