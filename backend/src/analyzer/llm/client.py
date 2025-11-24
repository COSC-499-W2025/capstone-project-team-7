# LLM Client Module
# Handles integration with OpenAI API for analysis tasks

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
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
    
    DEFAULT_MODEL = "gpt-4o-mini"
    
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 4000
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """
        Initialize the LLM client.
        
        Args:
            api_key: OpenAI API key. If None, client operates in mock mode.
            temperature: Sampling temperature (0.0-2.0). Default 0.7 (recommended).
                        Lower = more focused/deterministic, higher = more creative/random.
            max_tokens: Maximum tokens in response. Default 1000 (recommended).
                       Higher values allow longer responses but cost more.
        """
        self.api_key = api_key
        self.client = None
        self.logger = logging.getLogger(__name__)
        
        self.temperature = temperature if temperature is not None else self.DEFAULT_TEMPERATURE
        self.max_tokens = max_tokens if max_tokens is not None else self.DEFAULT_MAX_TOKENS

        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        if self.max_tokens <= 0:
            raise ValueError("Max tokens must be positive")
        
        if api_key:
            try:
                self.client = OpenAI(api_key=api_key)
                self.logger.info(
                    f"LLM client initialized (model: {self.DEFAULT_MODEL}, "
                    f"temperature: {self.temperature}, max_tokens: {self.max_tokens})"
                )
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI client: {e}")
                raise LLMError(f"Failed to initialize LLM client: {str(e)}")
        else:
            self.logger.warning("LLM client initialized without API key (mock mode)")
    
    def set_temperature(self, temperature: float) -> None:
        """
        Update the temperature parameter for future API calls.
        
        Args:
            temperature: New temperature value (0.0-2.0)
                        0.0 = deterministic, 1.0 = balanced, 2.0 = very creative
        
        Raises:
            ValueError: If temperature is out of range
        """
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        self.temperature = temperature
        self.logger.info(f"Temperature updated to: {temperature}")
    
    def set_max_tokens(self, max_tokens: int) -> None:
        """
        Update the max tokens parameter for future API calls.
        
        Args:
            max_tokens: New max tokens value (must be positive)
        
        Raises:
            ValueError: If max_tokens is not positive
        """
        if max_tokens <= 0:
            raise ValueError("Max tokens must be positive")
        self.max_tokens = max_tokens
        self.logger.info(f"Max tokens updated to: {max_tokens}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get current client configuration.
        
        Returns:
            Dict with current model, temperature, and max_tokens settings
        """
        return {
            "model": self.DEFAULT_MODEL,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
    
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
                model=self.DEFAULT_MODEL,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            
            if response and response.choices:
                self.logger.info("API key verified successfully")
                return True
            
            raise LLMError("Unexpected response from API")
            
        except Exception as e:
            error_msg = str(e).lower()
            self.logger.error(f"Verification error: {e}")
            
            # Check error message content to determine error type
            if "authentication" in error_msg or "api key" in error_msg or "unauthorized" in error_msg:
                raise InvalidAPIKeyError("Invalid API key. Please verify your OpenAI API key is correct.")
            elif "rate limit" in error_msg or "quota" in error_msg:
                raise LLMError(f"Rate limit exceeded. Please check your API quota and try again: {str(e)}")
            elif "connection" in error_msg or "network" in error_msg:
                raise LLMError(f"Connection error. Please check your internet connection and try again: {str(e)}")
            elif "timeout" in error_msg:
                raise LLMError(f"Request timed out. Please check your internet connection and try again: {str(e)}")
            else:
                raise LLMError(f"Verification failed: {str(e)}")
    
    def is_configured(self) -> bool:
        """
        Check if the client is properly configured with an API key.
        
        Returns:
            bool: True if API key is set, False otherwise
        """
        return self.api_key is not None and self.client is not None
    
    def _count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """
        Count the number of tokens in a text string, default to character estimate.
        
        Args:
            text: Text to count tokens for
            model: Model name for tokenizer (defaults to DEFAULT_MODEL)
            
        Returns:
            int: Number of tokens
        """
        if model is None:
            model = self.DEFAULT_MODEL
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except Exception as e:
            self.logger.warning(f"Failed to count tokens: {e}. Using character estimate.")
            return len(text) // 4
    
    def _make_llm_call(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        max_tokens: Optional[int] = None, 
        temperature: Optional[float] = None
    ) -> str:
        """
        Make a call to the LLM API using configured defaults.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use
            max_tokens: Maximum tokens in response (defaults to self.max_tokens)
            temperature: Temperature for response generation (defaults to self.temperature)
            
        Returns:
            str: LLM response content
            
        Raises:
            LLMError: If API call fails
        """
        if not self.is_configured():
            raise LLMError("LLM client is not configured with an API key")
        
        model = model or self.DEFAULT_MODEL
        max_tokens = max_tokens if max_tokens is not None else self.max_tokens
        temperature = temperature if temperature is not None else self.temperature
        
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
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check error message content to determine error type
            if "authentication" in error_msg or "api key" in error_msg or "unauthorized" in error_msg:
                raise InvalidAPIKeyError("Invalid API key. Please verify your OpenAI API key is correct.")
            elif "rate limit" in error_msg or "quota" in error_msg:
                raise LLMError(f"Rate limit exceeded. Please wait a moment and try again, or check your API quota: {str(e)}")
            elif "connection" in error_msg or "network" in error_msg:
                raise LLMError(f"Connection error. Please check your internet connection and try again: {str(e)}")
            elif "timeout" in error_msg:
                raise LLMError(f"Request timed out. Please check your internet connection and try again: {str(e)}")
            else:
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
            encoding = tiktoken.encoding_for_model(self.DEFAULT_MODEL)
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
            
            prompt = f"""Analyze this {file_type} file and provide a brief structured summary.

File: {file_path}

Content:
{content_to_analyze}

Provide a concise analysis (max 100 words total) in this format:

SUMMARY: [2-3 sentences on what this file does]

KEY FUNCTIONALITY: [3-4 bullet points of main features]

NOTABLE PATTERNS: [1-2 notable techniques or patterns used]"""

            messages = [{"role": "user", "content": prompt}]
            response = self._make_llm_call(messages, max_tokens=150, temperature=0.6)
            
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
    
    def _run_async_in_thread(self, coro):
        """Run an async coroutine in a dedicated thread with its own event loop.
        
        This prevents conflicts with existing event loops and is safe to call
        from synchronous code.
        
        Args:
            coro: The coroutine to run
            
        Returns:
            The result of the coroutine
        """
        result = None
        exception = None
        
        def run_in_thread():
            nonlocal result, exception
            try:
                # Create a new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(coro)
                finally:
                    loop.close()
            except Exception as e:
                exception = e
        
        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join()
        
        if exception:
            raise exception
        return result
    
    async def _summarize_file_batch(self, files_batch: List[tuple], base_path) -> List[Dict[str, str]]:
        """Process a batch of files in parallel.
        
        Args:
            files_batch: List of (file_path, full_path, file_type) tuples
            base_path: Base path for file reading
            
        Returns:
            List of file summary results
        """
        
        async def analyze_single_file(file_info):
            file_path, full_path, file_type = file_info
            try:
                content = full_path.read_text(encoding='utf-8', errors='ignore')
                # Run the synchronous summarize in thread pool
                loop = asyncio.get_event_loop()
                summary_result = await loop.run_in_executor(
                    None,
                    self.summarize_tagged_file,
                    file_path,
                    content,
                    file_type
                )
                self.logger.info(f"Summarized: {file_path}")
                return summary_result
            except Exception as e:
                self.logger.error(f"Error analyzing {file_path}: {e}")
                return None
        
        # Process batch in parallel
        results = await asyncio.gather(*[analyze_single_file(f) for f in files_batch])
        return [r for r in results if r is not None]
    
    def summarize_scan_with_ai(self, scan_summary: Dict[str, Any], 
                               relevant_files: List[Dict[str, Any]],
                               scan_base_path: str,
                               max_file_size_mb: int = 10,
                               project_dirs: Optional[List[str]] = None,
                               progress_callback: Optional[Any] = None) -> Dict[str, Any]:
        """
        Comprehensive AI analysis workflow for CLI integration.
        
        Args:
            scan_summary: Dict with file_count, total_size, language_breakdown, etc.
            relevant_files: List of file metadata dicts (path, size, mime_type, etc.)
            scan_base_path: Base path where original files are located for reading content
            max_file_size_mb: Maximum file size in MB to process (default: 10MB)
            project_dirs: Optional list of project directory paths (e.g., Git repo roots).
                         If provided, files are grouped by project and analyzed separately.
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dict containing:
                - project_analysis: Result from analyze_project() (single project mode)
                - projects: List of per-project analyses (multi-project mode)
                - file_summaries: List of results from summarize_tagged_file()
                - summary_text: Combined formatted output for display
                - skipped_files: List of files skipped due to size limits
                
        Raises:
            LLMError: If analysis fails
        """
        if not self.is_configured():
            raise LLMError("LLM client is not configured")
        
        try:
            from pathlib import Path
            
            self.logger.info("Starting LLM analysis")
            
            if progress_callback:
                progress_callback(f"Initializing analysis for {len(relevant_files)} files…")
            
            if project_dirs:
                self.logger.info(f"Multi-project mode: {len(project_dirs)} projects")
                if progress_callback:
                    progress_callback(f"Multi-project mode: analyzing {len(project_dirs)} projects…")
                return self._analyze_multiple_projects(
                    scan_summary=scan_summary,
                    relevant_files=relevant_files,
                    scan_base_path=scan_base_path,
                    project_dirs=project_dirs,
                    max_file_size_mb=max_file_size_mb,
                    progress_callback=progress_callback,
                )
            
            max_file_size_bytes = max_file_size_mb * 1024 * 1024
            file_summaries = []
            skipped_files = []
            
            total_files = len(relevant_files)
            
            # Prepare files for batch processing
            files_to_analyze = []
            for file_meta in relevant_files:
                file_path = file_meta.get('path', '')
                if not file_path:
                    continue

                full_path = Path(scan_base_path) / file_path

                if full_path.exists() and full_path.is_file():
                    file_size = full_path.stat().st_size
                    if file_size > max_file_size_bytes:
                        self.logger.warning(f"Skipping large file ({file_size / (1024*1024):.2f}MB): {file_path}")
                        skipped_files.append({
                            'path': file_path,
                            'size_mb': file_size / (1024 * 1024),
                            'reason': f'Exceeds maximum file size limit of {max_file_size_mb}MB'
                        })
                        continue

                mime_type = file_meta.get('mime_type', '')
                if not (mime_type.startswith('text/') or 
                       mime_type in ['application/json', 'application/xml', 'application/javascript']):
                    self.logger.info(f"Skipping non-text file: {file_path}")
                    continue
                
                if full_path.exists() and full_path.is_file():
                    file_type = full_path.suffix or 'unknown'
                    files_to_analyze.append((file_path, full_path, file_type))
            
            # Process files in batches of 5 for parallel execution
            BATCH_SIZE = 5
            processed_count = 0
            
            for i in range(0, len(files_to_analyze), BATCH_SIZE):
                batch = files_to_analyze[i:i + BATCH_SIZE]
                batch_num = (i // BATCH_SIZE) + 1
                total_batches = (len(files_to_analyze) + BATCH_SIZE - 1) // BATCH_SIZE
                
                if progress_callback:
                    progress_callback(f"Single-project: Batch {batch_num}/{total_batches} ({len(batch)} files)…")
                
                try:
                    # Process batch in parallel using dedicated thread
                    batch_results = self._run_async_in_thread(
                        self._summarize_file_batch(batch, scan_base_path)
                    )
                    file_summaries.extend(batch_results)
                    processed_count += len(batch_results)
                    
                    if progress_callback:
                        progress_callback(f"Single-project: Completed {processed_count}/{len(files_to_analyze)} files…")
                except Exception as e:
                    self.logger.error(f"Error processing batch: {e}")
                    continue
            
            if progress_callback:
                progress_callback("Generating project insights…")
            
            project_analysis = self.analyze_project(
                local_analysis=scan_summary,
                tagged_files_summaries=file_summaries
            )
            
            result = {
                "project_analysis": project_analysis,
                "file_summaries": file_summaries,
                "files_analyzed_count": len(file_summaries)
            }
            
            if skipped_files:
                result["skipped_files"] = skipped_files
                self.logger.info(f"Skipped {len(skipped_files)} files due to size limits")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Scan AI analysis failed: {e}")
            raise LLMError(f"Failed to analyze scan: {str(e)}")
    
    def _analyze_multiple_projects(self, scan_summary: Dict[str, Any],
                                   relevant_files: List[Dict[str, Any]],
                                   scan_base_path: str,
                                   project_dirs: List[str],
                                   max_file_size_mb: int = 10,
                                   progress_callback: Optional[Any] = None) -> Dict[str, Any]:
        """
        Analyze multiple projects separately (e.g., multiple Git repos in one scan).
        
        Args:
            scan_summary: Global scan summary
            relevant_files: All files from scan
            scan_base_path: Base path for file reading
            project_dirs: List of project root directories (e.g., Git repo paths)
            max_file_size_mb: Max file size to process
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict with per-project analyses and overall summary
        """
        from pathlib import Path
        
        self.logger.info(f"Analyzing {len(project_dirs)} separate projects")
        
        if progress_callback:
            progress_callback(f"Grouping files across {len(project_dirs)} projects…")
        
        max_file_size_bytes = max_file_size_mb * 1024 * 1024
        base_path = Path(scan_base_path)
        
        # Normalize project dirs to relative paths
        project_dirs_normalized = []
        for proj_dir in project_dirs:
            proj_path = Path(proj_dir)
            
            try:
                # Make paths relative to base_path
                rel_path = proj_path.relative_to(base_path)
                normalized = str(rel_path)
                project_dirs_normalized.append(normalized)
                self.logger.info(f"Normalized project path: {proj_dir} -> {normalized}")
            except ValueError:
                # Not relative to base_path, skip
                self.logger.warning(f"Project path {proj_dir} is not under base_path {base_path}, skipping")
                continue
        
        files_by_project = {proj: [] for proj in project_dirs_normalized}
        files_by_project['_unassigned'] = [] 
        
        self.logger.info(f"Starting file grouping. Projects: {project_dirs_normalized}")
        self.logger.info(f"Sample file paths (first 5): {[f.get('path', '') for f in relevant_files[:5]]}")
        
        import os
        debug_log_path = os.path.expanduser("~/.textual_ai_debug.log")
        with open(debug_log_path, "a") as f:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            f.write(f"{timestamp} | [LLM Client] Projects normalized: {project_dirs_normalized}\n")
            f.write(f"{timestamp} | [LLM Client] Sample files: {[f.get('path', '') for f in relevant_files[:5]]}\n")
            f.write(f"{timestamp} | [LLM Client] Total files to group: {len(relevant_files)}\n")
        
        for file_meta in relevant_files:
            file_path = file_meta.get('path', '')
            if not file_path:
                continue
            
            assigned = False
            for proj_dir in project_dirs_normalized:
                # Special case: "." means this is the root project (project path == base path)
                # In this case, all files belong to this project
                if proj_dir == ".":
                    files_by_project[proj_dir].append(file_meta)
                    assigned = True
                    break
                # Check if file path starts with project directory
                elif file_path.startswith(proj_dir + '/') or file_path.startswith(proj_dir + '\\'):
                    files_by_project[proj_dir].append(file_meta)
                    assigned = True
                    break
            
            if not assigned:
                files_by_project['_unassigned'].append(file_meta)
        
        # Log file grouping results
        for proj_dir, proj_files in files_by_project.items():
            self.logger.info(f"Project '{proj_dir}': {len(proj_files)} files")
        
        with open(debug_log_path, "a") as f:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            for proj_dir, proj_files in files_by_project.items():
                f.write(f"{timestamp} | [LLM Client] Project '{proj_dir}': {len(proj_files)} files\n")
        
        project_analyses = []
        all_file_summaries = []
        all_skipped_files = []
        unassigned_analysis = None  # Track unassigned files separately
        
        project_index = 0
        total_projects = len([p for p in files_by_project.keys() if p != '_unassigned' and files_by_project[p]])
        
        for proj_dir, proj_files in files_by_project.items():
            if proj_dir == '_unassigned':
                if not proj_files:
                    continue
                proj_name = "Unassigned Files"
            else:
                proj_name = Path(proj_dir).name or proj_dir
            
            if not proj_files:
                self.logger.info(f"Skipping empty project: {proj_name}")
                continue
            
            if proj_dir != '_unassigned':
                project_index += 1
                if progress_callback:
                    progress_callback(f"Multi-project [{project_index}/{total_projects}]: {proj_name}…")
            
            self.logger.info(f"Analyzing project '{proj_name}' ({len(proj_files)} files)")
            
            # Prepare files for batch processing
            file_summaries = []
            skipped_files = []
            files_to_analyze = []
            
            for file_meta in proj_files:
                file_path = file_meta.get('path', '')
                full_path = base_path / file_path
                
                if not full_path.exists() or not full_path.is_file():
                    self.logger.warning(f"File not found: {full_path}")
                    continue
                
                file_size = full_path.stat().st_size
                if file_size > max_file_size_bytes:
                    skipped_files.append({
                        'path': file_path,
                        'size_mb': file_size / (1024 * 1024),
                        'reason': f'Exceeds {max_file_size_mb}MB limit'
                    })
                    continue
                
                # Skip lock files and other non-essential files
                if any(skip in file_path.lower() for skip in ['package-lock.json', 'yarn.lock', 'poetry.lock', '.lock']):
                    self.logger.info(f"[{proj_name}] Skipping lock file: {file_path}")
                    continue
                
                mime_type = file_meta.get('mime_type', '')
                if not (mime_type.startswith('text/') or 
                       mime_type in ['application/json', 'application/xml', 'application/javascript']):
                    continue
                
                file_type = full_path.suffix or 'unknown'
                files_to_analyze.append((file_path, full_path, file_type))
            
            # Process files in batches of 5 for parallel execution
            BATCH_SIZE = 5
            processed_count = 0
            
            for i in range(0, len(files_to_analyze), BATCH_SIZE):
                batch = files_to_analyze[i:i + BATCH_SIZE]
                batch_num = (i // BATCH_SIZE) + 1
                total_batches = (len(files_to_analyze) + BATCH_SIZE - 1) // BATCH_SIZE
                
                if progress_callback:
                    if proj_dir != '_unassigned':
                        progress_callback(f"Project {project_index}/{total_projects} - Batch {batch_num}/{total_batches} ({len(batch)} files)…")
                    else:
                        progress_callback(f"[{proj_name}] Batch {batch_num}/{total_batches} ({len(batch)} files)…")
                
                try:
                    # Process batch in parallel using dedicated thread
                    batch_results = self._run_async_in_thread(
                        self._summarize_file_batch(batch, base_path)
                    )
                    file_summaries.extend(batch_results)
                    processed_count += len(batch_results)
                    
                    if progress_callback:
                        progress_callback(f"[{proj_name}] Completed {processed_count}/{len(files_to_analyze)} files…")
                except Exception as e:
                    self.logger.error(f"[{proj_name}] Error processing batch: {e}")
                    continue
            
            project_summary = {
                "project_name": proj_name,
                "project_path": proj_dir,
                "total_files": len(proj_files),
                "files_analyzed": len(file_summaries),
                "total_size_bytes": sum(f.get('size', 0) for f in proj_files)
            }
            
            if file_summaries:
                project_analysis = self.analyze_project(
                    local_analysis=project_summary,
                    tagged_files_summaries=file_summaries
                )
                
                analysis_result = {
                    "project_name": proj_name,
                    "project_path": proj_dir,
                    "file_count": len(proj_files),
                    "files_analyzed": len(file_summaries),
                    "analysis": project_analysis.get("analysis", ""),
                    "file_summaries": file_summaries
                }
                
                if proj_dir == '_unassigned':
                    unassigned_analysis = analysis_result
                    self.logger.info(f"Stored unassigned files analysis separately (not counted as project)")
                else:
                    project_analyses.append(analysis_result)
            
            all_file_summaries.extend(file_summaries)
            all_skipped_files.extend(skipped_files)
        
        portfolio_summary = None
        if len(project_analyses) > 1:
            portfolio_summary = self._generate_portfolio_summary(
                project_analyses, 
                unassigned_analysis=unassigned_analysis
            )
        
        result = {
            "mode": "multi_project",
            "projects": project_analyses,
            "project_count": len(project_analyses),
            "total_files_analyzed": len(all_file_summaries),
            "file_summaries": all_file_summaries,
            "files_analyzed_count": len(all_file_summaries)
        }
        
        if portfolio_summary:
            result["portfolio_summary"] = portfolio_summary
        
        # Include unassigned files as additional context (not a project)
        if unassigned_analysis:
            result["unassigned_files"] = unassigned_analysis
        
        if all_skipped_files:
            result["skipped_files"] = all_skipped_files
            self.logger.info(f"Skipped {len(all_skipped_files)} files across all projects")
        
        return result
    
    def _generate_portfolio_summary(self, project_analyses: List[Dict[str, Any]], 
                                    unassigned_analysis: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Generate a high-level portfolio summary from multiple project analyses.
        
        Args:
            project_analyses: List of individual project analysis results
            unassigned_analysis: Optional analysis of unassigned files (supporting docs, etc.)
            
        Returns:
            Dict with portfolio-level summary
        """
        if not self.is_configured():
            raise LLMError("LLM client is not configured")
        
        try:
            projects_overview = "\n\n".join([
                f"PROJECT: {p['project_name']}\n"
                f"Path: {p.get('project_path', 'N/A')}\n"
                f"Files analyzed: {p['files_analyzed']}\n"
                f"Analysis:\n{p['analysis']}"
                for p in project_analyses
            ])
            
            unassigned_context = ""
            if unassigned_analysis:
                unassigned_context = f"""

SUPPORTING FILES (not counted as a project):
Files analyzed: {unassigned_analysis['files_analyzed']}
These are documentation, configuration, and other supporting files found outside the main project directories.
Analysis:
{unassigned_analysis['analysis']}"""
            
            prompt = f"""You are reviewing a developer's portfolio containing {len(project_analyses)} separate projects.

INDIVIDUAL PROJECT ANALYSES:
{projects_overview}{unassigned_context}

Create a comprehensive PORTFOLIO-LEVEL summary in the following format:

PORTFOLIO OVERVIEW:
[2-3 sentences capturing the overall breadth and depth of the portfolio, highlighting the variety of projects and technologies]

KEY STRENGTHS:
[Main strengths demonstrated across projects - technical diversity, depth in certain areas, etc.]

TECHNICAL BREADTH:
[Summary of the range of technologies, frameworks, and domains covered across all projects]

STANDOUT PROJECTS:
[Identify 2-3 most impressive or notable projects and why they stand out]

PORTFOLIO COHERENCE:
[How well the projects work together to tell a cohesive story about the developer's skills and interests]"""

            messages = [{"role": "user", "content": prompt}]
            response = self._make_llm_call(messages, max_tokens=800, temperature=0.7)
            
            return {
                "summary": response,
                "project_count": len(project_analyses)
            }
            
        except Exception as e:
            self.logger.error(f"Portfolio summary generation failed: {e}")
            raise LLMError(f"Failed to generate portfolio summary: {str(e)}")
