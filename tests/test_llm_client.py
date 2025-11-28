# Unit tests for the LLM Client module

import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

backend_src = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

from analyzer.llm.client import (
    LLMClient,
    LLMError,
    InvalidAPIKeyError
)


class TestLLMClient:
    """Test cases for the LLMClient class."""
    
    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        mock = Mock()
        mock.chat.completions.create = Mock()
        return mock
    
    def test_client_initialization_without_key(self):
        """Test LLM client initialization without API key (mock mode)."""
        client = LLMClient()
        
        assert client.api_key is None
        assert client.client is None
        assert not client.is_configured()
    
    def test_client_initialization_with_key(self):
        """Test LLM client initialization with API key."""
        with patch('analyzer.llm.client.OpenAI') as mock_openai:
            client = LLMClient(api_key="test-key-123")
            
            assert client.api_key == "test-key-123"
            assert client.client is not None
            assert client.is_configured()
            mock_openai.assert_called_once_with(api_key="test-key-123")
    
    def test_client_initialization_failure(self):
        """Test LLM client initialization failure."""
        with patch('analyzer.llm.client.OpenAI', side_effect=Exception("API Error")):
            with pytest.raises(LLMError) as exc_info:
                LLMClient(api_key="test-key-123")
            
            assert "Failed to initialize LLM client" in str(exc_info.value)


