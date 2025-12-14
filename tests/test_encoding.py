#!/usr/bin/env python3
"""
Encoding detection tests for Tantivy Agent functionality
"""

import os
import sys
import json
import tempfile

# Add the parent directory to the path to import the agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tantivy2agents import TantivyAgent


def run_test(test_name, test_func):
    """Run a test function and report results"""
    try:
        test_func()
        print(f"✅ {test_name}")
        return True
    except Exception as e:
        import traceback

        print(f"❌ {test_name}: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False


def test_encoding_configuration_defaults():
    """Test that encoding configuration has proper defaults"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Initialize agent with default config
            agent = TantivyAgent()

            # Check encoding config defaults
            encoding_config = agent.config.get("encoding", {})

            assert (
                encoding_config.get("default_encoding") == "utf-8"
            ), "Default encoding should be utf-8"
            assert encoding_config.get(
                "auto_detect"
            ), "Auto-detect should be enabled by default"
            assert "utf-8" in encoding_config.get(
                "fallback_encodings", []
            ), "UTF-8 should be in fallback encodings"
            assert "cp1252" in encoding_config.get(
                "fallback_encodings", []
            ), "cp1252 should be in fallback encodings"
            assert (
                len(encoding_config.get("binary_extensions", [])) > 0
            ), "Should have binary extensions configured"
            assert (
                encoding_config.get("detection_confidence_threshold") == 0.7
            ), "Default confidence threshold should be 0.7"

        finally:
            os.chdir(original_cwd)


def test_utf8_file_reading():
    """Test reading UTF-8 encoded files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Create test file with UTF-8 content
            test_content = "This is a test file with UTF-8 content.\nIncludes special chars: áéíóú ñ 漢字"
            with open("test_utf8.txt", "w", encoding="utf-8") as f:
                f.write(test_content)

            agent = TantivyAgent()
            content, encoding = agent._read_file_with_encoding_detection(
                "test_utf8.txt"
            )

            assert content is not None, "Should be able to read UTF-8 file"
            assert encoding == "utf-8", "Should detect UTF-8 encoding"
            assert test_content in content, "Content should match original"

        finally:
            os.chdir(original_cwd)


def test_binary_file_detection():
    """Test binary file detection and exclusion"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            agent = TantivyAgent()

            # Test with image file extension
            assert agent._is_binary_file("test.jpg"), "Should detect .jpg as binary"
            assert agent._is_binary_file("test.png"), "Should detect .png as binary"
            assert agent._is_binary_file("test.pdf"), "Should detect .pdf as binary"
            assert agent._is_binary_file("test.zip"), "Should detect .zip as binary"

            # Test with text file extension
            assert not agent._is_binary_file(
                "test.txt"
            ), "Should not detect .txt as binary"
            assert not agent._is_binary_file(
                "test.md"
            ), "Should not detect .md as binary"

            # Test with actual binary content
            binary_content = b"\x00\x01\x02\x03\x04\x05\xff\xfe\xfd"
            with open("binary_file.dat", "wb") as f:
                f.write(binary_content)

            assert agent._is_binary_file(
                "binary_file.dat", binary_content
            ), "Should detect file with null bytes as binary"

            # Test with actual text content
            text_content = b"This is regular text content with ASCII characters only."
            with open("text_file.dat", "wb") as f:
                f.write(text_content)

            assert not agent._is_binary_file(
                "text_file.dat", text_content
            ), "Should not detect text content as binary"

        finally:
            os.chdir(original_cwd)


def test_file_specific_encoding_rules():
    """Test file-specific encoding configuration"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Create config with file-specific encoding rules
            config = {
                "version": "1.0",
                "index_dir": ".tantivy-data",
                "global_patterns": {"include": ["*"], "exclude": []},
                "index_dirs": ["./"],
                "encoding": {
                    "default_encoding": "utf-8",
                    "auto_detect": False,  # Disable to test specific rules
                    "file_specific_encodings": {
                        "*.txt": "cp1252",
                        "legacy/*.md": "iso-8859-1",
                        "special.txt": "utf-16",
                    },
                },
            }

            with open(".tantivy2agents.json", "w") as f:
                json.dump(config, f)

            agent = TantivyAgent()

            # Test file-specific encoding rules
            assert (
                agent._get_encoding_for_file("test.txt") == "cp1252"
            ), "Should apply *.txt rule"
            assert (
                agent._get_encoding_for_file("legacy/document.md") == "iso-8859-1"
            ), "Should apply legacy/*.md rule"
            assert (
                agent._get_encoding_for_file("special.txt") == "utf-16"
            ), "Should apply specific file rule"
            assert (
                agent._get_encoding_for_file("unknown.xyz") == "utf-8"
            ), "Should use default for unknown patterns"

        finally:
            os.chdir(original_cwd)


def test_fallback_encoding_mechanism():
    """Test fallback encoding when primary detection fails"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Create a simple config
            config = {
                "version": "1.0",
                "index_dir": ".tantivy-data",
                "global_patterns": {"include": ["*"], "exclude": []},
                "index_dirs": ["./"],
                "encoding": {
                    "default_encoding": "utf-8",
                    "auto_detect": False,  # Disable auto-detect to test fallbacks
                    "fallback_encodings": ["cp1252", "iso-8859-1", "utf-8"],
                },
            }

            with open(".tantivy2agents.json", "w") as f:
                json.dump(config, f)

            agent = TantivyAgent()

            # Create a file with cp1252 content that would fail as UTF-8
            cp1252_content = "Text with Windows-1252 characters: © ®".encode("cp1252")
            with open("test_cp1252.txt", "wb") as f:
                f.write(cp1252_content)

            content, encoding = agent._read_file_with_encoding_detection(
                "test_cp1252.txt"
            )

            assert (
                content is not None
            ), "Should be able to read file with fallback encoding"
            assert "©" in content, "Content should be properly decoded"

        finally:
            os.chdir(original_cwd)


def test_encoding_info_command():
    """Test the encoding-info command functionality"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Create test files
            with open("test_utf8.md", "w", encoding="utf-8") as f:
                f.write("# UTF-8 Test\nThis is UTF-8 content.")

            # Create binary file
            with open("test_binary.jpg", "wb") as f:
                f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF")  # JPEG header

            # Create config
            config = {
                "version": "1.0",
                "index_dir": ".tantivy-data",
                "global_patterns": {"include": ["*"], "exclude": []},
                "index_dirs": ["./"],
            }

            with open(".tantivy2agents.json", "w") as f:
                json.dump(config, f)

            # Test encoding info command
            agent = TantivyAgent()

            # This should not raise an exception
            try:
                agent.encoding_info_command()
                # If we get here, the command executed without exceptions
                command_success = True
            except Exception as e:
                command_success = False
                raise e

            assert command_success, "Encoding info command should execute successfully"

        finally:
            os.chdir(original_cwd)


def test_encoding_during_indexing():
    """Test that encoding detection works during actual indexing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Create test directory structure
            os.makedirs("docs")

            # Create UTF-8 file
            with open("docs/utf8_doc.md", "w", encoding="utf-8") as f:
                f.write("# UTF-8 Document\nContent with UTF-8: héllo wörld")

            # Create binary file that should be skipped
            with open("docs/image.png", "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")

            # Create config
            config = {
                "version": "1.0",
                "index_dir": ".tantivy-data",
                "global_patterns": {"include": ["*"], "exclude": []},
                "index_dirs": ["docs/"],
            }

            with open(".tantivy2agents.json", "w") as f:
                json.dump(config, f)

            # Test indexing
            agent = TantivyAgent()

            # This should index the UTF-8 file but skip the binary file
            agent.index_command(force=True)

            # Check that index was created
            index_dir = os.path.join(".tantivy-data", "idx")
            assert os.path.exists(index_dir), "Index should be created"

            # Test search to verify indexing worked
            try:
                agent.search_command("UTF-8")
                search_success = True
            except Exception:
                search_success = False

            assert (
                search_success
            ), "Search should work after indexing with encoding detection"

        finally:
            os.chdir(original_cwd)


def main():
    """Run all encoding tests"""
    print("🧪 Running encoding detection tests...")

    tests = [
        ("Encoding configuration defaults", test_encoding_configuration_defaults),
        ("UTF-8 file reading", test_utf8_file_reading),
        ("Binary file detection", test_binary_file_detection),
        ("File-specific encoding rules", test_file_specific_encoding_rules),
        ("Fallback encoding mechanism", test_fallback_encoding_mechanism),
        ("Encoding info command", test_encoding_info_command),
        ("Encoding during indexing", test_encoding_during_indexing),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        if run_test(test_name, test_func):
            passed += 1

    print(f"\n📊 Encoding test results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All encoding tests passed!")
        return 0
    else:
        print("💥 Some encoding tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
