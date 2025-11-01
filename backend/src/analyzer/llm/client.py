# LLM Client Module
# Handles integration with OpenAI API for analysis tasks

import logging
from typing import Optional, Dict, List, Any
import openai
from openai import OpenAI
import tiktoken


logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when LLM operations fail."""
    pass


class InvalidAPIKeyError(Exception):
    """Raised when API key is invalid or missing."""
    pass


class LLMClient:
    """
    Client for interacting with OpenAI's API.
    
    This class provides a foundation for LLM-based analysis operations.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the LLM client.
        
        Args:
            api_key: OpenAI API key. If None, client operates in mock mode.
        """
        self.api_key = api_key
        self.client = None
        self.logger = logging.getLogger(__name__)
        
        if api_key:
            try:
                self.client = OpenAI(api_key=api_key)
                self.logger.info("LLM client initialized with API key")
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI client: {e}")
                raise LLMError(f"Failed to initialize LLM client: {str(e)}")
        else:
            self.logger.warning("LLM client initialized without API key (mock mode)")
    
    def verify_api_key(self) -> bool:
        """
        Verify that the API key is valid by making a test request.
        
        Returns:
            bool: True if API key is valid, False otherwise
            
        Raises:
            InvalidAPIKeyError: If API key is missing or invalid
            LLMError: If verification fails due to other reasons
        """
        if not self.api_key:
            raise InvalidAPIKeyError("No API key provided")
        
        if not self.client:
            raise InvalidAPIKeyError("LLM client not initialized")
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            
            if response and response.choices:
                self.logger.info("API key verified successfully")
                return True
            
            raise LLMError("Unexpected response from API")
            
        except openai.AuthenticationError as e:
            self.logger.error(f"Authentication failed: {e}")
            raise InvalidAPIKeyError("Invalid API key")
        except openai.APIError as e:
            self.logger.error(f"API error during verification: {e}")
            raise LLMError(f"API error: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error during verification: {e}")
            raise LLMError(f"Verification failed: {str(e)}")
    
    def is_configured(self) -> bool:
        """
        Check if the client is properly configured with an API key.
        
        Returns:
            bool: True if API key is set, False otherwise
        """
        return self.api_key is not None and self.client is not None
    
    def _count_tokens(self, text: str, model: str = "gpt-3.5-turbo") -> int:
        """
        Count the number of tokens in a text string, default to character estimate.
        
        Args:
            text: Text to count tokens for
            model: Model name for tokenizer
            
        Returns:
            int: Number of tokens
        """
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except Exception as e:
            self.logger.warning(f"Failed to count tokens: {e}. Using character estimate.")
            return len(text) // 4
    
    def _make_llm_call(self, messages: List[Dict[str, str]], model: str = "gpt-3.5-turbo", 
                       max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """
        Make a call to the LLM API.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use
            max_tokens: Maximum tokens in response
            temperature: Temperature for response generation
            
        Returns:
            str: LLM response content
            
        Raises:
            LLMError: If API call fails
        """
        if not self.is_configured():
            raise LLMError("LLM client is not configured with an API key")
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            if response and response.choices:
                return response.choices[0].message.content.strip()
            
            raise LLMError("Empty response from API")
            
        except openai.AuthenticationError as e:
            raise InvalidAPIKeyError("Invalid API key")
        except openai.APIError as e:
            raise LLMError(f"API error: {str(e)}")
        except Exception as e:
            raise LLMError(f"LLM call failed: {str(e)}")
    
    def chunk_and_summarize(self, text: str, file_type: str = "", 
                           chunk_size: int = 2000, overlap: int = 100) -> Dict[str, Any]:
        """
        Handle large text files by splitting into chunks, summarizing each, then merging.
        
        Args:
            text: Large text content to summarize
            file_type: File type/extension for context
            chunk_size: Maximum tokens per chunk (default: 2000)
            overlap: Token overlap between chunks for context (default: 100)
            
        Returns:
            Dict containing:
                - final_summary: Merged summary
                - num_chunks: Number of chunks processed
                - chunk_summaries: List of individual chunk summaries
                
        Raises:
            LLMError: If summarization fails
        """
        if not self.is_configured():
            raise LLMError("LLM client is not configured")
        
        try:
            encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
            tokens = encoding.encode(text)
            chunks = []
            
            i = 0
            while i < len(tokens):
                chunk_tokens = tokens[i:i + chunk_size]
                chunk_text = encoding.decode(chunk_tokens)
                chunks.append(chunk_text)
                i += chunk_size - overlap
            
            self.logger.info(f"Split text into {len(chunks)} chunks")
            
            chunk_summaries = []
            for idx, chunk in enumerate(chunks):
                prompt = f"""Summarize this section of a {file_type} file. Focus on key functionality and important details.
                
                Section {idx + 1}/{len(chunks)}:
                {chunk}

                Provide a concise summary of this section."""

                messages = [{"role": "user", "content": prompt}]
                summary = self._make_llm_call(messages, max_tokens=300, temperature=0.5)
                chunk_summaries.append(summary)
            
            merge_prompt = f"""You are reviewing summaries of different sections of a {file_type} file.
            Create a coherent, comprehensive summary that captures the overall purpose and key functionality.

            Section summaries:
            {chr(10).join(f"{i+1}. {s}" for i, s in enumerate(chunk_summaries))}

            Provide a unified summary (100-200 words) that captures the essence of the entire file."""

            messages = [{"role": "user", "content": merge_prompt}]
            final_summary = self._make_llm_call(messages, max_tokens=400, temperature=0.5)
            
            return {
                "final_summary": final_summary,
                "num_chunks": len(chunks),
                "chunk_summaries": chunk_summaries
            }
            
        except Exception as e:
            self.logger.error(f"Chunk and summarize failed: {e}")
            raise LLMError(f"Failed to chunk and summarize: {str(e)}")
    
    def summarize_tagged_file(self, file_path: str, content: str, file_type: str) -> Dict[str, str]:
        """
        Create a detailed summary of a user-tagged important file.
        Automatically handles large files through chunking.
        
        Args:
            file_path: Path to the file
            content: Full file content
            file_type: File extension/type
            
        Returns:
            Formatted text output containing:
                - summary: Concise summary (80-150 words)
                - key_functionality: Key functionality and purpose
                - notable_patterns: Notable patterns or techniques
                
        Raises:
            LLMError: If summarization fails
        """
        if not self.is_configured():
            raise LLMError("LLM client is not configured")
        
        try:
            token_count = self._count_tokens(content)
            self.logger.info(f"Summarizing {file_path} ({token_count} tokens)")
            
            if token_count > 2000:
                chunk_result = self.chunk_and_summarize(content, file_type)
                content_to_analyze = chunk_result["final_summary"]
            else:
                content_to_analyze = content
            
            prompt = f"""Analyze this {file_type} file and provide a structured summary.

            File: {file_path}

            Content:
            {content_to_analyze}

            Provide your analysis in the following format:

            SUMMARY:
            [Concise 80-150 word summary of what this file does]

            KEY FUNCTIONALITY:
            [Main features and purpose of this file]

            NOTABLE PATTERNS:
            [Any interesting techniques, patterns, or approaches used]"""

            messages = [{"role": "user", "content": prompt}]
            response = self._make_llm_call(messages, max_tokens=500, temperature=0.6)
            
            return {
                "file_path": file_path,
                "file_type": file_type,
                "analysis": response
            }
            
        except Exception as e:
            self.logger.error(f"Failed to summarize tagged file: {e}")
            raise LLMError(f"File summarization failed: {str(e)}")
    
    def analyze_project(self, local_analysis: Dict[str, Any],
                       tagged_files_summaries: List[Dict[str, str]]) -> Dict[str, str]:
        """
        Generate a comprehensive, resume-friendly project report.
        
        Args:
            local_analysis: Dict with stats, metrics, file_counts
            tagged_files_summaries: List of summaries from summarize_tagged_file()
            
        Returns:
            Dict containing:
                - analysis result: Formatted output text
                
        Raises:
            LLMError: If analysis fails
        """
        if not self.is_configured():
            raise LLMError("LLM client is not configured")
        
        try:
            files_info = "\n\n".join([
                f"File: {f.get('file_path', 'Unknown')}\n{f.get('analysis', '')}"
                for f in tagged_files_summaries
            ])
            
            prompt = f"""You are analyzing a software project to create a professional, resume-worthy report.

            LOCAL ANALYSIS RESULTS:
            {local_analysis}

            IMPORTANT FILES ANALYSIS:
            {files_info if files_info else 'No tagged files provided'}

            Create a comprehensive analysis in the following format:

            EXECUTIVE SUMMARY:
            [2-3 sentences capturing the project's essence and main value proposition]

            TECHNICAL HIGHLIGHTS:
            [Key features, capabilities, and technical achievements in bullet points]

            TECHNOLOGIES USED:
            [Summary of the tech stack and how technologies are used]

            PROJECT QUALITY:
            [Assessment of completeness, production-readiness, code quality, and overall maturity]"""

            messages = [{"role": "user", "content": prompt}]
            response = self._make_llm_call(messages, max_tokens=800, temperature=0.7)
            
            return {
                "analysis": response
            }
            
        except Exception as e:
            self.logger.error(f"Project analysis failed: {e}")
            raise LLMError(f"Failed to analyze project: {str(e)}")
    
    def suggest_feedback(self, local_analysis: Dict[str, Any],
                        llm_analysis: Dict[str, Any],
                        career_goal: str) -> Dict[str, str]:
        """
        Generate personalized, actionable recommendations for entire portfolio
        improvements and career development.
        
        Args:
            local_analysis: Local analysis results for the entire portfolio
            llm_analysis: LLM analysis results for the entire portfolio
            career_goal: User's career goal (e.g., "frontend developer")
            
        Returns:
            Formatted text output containing:
                - portfolio_overview: Overall assessment with strengths and improvements
                - specific_recommendations: Portfolio structuring, new projects, and existing project enhancements
                - career_alignment_analysis: Market-aligned analysis of portfolio fit for career goal
                
        Raises:
            LLMError: If feedback generation fails
        """
        if not self.is_configured():
            raise LLMError("LLM client is not configured")
        
        try:
            prompt = f"""You are an experienced senior software engineer and career mentor. Provide personalized feedback for a developer based on their entire portfolio.

            CAREER GOAL: {career_goal}

            LOCAL ANALYSIS RESULTS:
            {local_analysis}

            LLM ANALYSIS RESULTS:
            {llm_analysis}

            Provide actionable feedback in the following format:

            PORTFOLIO OVERVIEW:
            [Provide an overall assessment of the portfolio's current state, highlighting strengths and areas for improvement. Include specific suggestions on current industry trends, best practices, and features that would make the portfolio more impressive and professional.]

            SPECIFIC RECOMMENDATIONS:
            - Portfolio Structuring: [Advice on how to organize, present, and document the portfolio effectively]
            - New Projects to Build: [Specific project ideas that would complement the existing portfolio and align with the career goal]
            - Existing Project Enhancements: [Actionable suggestions for improving or building upon current projects - new features, refactoring, testing, deployment, etc.]

            CAREER ALIGNMENT ANALYSIS:
            [Analyze how well the portfolio aligns with the career goal in the context of current market trends and industry requirements for {career_goal} positions. 
            Address: what skills are demonstrated, what's missing based on current job market demands, what technologies or practices are trending in this field, and 
            what specific steps to take next to be competitive in today's job market]"""

            messages = [{"role": "user", "content": prompt}]
            response = self._make_llm_call(messages, max_tokens=800, temperature=0.7)
            
            return {
                "career_goal": career_goal,
                "feedback": response
            }
            
        except Exception as e:
            self.logger.error(f"Feedback generation failed: {e}")
            raise LLMError(f"Failed to generate feedback: {str(e)}")
    
    def summarize_scan_with_ai(self, scan_summary: Dict[str, Any], 
                               relevant_files: List[Dict[str, Any]],
                               scan_base_path: str) -> Dict[str, Any]:
        """
        Comprehensive AI analysis workflow for CLI integration.
        
        Args:
            scan_summary: Dict with file_count, total_size, language_breakdown, etc.
            relevant_files: List of file metadata dicts (path, size, mime_type, etc.)
            scan_base_path: Base path where original files are located for reading content
            
        Returns:
            Dict containing:
                - project_analysis: Result from analyze_project()
                - file_summaries: List of results from summarize_tagged_file()
                - summary_text: Combined formatted output for display
                
        Raises:
            LLMError: If analysis fails
        """
        if not self.is_configured():
            raise LLMError("LLM client is not configured")
        
        try:
            self.logger.info("Starting LLM analysis")
            
            file_summaries = []
            for file_meta in relevant_files:
                file_path = file_meta.get('path', '')
                if not file_path:
                    continue

                from pathlib import Path
                full_path = Path(scan_base_path) / file_path

                mime_type = file_meta.get('mime_type', '')
                if not (mime_type.startswith('text/') or 
                       mime_type in ['application/json', 'application/xml', 'application/javascript']):
                    self.logger.info(f"Skipping non-text file: {file_path}")
                    continue
                
                try:
                    if full_path.exists() and full_path.is_file():
                        content = full_path.read_text(encoding='utf-8', errors='ignore')
                        file_type = full_path.suffix or 'unknown'
                        
                        summary_result = self.summarize_tagged_file(file_path, content, file_type)
                        file_summaries.append(summary_result)
                        self.logger.info(f"Summarized: {file_path}")
                    else:
                        self.logger.warning(f"File not found: {full_path}")
                except Exception as e:
                    self.logger.error(f"Error reading/summarizing {file_path}: {e}")
                    continue
            
            project_analysis = self.analyze_project(
                local_analysis=scan_summary,
                tagged_files_summaries=file_summaries
            )
            
            return {
                "project_analysis": project_analysis,
                "file_summaries": file_summaries,
                "files_analyzed_count": len(file_summaries)
            }
            
        except Exception as e:
            self.logger.error(f"Scan AI analysis failed: {e}")
            raise LLMError(f"Failed to analyze scan: {str(e)}")
