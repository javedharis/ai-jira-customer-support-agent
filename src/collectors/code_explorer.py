"""
Codebase explorer using Claude CLI for analyzing code related to customer support issues
"""

import logging
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from pathlib import Path
import subprocess

from ..core.config import CodebaseConfig, ClaudeConfig


@dataclass
class CodeAnalysisResult:
    search_term: str
    analysis_summary: str
    relevant_files: List[str]
    code_insights: str
    potential_issues: List[str]
    recommended_fixes: List[str]
    confidence_score: float


class CodebaseExplorer:
    """Uses Claude CLI to explore codebase for patterns related to customer issues"""
    
    def __init__(self, codebase_config: CodebaseConfig, claude_config: ClaudeConfig):
        self.codebase_config = codebase_config
        self.claude_config = claude_config
        self.logger = logging.getLogger(__name__)
        self.repo_path = Path(codebase_config.repo_path)
        
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {codebase_config.repo_path}")
    
    async def search_codebase(self, search_terms: List[str], files_to_check: Optional[List[str]] = None) -> Dict[str, CodeAnalysisResult]:
        """Search codebase using Claude CLI for relevant code patterns"""
        
        self.logger.info(f"Using Claude CLI to search codebase for terms: {search_terms}")
        
        results = {}
        
        for term in search_terms:
            try:
                analysis = await self._analyze_with_claude(term, files_to_check)
                results[term] = analysis
            except Exception as e:
                self.logger.error(f"Failed to analyze term '{term}' with Claude CLI: {str(e)}")
                results[term] = CodeAnalysisResult(
                    search_term=term,
                    analysis_summary=f"Analysis failed: {str(e)}",
                    relevant_files=[],
                    code_insights="",
                    potential_issues=[],
                    recommended_fixes=[],
                    confidence_score=0.0
                )
        
        return results
    
    async def _analyze_with_claude(self, search_term: str, files_to_check: Optional[List[str]]) -> CodeAnalysisResult:
        """Use Claude CLI to analyze code patterns for a search term"""
        
        # Build the Claude CLI prompt
        prompt = self._build_analysis_prompt(search_term, files_to_check)
        
        try:
            # Execute Claude CLI
            process = await asyncio.create_subprocess_exec(
                self.claude_config.cli_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.repo_path
            )
            
            stdout, stderr = await process.communicate(prompt.encode())
            
            if process.returncode != 0:
                raise Exception(f"Claude CLI failed: {stderr.decode()}")
            
            # Parse Claude's response
            response = stdout.decode()
            
            return self._parse_claude_response(search_term, response)
            
        except Exception as e:
            self.logger.error(f"Claude CLI execution failed for '{search_term}': {str(e)}")
            raise
    
    def _build_analysis_prompt(self, search_term: str, files_to_check: Optional[List[str]]) -> str:
        """Build the prompt for Claude CLI code analysis"""
        
        prompt = f"""You are analyzing a codebase to understand issues related to the term: "{search_term}"

Please analyze the codebase and provide insights in JSON format:

{{
    "analysis_summary": "Brief summary of what you found related to the search term",
    "relevant_files": ["list of files that are most relevant to this term"],
    "code_insights": "Detailed insights about how this term is used in the code",
    "potential_issues": ["list of potential issues or bugs you identified"],
    "recommended_fixes": ["list of specific recommendations to address issues"],
    "confidence_score": 0.85
}}

Focus on:
1. Finding where "{search_term}" appears in the code
2. Understanding the context and functionality
3. Identifying potential bugs or issues
4. Suggesting specific fixes or improvements

"""
        
        if files_to_check:
            prompt += f"\nPay special attention to these files: {', '.join(files_to_check)}\n"
        
        prompt += """
Please search the codebase thoroughly and provide actionable insights that would help resolve customer support issues related to this term.
"""
        
        return prompt
    
    def _parse_claude_response(self, search_term: str, response: str) -> CodeAnalysisResult:
        """Parse Claude CLI response into structured result"""
        
        try:
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                
                return CodeAnalysisResult(
                    search_term=search_term,
                    analysis_summary=data.get('analysis_summary', ''),
                    relevant_files=data.get('relevant_files', []),
                    code_insights=data.get('code_insights', ''),
                    potential_issues=data.get('potential_issues', []),
                    recommended_fixes=data.get('recommended_fixes', []),
                    confidence_score=data.get('confidence_score', 0.5)
                )
            else:
                # Fallback: use the entire response as analysis summary
                return CodeAnalysisResult(
                    search_term=search_term,
                    analysis_summary=response.strip(),
                    relevant_files=[],
                    code_insights=response.strip(),
                    potential_issues=[],
                    recommended_fixes=[],
                    confidence_score=0.7
                )
                
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse Claude response as JSON: {str(e)}")
            
            # Fallback: use the entire response as analysis
            return CodeAnalysisResult(
                search_term=search_term,
                analysis_summary=response.strip()[:200] + "..." if len(response) > 200 else response.strip(),
                relevant_files=[],
                code_insights=response.strip(),
                potential_issues=[],
                recommended_fixes=[],
                confidence_score=0.6
            )