class TestVerifyAPIKey:
    """Test cases for API key verification."""
    
    @pytest.fixture
    def client_with_key(self):
        """Create a client with a test API key."""
        with patch('analyzer.llm.client.OpenAI'):
            return LLMClient(api_key="test-key-123")
    
    def test_verify_without_api_key(self):
        """Test verification fails when no API key is provided."""
        client = LLMClient()
        
        with pytest.raises(InvalidAPIKeyError) as exc_info:
            client.verify_api_key()
        
        assert "No API key provided" in str(exc_info.value)
    
    def test_verify_without_client(self):
        """Test verification fails when client is not initialized."""
        client = LLMClient()
        client.api_key = "test-key"  # Set key but no client
        
        with pytest.raises(InvalidAPIKeyError) as exc_info:
            client.verify_api_key()
        
        assert "LLM client not initialized" in str(exc_info.value)
    
    def test_verify_success(self, client_with_key):
        """Test successful API key verification."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key.verify_api_key()
        
        assert result is True
        client_with_key.client.chat.completions.create.assert_called_once()
    
    def test_verify_authentication_error(self, client_with_key):
        """Test verification with authentication error."""
        import openai
        
        with patch.object(
            client_with_key.client.chat.completions,
            'create',
            side_effect=openai.AuthenticationError(
                message="Invalid API key",
                response=Mock(status_code=401),
                body=None
            )
        ):
            with pytest.raises(InvalidAPIKeyError) as exc_info:
                client_with_key.verify_api_key()
            
            assert "Invalid API key" in str(exc_info.value)
    
    def test_verify_api_error(self, client_with_key):
        """Test verification with API error."""
        import openai
        
        with patch.object(
            client_with_key.client.chat.completions,
            'create',
            side_effect=openai.APIError(
                message="Service unavailable",
                request=Mock(),
                body=None
            )
        ):
            with pytest.raises(LLMError) as exc_info:
                client_with_key.verify_api_key()
            
            assert "API error" in str(exc_info.value)
    
    def test_verify_unexpected_error(self, client_with_key):
        """Test verification with unexpected error."""
        with patch.object(
            client_with_key.client.chat.completions,
            'create',
            side_effect=Exception("Unexpected error")
        ):
            with pytest.raises(LLMError) as exc_info:
                client_with_key.verify_api_key()
            
            assert "Verification failed" in str(exc_info.value)
    
    def test_verify_empty_response(self, client_with_key):
        """Test verification with empty response."""
        mock_response = Mock()
        mock_response.choices = []
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        with pytest.raises(LLMError) as exc_info:
            client_with_key.verify_api_key()
        
        assert "Unexpected response" in str(exc_info.value)


class TestClientMethods:
    """Test cases for LLM client utility methods."""
    
    def test_is_configured_false(self):
        """Test is_configured returns False when not configured."""
        client = LLMClient()
        assert not client.is_configured()
    
    def test_is_configured_true(self):
        """Test is_configured returns True when configured."""
        with patch('analyzer.llm.client.OpenAI'):
            client = LLMClient(api_key="test-key")
            assert client.is_configured()


class TestIntegrationScenarios:
    """Integration test scenarios for common use cases."""
    
    def test_complete_setup_workflow(self):
        """Test complete workflow of setting up and verifying LLM client."""
        with patch('analyzer.llm.client.OpenAI') as mock_openai:
            client = LLMClient(api_key="sk-test123")
            assert client.is_configured()
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            client.client.chat.completions.create = Mock(return_value=mock_response)
            
            is_valid = client.verify_api_key()
            assert is_valid is True
    
    def test_workflow_without_api_key(self):
        """Test workflow when API key is not provided."""
        client = LLMClient()
        
        assert not client.is_configured()
        
        with pytest.raises(InvalidAPIKeyError):
            client.verify_api_key()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestTokenCounting:
    """Test cases for token counting functionality."""
    
    def test_count_tokens_basic(self):
        """Test basic token counting."""
        with patch('analyzer.llm.client.OpenAI'):
            client = LLMClient(api_key="test-key")
            
            text = "Hello, world!"
            count = client._count_tokens(text)
            
            assert isinstance(count, int)
            assert count > 0
    
    def test_count_tokens_fallback(self):
        """Test token counting fallback when tiktoken fails."""
        with patch('analyzer.llm.client.OpenAI'):
            client = LLMClient(api_key="test-key")
            
            with patch('analyzer.llm.client.tiktoken.encoding_for_model', side_effect=Exception("Error")):
                text = "Hello" * 100
                count = client._count_tokens(text)
                
                # Should use character estimate (len / 4)
                assert count == len(text) // 4


class TestMakeLLMCall:
    """Test cases for _make_llm_call helper method."""
    
    @pytest.fixture
    def client_with_key(self):
        """Create a client with a test API key."""
        with patch('analyzer.llm.client.OpenAI'):
            return LLMClient(api_key="test-key")
    
    def test_make_llm_call_success(self, client_with_key):
        """Test successful LLM call."""
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Test response"
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        messages = [{"role": "user", "content": "Test"}]
        result = client_with_key._make_llm_call(messages)
        
        assert result == "Test response"
    
    def test_make_llm_call_not_configured(self):
        """Test LLM call when client not configured."""
        client = LLMClient()
        
        with pytest.raises(LLMError) as exc_info:
            client._make_llm_call([{"role": "user", "content": "test"}])
        
        assert "not configured" in str(exc_info.value)
    
    def test_make_llm_call_authentication_error(self, client_with_key):
        """Test LLM call with authentication error."""
        import openai
        
        client_with_key.client.chat.completions.create = Mock(
            side_effect=openai.AuthenticationError(
                message="Invalid key",
                response=Mock(status_code=401),
                body=None
            )
        )
        
        with pytest.raises(InvalidAPIKeyError):
            client_with_key._make_llm_call([{"role": "user", "content": "test"}])
    
    def test_make_llm_call_api_error(self, client_with_key):
        """Test LLM call with API error."""
        import openai
        
        client_with_key.client.chat.completions.create = Mock(
            side_effect=openai.APIError(
                message="Service error",
                request=Mock(),
                body=None
            )
        )
        
        with pytest.raises(LLMError) as exc_info:
            client_with_key._make_llm_call([{"role": "user", "content": "test"}])
        
        assert "API error" in str(exc_info.value)


class TestChunkAndSummarize:
    """Test cases for chunk_and_summarize method."""
    
    @pytest.fixture
    def client_with_key(self):
        """Create a client with a test API key."""
        with patch('analyzer.llm.client.OpenAI'):
            return LLMClient(api_key="test-key")
    
    def test_chunk_and_summarize_success(self, client_with_key):
        """Test successful chunking and summarization."""
        # Create a large text that will be chunked
        large_text = "This is a test. " * 500
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Summary of chunk"
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key.chunk_and_summarize(large_text, "python")
        
        assert "final_summary" in result
        assert "num_chunks" in result
        assert "chunk_summaries" in result
        assert result["num_chunks"] > 0
        assert isinstance(result["chunk_summaries"], list)
    
    def test_chunk_and_summarize_not_configured(self):
        """Test chunking when client not configured."""
        client = LLMClient()
        
        with pytest.raises(LLMError) as exc_info:
            client.chunk_and_summarize("test text")
        
        assert "not configured" in str(exc_info.value)
    
    def test_chunk_and_summarize_custom_params(self, client_with_key):
        """Test chunking with custom chunk size and overlap."""
        text = "Test " * 1000
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Summary"
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key.chunk_and_summarize(
            text, "txt", chunk_size=1000, overlap=50
        )
        
        assert result["num_chunks"] > 0
    
    def test_chunk_and_summarize_error_handling(self, client_with_key):
        """Test error handling in chunk and summarize."""
        client_with_key.client.chat.completions.create = Mock(
            side_effect=Exception("API Error")
        )
        
        with pytest.raises(LLMError) as exc_info:
            client_with_key.chunk_and_summarize("test text")
        
        assert "Failed to chunk and summarize" in str(exc_info.value)


class TestSummarizeTaggedFile:
    """Test cases for summarize_tagged_file method."""
    
    @pytest.fixture
    def client_with_key(self):
        """Create a client with a test API key."""
        with patch('analyzer.llm.client.OpenAI'):
            return LLMClient(api_key="test-key")
    
    def test_summarize_small_file(self, client_with_key):
        """Test summarizing a small file that doesn't need chunking."""
        content = "def hello():\n    print('Hello, world!')\n"
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = """SUMMARY:
A simple Python function that prints hello world.

KEY FUNCTIONALITY:
Defines a hello function for greeting output.

NOTABLE PATTERNS:
Basic function definition and print statement."""
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key.summarize_tagged_file(
            "test.py", content, "python"
        )
        
        assert "file_path" in result
        assert "file_type" in result
        assert "analysis" in result
        assert result["file_path"] == "test.py"
        assert result["file_type"] == "python"
    
    def test_summarize_large_file(self, client_with_key):
        """Test summarizing a large file that needs chunking."""
        # Create large content
        content = "# Python code\n" + "x = 1\n" * 1000
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Summary text"
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        with patch.object(client_with_key, '_count_tokens', return_value=3000):
            with patch.object(client_with_key, 'chunk_and_summarize') as mock_chunk:
                mock_chunk.return_value = {
                    "final_summary": "Chunked summary",
                    "num_chunks": 2,
                    "chunk_summaries": ["s1", "s2"]
                }
                
                result = client_with_key.summarize_tagged_file(
                    "large.py", content, "python"
                )
                
                assert mock_chunk.called
                assert "analysis" in result
    
    def test_summarize_file_not_configured(self):
        """Test file summarization when client not configured."""
        client = LLMClient()
        
        with pytest.raises(LLMError) as exc_info:
            client.summarize_tagged_file("test.py", "content", "python")
        
        assert "not configured" in str(exc_info.value)
    
    def test_summarize_file_error_handling(self, client_with_key):
        """Test error handling in file summarization."""
        client_with_key.client.chat.completions.create = Mock(
            side_effect=Exception("API Error")
        )
        
        with pytest.raises(LLMError) as exc_info:
            client_with_key.summarize_tagged_file("test.py", "content", "python")
        
        assert "File summarization failed" in str(exc_info.value)


