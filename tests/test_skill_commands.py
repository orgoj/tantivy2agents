"""
Tests for skill commands (skill-usage, skill-setup).
"""

import os
import sys
import tempfile
import unittest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tantivy2agents.agent import TantivyAgent


class TestSkillCommands(unittest.TestCase):
    """Test skill command functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

        # Create git directory (required for project root detection)
        os.makedirs(".git", exist_ok=True)

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_dir)
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_skill_usage_command_outputs_to_stdout(self):
        """Test skill-usage command outputs to stdout."""
        agent = TantivyAgent(quiet=True)

        # Capture stdout
        from io import StringIO

        captured_output = StringIO()
        sys.stdout = captured_output

        agent.skill_usage_command()

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        # Verify output contains expected content
        self.assertIn("tantivy2agents - Usage Guide", output)
        self.assertIn("## Commands Reference", output)
        self.assertIn("### index - Build or Update Search Index", output)
        self.assertIn("### search - Search Indexed Documents", output)

    def test_skill_setup_command_outputs_to_stdout(self):
        """Test skill-setup command outputs to stdout."""
        agent = TantivyAgent(quiet=True)

        # Capture stdout
        from io import StringIO

        captured_output = StringIO()
        sys.stdout = captured_output

        agent.skill_setup_command()

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        # Verify output contains expected content
        self.assertIn("tantivy2agents - Setup and Configuration Guide", output)
        self.assertIn("## Installation", output)
        self.assertIn("## Configuration File", output)
        self.assertIn("### index_dirs", output)

    def test_skill_usage_command_saves_to_file(self):
        """Test skill-usage command can save to file."""
        agent = TantivyAgent(quiet=True)

        output_file = os.path.join(self.test_dir, "usage_guide.md")
        agent.skill_usage_command(output_file)

        # Verify file was created
        self.assertTrue(os.path.exists(output_file))

        # Verify content
        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("tantivy2agents - Usage Guide", content)
        self.assertIn("## Commands Reference", content)

    def test_skill_setup_command_saves_to_file(self):
        """Test skill-setup command can save to file."""
        agent = TantivyAgent(quiet=True)

        output_file = os.path.join(self.test_dir, "setup_guide.md")
        agent.skill_setup_command(output_file)

        # Verify file was created
        self.assertTrue(os.path.exists(output_file))

        # Verify content
        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("tantivy2agents - Setup and Configuration Guide", content)
        self.assertIn("## Installation", content)

    def test_skill_files_are_valid_markdown(self):
        """Test skill files are valid markdown with proper frontmatter."""
        agent = TantivyAgent(quiet=True)

        # Get skill file paths
        usage_path = agent._find_skill_file("tantivy2agents-usage")
        setup_path = agent._find_skill_file("tantivy2agents-setup")

        # Verify files exist
        self.assertTrue(os.path.exists(usage_path))
        self.assertTrue(os.path.exists(setup_path))

        # Verify frontmatter
        with open(usage_path, "r", encoding="utf-8") as f:
            usage_content = f.read()

        with open(setup_path, "r", encoding="utf-8") as f:
            setup_content = f.read()

        # Check for YAML frontmatter
        self.assertIn("---", usage_content)
        self.assertIn("name:", usage_content)
        self.assertIn("description:", usage_content)

        self.assertIn("---", setup_content)
        self.assertIn("name:", setup_content)
        self.assertIn("description:", setup_content)

    def test_skill_usage_skill_name_correct(self):
        """Test skill-usage has correct name and description."""
        agent = TantivyAgent(quiet=True)

        usage_path = agent._find_skill_file("tantivy2agents-usage")

        with open(usage_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check frontmatter
        self.assertIn("name: tantivy2agents-usage", content)
        self.assertIn(
            "description: Daily usage of tantivy2agents - search, index, status commands",
            content,
        )

    def test_skill_setup_skill_name_correct(self):
        """Test skill-setup has correct name and description."""
        agent = TantivyAgent(quiet=True)

        setup_path = agent._find_skill_file("tantivy2agents-setup")

        with open(setup_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check frontmatter
        self.assertIn("name: tantivy2agents-setup", content)
        self.assertIn(
            "description: Setup and configuration of tantivy2agents",
            content,
        )

    def test_find_skill_file_package_location(self):
        """Test _find_skill_file finds skill in package location."""
        agent = TantivyAgent(quiet=True)

        # Should find skill in package directory
        path = agent._find_skill_file("tantivy2agents-usage")

        self.assertTrue(os.path.exists(path))
        self.assertTrue(path.endswith("skills/tantivy2agents-usage/SKILL.md"))

    def test_find_skill_file_ignores_local_claude_fallback(self):
        """Test _find_skill_file only resolves packaged skill files."""
        local_skill_dir = os.path.join(
            self.test_dir, ".claude", "skills", "tantivy2agents-usage"
        )
        os.makedirs(local_skill_dir, exist_ok=True)
        local_skill_path = os.path.join(local_skill_dir, "SKILL.md")
        with open(local_skill_path, "w", encoding="utf-8") as f:
            f.write("# Local duplicate should not be used\n")

        agent = TantivyAgent(quiet=True)
        path = agent._find_skill_file("tantivy2agents-usage")

        self.assertNotEqual(path, local_skill_path)
        self.assertTrue(
            path.endswith("src/tantivy2agents/skills/tantivy2agents-usage/SKILL.md")
        )

    def test_skill_usage_contains_all_sections(self):
        """Test skill-usage contains all expected sections."""
        agent = TantivyAgent(quiet=True)

        usage_path = agent._find_skill_file("tantivy2agents-usage")

        with open(usage_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for key sections
        expected_sections = [
            "## Quick Start",
            "## Commands Reference",
            "## Output Format Examples",
            "## YAML Frontmatter",
            "## Search Tips",
            "## Best Practices",
            "## Troubleshooting",
        ]

        for section in expected_sections:
            self.assertIn(section, content)

    def test_skill_setup_contains_all_sections(self):
        """Test skill-setup contains all expected sections."""
        agent = TantivyAgent(quiet=True)

        setup_path = agent._find_skill_file("tantivy2agents-setup")

        with open(setup_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for key sections
        expected_sections = [
            "## Installation",
            "## Auto-Setup",
            "## Project Type Detection",
            "## Configuration File",
            "## Configuration Options",
            "## Claude Code Hook Setup",
            "## Troubleshooting Setup",
        ]

        for section in expected_sections:
            self.assertIn(section, content)


if __name__ == "__main__":
    unittest.main()
