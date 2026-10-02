import pytest
from pydantic import ValidationError

from backend.app.tenants.schema import PricingConfig, BrandConfig, TenantConfig
from backend.app.core.guard import sanitize_price_leaks


class TestPricingSchemaHardening:
    def test_extra_fields_forbidden_in_pricing_config(self):
        with pytest.raises(ValidationError) as exc:
            PricingConfig.model_validate({"currency": "USD", "extra_random_key": 123})
        assert "extra_random_key" in str(exc.value)

    def test_negative_base_price_rejected(self):
        with pytest.raises(ValidationError) as exc:
            PricingConfig.model_validate({"bases": {"web_app": -1000}})
        assert "Base price" in str(exc.value) or "greater than 0" in str(exc.value).lower()

    def test_negative_multiplier_rejected(self):
        with pytest.raises(ValidationError) as exc:
            PricingConfig.model_validate({
                "multipliers": {"platforms": {"ios": -1.2}}
            })
        assert "Multiplier" in str(exc.value) or "greater than 0" in str(exc.value).lower()

    def test_invalid_low_side_factor_rejected(self):
        with pytest.raises(ValidationError) as exc:
            PricingConfig.model_validate({"low_side_factor": 1.5})
        assert "low_side_factor" in str(exc.value)

        with pytest.raises(ValidationError):
            PricingConfig.model_validate({"low_side_factor": -0.2})

    def test_invalid_range_factor_rejected(self):
        with pytest.raises(ValidationError) as exc:
            PricingConfig.model_validate({"range_factor": 0.8})
        assert "range_factor" in str(exc.value)

    def test_service_bases_team_mix_consistency(self):
        with pytest.raises(ValidationError) as exc:
            PricingConfig.model_validate({
                "bases": {"web_app": 24000, "custom_robotics": 50000},
                "team_mix": {"web_app": ["Frontend Engineer", "Backend Engineer"]}
            })
        assert "custom_robotics" in str(exc.value)

    def test_demo_pricing_yaml_passes_validation(self):
        from backend.app.tenants.loader import load_tenant, clear_tenant_cache
        clear_tenant_cache()
        config = load_tenant("demo")
        assert config.pricing.currency == "USD"
        assert config.pricing.low_side_factor == 0.80
        assert config.pricing.range_factor == 1.25

    def test_brand_config_currency_and_timezone(self):
        brand = BrandConfig(currency="USD", timezone="America/New_York")
        assert brand.currency == "USD"
        assert brand.timezone == "America/New_York"


class TestOutputPriceLeakGuard:
    def test_authorized_engine_price_allowed(self):
        estimate = {"low": 19000, "high": 24000, "range_label": "$19,000 – $24,000"}
        msg = "Based on your brief, the indicative estimate is $19,000 – $24,000 over 8 weeks."
        sanitized = sanitize_price_leaks(msg, estimate)
        assert "$19,000" in sanitized
        assert "$24,000" in sanitized

    def test_unauthorized_currency_figure_sanitized(self):
        estimate = {"low": 19000, "high": 24000, "range_label": "$19,000 – $24,000"}
        msg = "We can build this quickly for just $4,500."
        sanitized = sanitize_price_leaks(msg, estimate)
        assert "$4,500" not in sanitized
        assert "$19,000 – $24,000" in sanitized or "indicative" in sanitized.lower()

    def test_unauthorized_rupee_figure_sanitized(self):
        msg = "Our basic package starts at ₹50,000."
        sanitized = sanitize_price_leaks(msg, None)
        assert "₹50,000" not in sanitized