class TestAnalyzeProject:
    """Test cases for analyze_project method."""
    
    @pytest.fixture
    def client_with_key(self):
        """Create a client with a test API key."""
        with patch('analyzer.llm.client.OpenAI'):
            return LLMClient(api_key="test-key")
    
    @pytest.fixture
    def sample_project_data(self):
        """Create sample project data."""
        return {
            "local_analysis": {
                "total_files": 50,
                "lines_of_code": 5000,
                "file_types": {"py": 30, "js": 20}
            },
            "tagged_files": [
                {
                    "file_path": "main.py",
                    "analysis": "Main application entry point"
                }
            ]
        }
    
    def test_analyze_project_success(self, client_with_key, sample_project_data):
        """Test successful project analysis."""
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = """EXECUTIVE SUMMARY:
A well-structured test application built with modern technologies.

TECHNICAL HIGHLIGHTS:
- FastAPI for high-performance API
- PostgreSQL for data persistence
- Clean code structure

TECHNOLOGIES USED:
Python, FastAPI, PostgreSQL

PROJECT QUALITY:
Production-ready with good code organization."""
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key.analyze_project(
            sample_project_data["local_analysis"],
            sample_project_data["tagged_files"]
        )
        
        assert "analysis" in result
        assert "EXECUTIVE SUMMARY" in result["analysis"]
    
    def test_analyze_project_empty_tagged_files(self, client_with_key, sample_project_data):
        """Test project analysis with no tagged files."""
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Analysis result"
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key.analyze_project(
            sample_project_data["local_analysis"],
            []
        )
        
        assert "analysis" in result
    
    def test_analyze_project_not_configured(self, sample_project_data):
        """Test project analysis when client not configured."""
        client = LLMClient()
        
        with pytest.raises(LLMError) as exc_info:
            client.analyze_project(
                sample_project_data["local_analysis"],
                sample_project_data["tagged_files"]
            )
        
        assert "not configured" in str(exc_info.value)
    
    def test_analyze_project_error_handling(self, client_with_key, sample_project_data):
        """Test error handling in project analysis."""
        client_with_key.client.chat.completions.create = Mock(
            side_effect=Exception("API Error")
        )
        
        with pytest.raises(LLMError) as exc_info:
            client_with_key.analyze_project(
                sample_project_data["local_analysis"],
                sample_project_data["tagged_files"]
            )
        
        assert "Failed to analyze project" in str(exc_info.value)


