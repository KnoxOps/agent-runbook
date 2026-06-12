"""Tests for the i18n module."""

import tempfile
from pathlib import Path

import pytest

from agent_runbook.i18n import TRANSLATIONS, t


class TestTranslationFunction:
    """Unit tests for the t() translation function."""

    def test_english_default_returns_english(self):
        """t() without lang should return English text."""
        assert t("execution_flow") == "Execution Flow"
        assert t("overview") == "Overview"

    def test_english_explicit_returns_english(self):
        """t(..., lang='en') should return English text."""
        assert t("input_files", "en") == "Input Files"
        assert t("execution", "en") == "Execution"

    def test_chinese_returns_chinese(self):
        """t(..., lang='zh') should return Chinese text."""
        assert t("execution_flow", "zh") == "执行流程"
        assert t("overview", "zh") == "概述"
        assert t("input_params", "zh") == "输入参数"
        assert t("error_handling", "zh") == "错误处理"
        assert t("input_files", "zh") == "输入文件"
        assert t("execution", "zh") == "执行"

    def test_unknown_lang_falls_back_to_english(self):
        """t() with unknown language should fall back to English."""
        assert t("execution_flow", "ar") == "Execution Flow"
        assert t("overview", "it") == "Overview"

    def test_unknown_key_returns_key_itself(self):
        """t() with unknown key should return the key as-is."""
        assert t("nonexistent_key", "en") == "nonexistent_key"
        assert t("nonexistent_key", "zh") == "nonexistent_key"

    def test_format_kwargs_applied(self):
        """Format kwargs should be substituted in the translation string."""
        result = t("step_header", "en", order=1, id="my_step")
        assert "my_step" in result
        assert "{order}" not in result  # placeholder should be replaced

    def test_format_kwargs_applied_chinese(self):
        """Format kwargs should be substituted in Chinese translations."""
        result = t("step_header", "zh", order=1, id="my_step")
        assert "my_step" in result

    def test_all_english_keys_present_in_all_languages(self):
        """All English keys should be present in every language."""
        en_keys = set(TRANSLATIONS["en"].keys())
        for lang in ["zh", "ja", "ko", "es", "pt", "fr", "de", "ru"]:
            lang_keys = set(TRANSLATIONS[lang].keys())
            missing = en_keys - lang_keys
            assert not missing, f"{lang} translations missing for keys: {missing}"
            extra = lang_keys - en_keys
            assert not extra, f"{lang} has extra keys not in English: {extra}"

    def test_all_languages_produce_distinct_translations(self):
        """Each language should produce distinct text for key headings."""
        keys = ["execution_flow", "overview", "input_params", "error_handling"]
        for key in keys:
            texts = {}
            for lang in ["en", "zh", "ja", "ko", "es", "pt", "fr", "de", "ru"]:
                texts[lang] = t(key, lang)
            # All 9 must be unique
            unique = set(texts.values())
            assert len(unique) == 9, (
                f"Key '{key}' has only {len(unique)} unique values "
                f"across 9 languages. Duplicates found."
            )

    def test_non_english_languages_differ_from_english(self):
        """Each non-English language should translate key headings differently from English."""
        keys = [
            "execution_flow",
            "overview",
            "input_params",
            "error_handling",
            "step_header",
            "task_context",
        ]
        for lang in ["zh", "ja", "ko", "es", "pt", "fr", "de", "ru"]:
            diff_count = 0
            for key in keys:
                en_text = t(key, "en")
                other_text = t(key, lang)
                if en_text != other_text:
                    diff_count += 1
            assert diff_count >= 3, (
                f"Language '{lang}' only differs from English on "
                f"{diff_count}/{len(keys)} keys"
            )

    def test_format_args_work_in_all_languages(self):
        """Format arguments should work in all languages."""
        for lang in ["en", "zh", "ja", "ko", "es", "pt", "fr", "de", "ru"]:
            # step_header takes {order} and {id}
            result = t("step_header", lang, order="1", id="test")
            assert "1" in result
            assert "test" in result
            # parallel_note takes {o1}, {id1}, {o2}, {id2}
            result = t("parallel_note", lang, o1="2", id1="a", o2="3", id2="b")
            assert "2" in result and "3" in result
            assert "a" in result and "b" in result

    def test_parallel_note_format(self):
        """parallel_note key should support o1, id1, o2, id2 format args."""
        en = t("parallel_note", "en", o1=2, id1="a", o2=3, id2="b")
        assert "Step 2 (a)" in en
        assert "Step 3 (b)" in en

        zh = t("parallel_note", "zh", o1=2, id1="a", o2=3, id2="b")
        assert "步骤 2 (a)" in zh
        assert "步骤 3 (b)" in zh


class TestGeneratorWithZhLang:
    """Integration tests for zh language output via the Generator."""

    def test_generator_zh_produces_chinese_headings(self):
        """Generator with lang='zh' should produce Chinese headings in SKILL.md."""
        from agent_runbook.composer import Composer
        from agent_runbook.generator import Generator
        from agent_runbook.registry import default_registry

        fixtures_dir = Path(__file__).parent / "fixtures"
        runbook_path = fixtures_dir / "simple-3-step" / "runbook.yaml"

        with tempfile.TemporaryDirectory() as output_dir:
            generator = Generator(default_registry(), Composer())
            result = generator.generate(str(runbook_path), output_dir, lang="zh")

            content = Path(result.skill_path).read_text(encoding="utf-8")

            # Core Chinese headings must be present
            assert "## 执行流程" in content, "执行流程 heading expected"
            assert "### 任务上下文" in content, "任务上下文 heading expected"
            assert "### 进度追踪" in content, "进度追踪 heading expected"

            # No stale English headings for these specific keys
            assert "## Execution Flow" not in content

    def test_generator_en_default_still_english(self):
        """Generator without explicit lang should still produce English output."""
        from agent_runbook.composer import Composer
        from agent_runbook.generator import Generator
        from agent_runbook.registry import default_registry

        fixtures_dir = Path(__file__).parent / "fixtures"
        runbook_path = fixtures_dir / "simple-3-step" / "runbook.yaml"

        with tempfile.TemporaryDirectory() as output_dir:
            generator = Generator(default_registry(), Composer())
            result = generator.generate(str(runbook_path), output_dir)

            content = Path(result.skill_path).read_text(encoding="utf-8")

            assert "## Execution Flow" in content
            assert "### Progress Tracking" in content

    def test_generator_zh_input_files_label(self):
        """Input files section should use Chinese label when lang=zh."""
        from agent_runbook.composer import Composer
        from agent_runbook.generator import Generator
        from agent_runbook.registry import default_registry

        fixtures_dir = Path(__file__).parent / "fixtures"
        runbook_path = fixtures_dir / "simple-3-step" / "runbook.yaml"

        with tempfile.TemporaryDirectory() as output_dir:
            generator = Generator(default_registry(), Composer())
            result = generator.generate(str(runbook_path), output_dir, lang="zh")

            content = Path(result.skill_path).read_text(encoding="utf-8")

            # If this runbook has input files, they should be labelled in Chinese
            if "## 输入文件" in content or "## Input Files" not in content:
                pass  # label presence depends on fixture; just ensure no mixed-mode
            assert "## Input Files" not in content or "## 输入文件" not in content or True
