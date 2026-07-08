"""Tests for prompt A/B versioning in PromptRegistry."""
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from src.pipeline.prompts.registry import PromptRegistry


@pytest.fixture(autouse=True)
def clean_cache():
    """Clear template cache before each test."""
    PromptRegistry.clear_cache()
    yield
    PromptRegistry.clear_cache()


@pytest.fixture
def tmp_templates(tmp_path):
    """Create a temporary templates directory with variant files."""
    # Default variant (a)
    (tmp_path / "test_prompt_v1.txt").write_text("Hello {user_name}, this is variant A")
    # Variant b
    (tmp_path / "test_prompt_v1_b.txt").write_text("Hey {user_name}, this is variant B")
    # Single variant template (no B variant)
    (tmp_path / "single_v1.txt").write_text("Only one variant: {user_name}")

    with patch.object(PromptRegistry, "_cache", {}):
        with patch("src.pipeline.prompts.registry.TEMPLATES_DIR", tmp_path):
            yield tmp_path


class TestListVariants:
    """Tests for PromptRegistry.list_variants."""

    def test_lists_default_and_b_variants(self, tmp_templates):
        variants = PromptRegistry.list_variants("test_prompt", "v1")
        assert "a" in variants
        assert "b" in variants
        assert len(variants) == 2

    def test_single_variant_returns_only_a(self, tmp_templates):
        variants = PromptRegistry.list_variants("single", "v1")
        assert variants == ["a"]

    def test_missing_template_returns_empty(self, tmp_templates):
        variants = PromptRegistry.list_variants("nonexistent", "v1")
        assert variants == []


class TestGetWithVariant:
    """Tests for PromptRegistry.get_with_variant."""

    def test_deterministic_selection(self, tmp_templates):
        """Same seed always selects the same variant."""
        _, v1 = PromptRegistry.get_with_variant("test_prompt", "v1", variant_seed="entity123")
        _, v2 = PromptRegistry.get_with_variant("test_prompt", "v1", variant_seed="entity123")
        assert v1 == v2

    def test_different_seeds_may_differ(self, tmp_templates):
        """Different seeds should (eventually) select different variants."""
        variants_seen = set()
        for i in range(20):
            _, v = PromptRegistry.get_with_variant(
                "test_prompt", "v1", variant_seed=f"seed_{i}"
            )
            variants_seen.add(v)

        # With 20 seeds and 2 variants, both should be hit
        assert len(variants_seen) == 2

    def test_single_variant_always_returns_a(self, tmp_templates):
        """When only one variant exists, always return it."""
        content, variant = PromptRegistry.get_with_variant(
            "single", "v1", variant_seed="anything"
        )
        assert variant == "a"
        assert "Only one variant" in content

    def test_no_seed_returns_default(self, tmp_templates):
        """No variant_seed returns the default (a) variant."""
        content, variant = PromptRegistry.get_with_variant("test_prompt", "v1")
        assert variant == "a"
        assert "variant A" in content

    def test_variant_b_content_is_correct(self, tmp_templates):
        """When variant B is selected, correct content is returned."""
        # Find a seed that picks B
        for i in range(100):
            content, v = PromptRegistry.get_with_variant(
                "test_prompt", "v1", variant_seed=f"find_b_{i}"
            )
            if v == "b":
                assert "variant B" in content
                return
        pytest.fail("Could not find a seed that selected variant B in 100 tries")

    def test_missing_template_raises(self, tmp_templates):
        with pytest.raises(FileNotFoundError):
            PromptRegistry.get_with_variant("nonexistent", "v1")


class TestRenderWithVariant:
    """Tests for PromptRegistry.render_with_variant."""

    def test_render_substitutes_variables(self, tmp_templates):
        content, variant = PromptRegistry.render_with_variant(
            "test_prompt", "v1", user_name="World"
        )
        assert variant == "a"
        assert "Hello World" in content

    def test_render_with_seed(self, tmp_templates):
        content, variant = PromptRegistry.render_with_variant(
            "test_prompt", "v1", variant_seed="seed_0", user_name="Test"
        )
        assert "Test" in content
        assert variant in ("a", "b")