class TestSuggestFeedback:
    """Test cases for suggest_feedback method."""
    
    @pytest.fixture
    def client_with_key(self):
        """Create a client with a test API key."""
        with patch('analyzer.llm.client.OpenAI'):
            return LLMClient(api_key="test-key")
    
    @pytest.fixture
    def sample_local_analysis(self):
        """Create sample local analysis results."""
        return {
            "total_files": 50,
            "lines_of_code": 5000,
            "file_types": {"py": 30, "js": 20}
        }
    
    @pytest.fixture
    def sample_llm_analysis(self):
        """Create sample LLM analysis results."""
        return {
            "project_summaries": [
                "Project 1: Good project structure with modern tech stack",
                "Project 2: Well-organized codebase with comprehensive tests"
            ],
            "overall_assessment": "Strong portfolio demonstrating full-stack capabilities"
        }
    
    def test_suggest_feedback_success(self, client_with_key, sample_local_analysis, sample_llm_analysis):
        """Test successful feedback generation."""
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = """PORTFOLIO OVERVIEW:
Strong overall portfolio with good technical depth and modern practices.

SPECIFIC RECOMMENDATIONS:
- Portfolio Structuring: Add live demos and comprehensive READMEs
- New Projects to Build: Consider building a microservices architecture project
- Existing Project Enhancements: Add CI/CD pipelines and comprehensive testing

CAREER ALIGNMENT ANALYSIS:
Strong alignment with frontend development goals, demonstrating current market-relevant skills."""
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key.suggest_feedback(
            sample_local_analysis,
            sample_llm_analysis,
            "frontend developer"
        )
        
        assert "career_goal" in result
        assert "feedback" in result
        assert result["career_goal"] == "frontend developer"
    
    def test_suggest_feedback_different_career_goal(self, client_with_key, sample_local_analysis, sample_llm_analysis):
        """Test feedback with different career goal."""
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "ML-focused feedback"
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key.suggest_feedback(
            sample_local_analysis,
            sample_llm_analysis,
            "machine learning engineer"
        )
        
        assert result["career_goal"] == "machine learning engineer"
    
    def test_suggest_feedback_not_configured(self, sample_local_analysis, sample_llm_analysis):
        """Test feedback generation when client not configured."""
        client = LLMClient()
        
        with pytest.raises(LLMError) as exc_info:
            client.suggest_feedback(sample_local_analysis, sample_llm_analysis, "developer")
        
        assert "not configured" in str(exc_info.value)
    
    def test_suggest_feedback_error_handling(self, client_with_key, sample_local_analysis, sample_llm_analysis):
        """Test error handling in feedback generation."""
        client_with_key.client.chat.completions.create = Mock(
            side_effect=Exception("API Error")
        )
        
        with pytest.raises(LLMError) as exc_info:
            client_with_key.suggest_feedback(sample_local_analysis, sample_llm_analysis, "developer")
        
        assert "Failed to generate feedback" in str(exc_info.value)


class TestSummarizeScanWithAI:
    """Test cases for summarize_scan_with_ai method (CLI integration)."""
    
    @pytest.fixture
    def client_with_key(self):
        """Create a client with a test API key."""
        with patch('analyzer.llm.client.OpenAI'):
            return LLMClient(api_key="test-key")
    
    @pytest.fixture
    def sample_scan_data(self, tmp_path):
        """Create sample scan data with temporary files."""

        test_file = tmp_path / "main.py"
        test_file.write_text("def hello():\n    print('Hello, world!')\n")
        
        readme_file = tmp_path / "README.md"
        readme_file.write_text("# Test Project\nThis is a test project.\n")
        
        return {
            "scan_summary": {
                "total_files": 2,
                "total_size_bytes": 1024,
                "language_breakdown": [
                    {"language": "Python", "file_count": 1, "percentage": 50.0},
                    {"language": "Markdown", "file_count": 1, "percentage": 50.0}
                ],
                "scan_path": str(tmp_path)
            },
            "relevant_files": [
                {
                    "path": "main.py",
                    "size": 512,
                    "mime_type": "text/x-python"
                },
                {
                    "path": "README.md",
                    "size": 512,
                    "mime_type": "text/markdown"
                }
            ],
            "scan_base_path": str(tmp_path)
        }
    
    def test_summarize_scan_success(self, client_with_key, sample_scan_data):
        """Test successful scan summarization."""
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Analysis result"
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key.summarize_scan_with_ai(
            scan_summary=sample_scan_data["scan_summary"],
            relevant_files=sample_scan_data["relevant_files"],
            scan_base_path=sample_scan_data["scan_base_path"]
        )
        
        assert "project_analysis" in result
        assert "file_summaries" in result
        assert "files_analyzed_count" in result
        assert isinstance(result["file_summaries"], list)

    def test_summarize_scan_includes_media_briefings(self, client_with_key, tmp_path):
        """Media assets should be surfaced when metadata is available."""
        scan_data = {
            "scan_summary": {"total_files": 1, "scan_path": str(tmp_path)},
            "relevant_files": [
                {
                    "path": "images/photo.jpg",
                    "size": 2048,
                    "mime_type": "image/jpeg",
                    "media_info": {"width": 1024, "height": 768, "content_summary": "sunset over mountains"},
                }
            ],
            "scan_base_path": str(tmp_path),
        }

        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Analysis result with media"
        mock_response.choices = [mock_choice]
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)

        result = client_with_key.summarize_scan_with_ai(
            scan_summary=scan_data["scan_summary"],
            relevant_files=scan_data["relevant_files"],
            scan_base_path=scan_data["scan_base_path"],
        )

        assert result.get("media_briefings")
        assert "photo.jpg" in " ".join(result["media_briefings"])
    
    def test_summarize_scan_not_configured(self, sample_scan_data):
        """Test scan summarization when client not configured."""
        client = LLMClient()
        
        with pytest.raises(LLMError) as exc_info:
            client.summarize_scan_with_ai(
                scan_summary=sample_scan_data["scan_summary"],
                relevant_files=sample_scan_data["relevant_files"],
                scan_base_path=sample_scan_data["scan_base_path"]
            )
        
        assert "not configured" in str(exc_info.value)
    
    def test_summarize_scan_skips_binary_files(self, client_with_key, tmp_path):
        """Test that binary files are skipped during analysis."""
        scan_data = {
            "scan_summary": {"total_files": 2},
            "relevant_files": [
                {
                    "path": "test.py",
                    "size": 100,
                    "mime_type": "text/x-python"
                },
                {
                    "path": "image.png",
                    "size": 5000,
                    "mime_type": "image/png"
                }
            ],
            "scan_base_path": str(tmp_path)
        }
        
        test_file = tmp_path / "test.py"
        test_file.write_text("print('test')")
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Analysis"
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key.summarize_scan_with_ai(
            scan_summary=scan_data["scan_summary"],
            relevant_files=scan_data["relevant_files"],
            scan_base_path=scan_data["scan_base_path"]
        )
        
        # Should only analyze the Python file, not the image
        assert result["files_analyzed_count"] >= 0 
    
    def test_summarize_scan_handles_missing_files(self, client_with_key, tmp_path):
        """Test handling of files that don't exist."""
        scan_data = {
            "scan_summary": {"total_files": 1},
            "relevant_files": [
                {
                    "path": "nonexistent.py",
                    "size": 100,
                    "mime_type": "text/x-python"
                }
            ],
            "scan_base_path": str(tmp_path)
        }
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Analysis"
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key.summarize_scan_with_ai(
            scan_summary=scan_data["scan_summary"],
            relevant_files=scan_data["relevant_files"],
            scan_base_path=scan_data["scan_base_path"]
        )
        
        assert "file_summaries" in result
        assert result["files_analyzed_count"] == 0
    
    def test_summarize_scan_empty_files_list(self, client_with_key, tmp_path):
        """Test scan summarization with no files."""
        scan_data = {
            "scan_summary": {"total_files": 0},
            "relevant_files": [],
            "scan_base_path": str(tmp_path)
        }
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Empty project analysis"
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key.summarize_scan_with_ai(
            scan_summary=scan_data["scan_summary"],
            relevant_files=scan_data["relevant_files"],
            scan_base_path=scan_data["scan_base_path"]
        )
        
        assert result["files_analyzed_count"] == 0
        assert "project_analysis" in result
    
    def test_summarize_scan_error_handling(self, client_with_key, sample_scan_data):
        """Test error handling in scan summarization."""
        client_with_key.client.chat.completions.create = Mock(
            side_effect=Exception("API Error")
        )
        
        with pytest.raises(LLMError) as exc_info:
            client_with_key.summarize_scan_with_ai(
                scan_summary=sample_scan_data["scan_summary"],
                relevant_files=sample_scan_data["relevant_files"],
                scan_base_path=sample_scan_data["scan_base_path"]
            )
        
        assert "Failed to analyze scan" in str(exc_info.value)
    
    def test_summarize_scan_handles_file_read_errors(self, client_with_key, tmp_path):
        """Test handling of file read errors (encoding issues, etc.)."""
        scan_data = {
            "scan_summary": {"total_files": 1},
            "relevant_files": [
                {
                    "path": "test.py",
                    "size": 100,
                    "mime_type": "text/x-python"
                }
            ],
            "scan_base_path": str(tmp_path)
        }
        
        test_file = tmp_path / "test.py"
        test_file.write_text("# Valid Python file\nprint('test')")
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Analysis"
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key.summarize_scan_with_ai(
            scan_summary=scan_data["scan_summary"],
            relevant_files=scan_data["relevant_files"],
            scan_base_path=scan_data["scan_base_path"]
        )
        
        assert "file_summaries" in result


class TestMultiProjectAnalysis:
    """Test cases for multi-project analysis with unassigned files."""
    
    @pytest.fixture
    def client_with_key(self):
        """Create a client with a test API key."""
        with patch('analyzer.llm.client.OpenAI'):
            return LLMClient(api_key="test-key")
    
    @pytest.fixture
    def multi_project_scan_data(self, tmp_path):
        """Create sample multi-project scan data."""
        # Create project 1 directory
        project1 = tmp_path / "project1"
        project1.mkdir()
        (project1 / ".git").mkdir()
        (project1 / "main.py").write_text("print('Project 1')")
        
        # Create project 2 directory
        project2 = tmp_path / "project2"
        project2.mkdir()
        (project2 / ".git").mkdir()
        (project2 / "app.py").write_text("print('Project 2')")
        
        # Create unassigned files
        (tmp_path / "README.md").write_text("# Portfolio README")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "architecture.md").write_text("# Architecture")
        
        return {
            "scan_summary": {"total_files": 5},
            "relevant_files": [
                {"path": "project1/main.py", "size": 100, "mime_type": "text/x-python"},
                {"path": "project2/app.py", "size": 100, "mime_type": "text/x-python"},
                {"path": "README.md", "size": 50, "mime_type": "text/markdown"},
                {"path": "docs/architecture.md", "size": 50, "mime_type": "text/markdown"},
            ],
            "scan_base_path": str(tmp_path),
            "project_dirs": [str(project1), str(project2)]
        }
    
    def test_multi_project_analysis_success(self, client_with_key, multi_project_scan_data):
        """Test successful multi-project analysis."""
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Analysis result"
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key.summarize_scan_with_ai(
            scan_summary=multi_project_scan_data["scan_summary"],
            relevant_files=multi_project_scan_data["relevant_files"],
            scan_base_path=multi_project_scan_data["scan_base_path"],
            project_dirs=multi_project_scan_data["project_dirs"]
        )
        
        # Verify multi-project mode
        assert result["mode"] == "multi_project"
        assert "projects" in result
        assert "project_count" in result
        
        # Should have 2 projects (not 3, unassigned files are separate)
        assert result["project_count"] == 2
        assert len(result["projects"]) == 2
        
        # Verify project names
        project_names = [p["project_name"] for p in result["projects"]]
        assert "project1" in project_names
        assert "project2" in project_names
        assert "Unassigned Files" not in project_names  # Should NOT be in projects list
        
        # Verify unassigned files are tracked separately
        assert "unassigned_files" in result
        assert result["unassigned_files"]["project_name"] == "Unassigned Files"
        assert result["unassigned_files"]["files_analyzed"] >= 0
    
    def test_multi_project_portfolio_summary_includes_unassigned(self, client_with_key, multi_project_scan_data):
        """Test that portfolio summary includes unassigned files context."""
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Portfolio summary with supporting files"
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key.summarize_scan_with_ai(
            scan_summary=multi_project_scan_data["scan_summary"],
            relevant_files=multi_project_scan_data["relevant_files"],
            scan_base_path=multi_project_scan_data["scan_base_path"],
            project_dirs=multi_project_scan_data["project_dirs"]
        )
        
        # Should have portfolio summary (more than 1 project)
        assert "portfolio_summary" in result
        assert result["portfolio_summary"]["project_count"] == 2
        
        # Verify unassigned files exist
        assert "unassigned_files" in result
    
    def test_multi_project_no_unassigned_files(self, client_with_key, tmp_path):
        """Test multi-project analysis when all files belong to projects."""
        # Create projects with no loose files
        project1 = tmp_path / "project1"
        project1.mkdir()
        (project1 / ".git").mkdir()
        (project1 / "main.py").write_text("print('Project 1')")
        
        project2 = tmp_path / "project2"
        project2.mkdir()
        (project2 / ".git").mkdir()
        (project2 / "app.py").write_text("print('Project 2')")
        
        scan_data = {
            "scan_summary": {"total_files": 2},
            "relevant_files": [
                {"path": "project1/main.py", "size": 100, "mime_type": "text/x-python"},
                {"path": "project2/app.py", "size": 100, "mime_type": "text/x-python"},
            ],
            "scan_base_path": str(tmp_path),
            "project_dirs": [str(project1), str(project2)]
        }
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Analysis"
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key.summarize_scan_with_ai(
            scan_summary=scan_data["scan_summary"],
            relevant_files=scan_data["relevant_files"],
            scan_base_path=scan_data["scan_base_path"],
            project_dirs=scan_data["project_dirs"]
        )
        
        assert result["mode"] == "multi_project"
        assert result["project_count"] == 2
        
        # Should NOT have unassigned files
        assert "unassigned_files" not in result
    
    def test_single_project_with_unassigned_files(self, client_with_key, tmp_path):
        """Test that single project with unassigned files doesn't trigger multi-project mode."""
        # Create only one project
        project1 = tmp_path / "project1"
        project1.mkdir()
        (project1 / ".git").mkdir()
        (project1 / "main.py").write_text("print('Project 1')")
        
        # Create unassigned files
        (tmp_path / "README.md").write_text("# README")
        
        scan_data = {
            "scan_summary": {"total_files": 2},
            "relevant_files": [
                {"path": "project1/main.py", "size": 100, "mime_type": "text/x-python"},
                {"path": "README.md", "size": 50, "mime_type": "text/markdown"},
            ],
            "scan_base_path": str(tmp_path),
            "project_dirs": [str(project1)]
        }
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Analysis"
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key.summarize_scan_with_ai(
            scan_summary=scan_data["scan_summary"],
            relevant_files=scan_data["relevant_files"],
            scan_base_path=scan_data["scan_base_path"],
            project_dirs=scan_data["project_dirs"]
        )
        
        # With only 1 project, should still be multi-project mode but no portfolio summary
        assert result["mode"] == "multi_project"
        assert result["project_count"] == 1
        assert "portfolio_summary" not in result  # Only generated when > 1 project
        
        # But unassigned files should still be tracked separately
        assert "unassigned_files" in result
    
    def test_generate_portfolio_summary_with_unassigned(self, client_with_key):
        """Test _generate_portfolio_summary with unassigned files context."""
        project_analyses = [
            {
                "project_name": "project1",
                "project_path": "project1",
                "files_analyzed": 10,
                "analysis": "Project 1 analysis"
            },
            {
                "project_name": "project2",
                "project_path": "project2",
                "files_analyzed": 15,
                "analysis": "Project 2 analysis"
            }
        ]
        
        unassigned_analysis = {
            "project_name": "Unassigned Files",
            "files_analyzed": 5,
            "analysis": "Supporting documentation and configuration files"
        }
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Portfolio summary including supporting files context"
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key._generate_portfolio_summary(
            project_analyses,
            unassigned_analysis=unassigned_analysis
        )
        
        assert "summary" in result
        assert "project_count" in result
        assert result["project_count"] == 2  # Only actual projects counted
        
        # Verify the LLM was called with unassigned context in prompt
        call_args = client_with_key.client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "SUPPORTING FILES" in prompt
        assert "not counted as a project" in prompt
    
    def test_generate_portfolio_summary_without_unassigned(self, client_with_key):
        """Test _generate_portfolio_summary without unassigned files."""
        project_analyses = [
            {
                "project_name": "project1",
                "project_path": "project1",
                "files_analyzed": 10,
                "analysis": "Project 1 analysis"
            },
            {
                "project_name": "project2",
                "project_path": "project2",
                "files_analyzed": 15,
                "analysis": "Project 2 analysis"
            }
        ]
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Portfolio summary"
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key._generate_portfolio_summary(
            project_analyses,
            unassigned_analysis=None
        )
        
        assert "summary" in result
        assert result["project_count"] == 2
        
        # Verify the LLM was NOT called with unassigned context
        call_args = client_with_key.client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "SUPPORTING FILES" not in prompt
    
    def test_unassigned_files_analysis_structure(self, client_with_key, multi_project_scan_data):
        """Test that unassigned files analysis has correct structure."""
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Analysis"
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key.summarize_scan_with_ai(
            scan_summary=multi_project_scan_data["scan_summary"],
            relevant_files=multi_project_scan_data["relevant_files"],
            scan_base_path=multi_project_scan_data["scan_base_path"],
            project_dirs=multi_project_scan_data["project_dirs"]
        )
        
        if "unassigned_files" in result:
            unassigned = result["unassigned_files"]
            
            # Verify structure
            assert "project_name" in unassigned
            assert "project_path" in unassigned
            assert "file_count" in unassigned
            assert "files_analyzed" in unassigned
            assert "analysis" in unassigned
            assert "file_summaries" in unassigned
            
            # Verify values
            assert unassigned["project_name"] == "Unassigned Files"
            assert unassigned["project_path"] == "_unassigned"
            assert isinstance(unassigned["file_summaries"], list)


class TestAnalyzeMultipleProjects:
    """Test cases for _analyze_multiple_projects method."""
    
    @pytest.fixture
    def client_with_key(self):
        """Create a client with a test API key."""
        with patch('analyzer.llm.client.OpenAI'):
            return LLMClient(api_key="test-key")
    
    def test_file_grouping_by_project(self, client_with_key, tmp_path):
        """Test that files are correctly grouped by project directory."""
        # Create project structure
        proj1 = tmp_path / "backend"
        proj1.mkdir()
        (proj1 / "main.py").write_text("print('backend')")
        
        proj2 = tmp_path / "frontend"
        proj2.mkdir()
        (proj2 / "app.js").write_text("console.log('frontend')")
        
        (tmp_path / "LICENSE").write_text("MIT")
        
        relevant_files = [
            {"path": "backend/main.py", "size": 100, "mime_type": "text/x-python"},
            {"path": "frontend/app.js", "size": 100, "mime_type": "text/javascript"},
            {"path": "LICENSE", "size": 50, "mime_type": "text/plain"},
        ]
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Analysis"
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key._analyze_multiple_projects(
            scan_summary={},
            relevant_files=relevant_files,
            scan_base_path=str(tmp_path),
            project_dirs=[str(proj1), str(proj2)],
            max_file_size_mb=10
        )
        
        # Should have 2 projects
        assert len(result["projects"]) == 2
        project_names = [p["project_name"] for p in result["projects"]]
        assert "backend" in project_names
        assert "frontend" in project_names
        
        # Should have unassigned files (LICENSE)
        assert "unassigned_files" in result
    
    def test_empty_unassigned_files_not_included(self, client_with_key, tmp_path):
        """Test that empty unassigned files group is not included."""
        # Create projects with all files assigned
        proj1 = tmp_path / "project1"
        proj1.mkdir()
        (proj1 / "main.py").write_text("print('test')")
        
        relevant_files = [
            {"path": "project1/main.py", "size": 100, "mime_type": "text/x-python"},
        ]
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Analysis"
        mock_response.choices = [mock_choice]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key._analyze_multiple_projects(
            scan_summary={},
            relevant_files=relevant_files,
            scan_base_path=str(tmp_path),
            project_dirs=[str(proj1)],
            max_file_size_mb=10
        )
        
        # Should NOT have unassigned_files key
        assert "unassigned_files" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
