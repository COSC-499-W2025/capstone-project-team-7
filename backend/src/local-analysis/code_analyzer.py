import os
import ast
import json
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
import re


class CodeAnalyzer:
    
    LANGUAGE_MAP = {
         '.py': 'Python',       # .py files are Python
        '.js': 'JavaScript',   # .js files are JavaScript
        '.jsx': 'React',       # .jsx files are React (JavaScript with HTML)
        '.ts': 'TypeScript',   # And so on...
        '.tsx': 'React TypeScript',
        '.java': 'Java',
        '.cpp': 'C++',
        '.cc': 'C++',          # C++ can have multiple extensions
        '.cxx': 'C++',
        '.c': 'C',
        '.h': 'C Header',
        '.hpp': 'C++ Header',
        '.cs': 'C#',
        '.go': 'Go',
        '.rs': 'Rust',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.scala': 'Scala',
        '.r': 'R',
        '.m': 'Objective-C',
        '.sh': 'Shell',
        '.sql': 'SQL',
    }
    
    def __init__(self,folder_path:str):
        """
        Args:
            folder_path (str): Path to the folder to analyze
        
        """
        self.folder_path = Path(folder_path)
        self.results = {
            'overview':{},
            'files':[],
            'languages':{},
            'metrics':{},
            'issues':[],
            'insights':[],
            'timestamp':datetime.now().isoformat()   
        }
        
        
    def analyze(self):
        print("Starting code analysis...")
        
        self.scan_folder()
        
        self.analyze_files()
        
        self.calculate_metrics()
        
        self.generate_insights()
        
        print("Analysis complete.")
        
        return self.results
    
    def scan_folder(self):
        """
        Scan the folder and categorize all code files by language
        
        This method will:
        1. Walk through all the subdirectories
        2. Find code files based on their extension
        3. Group them up by language
        4. Calculate total size
        """
        
        print("Scanning folder...")
        
        files_by_language = defaultdict(list)
        
        total_size = 0 
        for root, dirs, files in os.walk(self.folder_path):
            dirs[:] = [d for d in dirs if d not in [
                'node_modules',
                '__pycache__',
                '.git',
                'venv',
                'env',
                'build',
                'dist',
                'target',
                '.idea',
                '.vscode',
                'bin',
                'obj'
            ]]
            
            for file in files:
                filepath = Path(root)/file
        
                ext = filepath.suffix.lower()
                
                if ext in self.LANGUAGE_MAP:
                    language = self.LANGUAGE_MAP[ext]
                    size = filepath.stat().st_size
                    
                    file_info = {
                        'path':str(filepath.relative_to(self.folder_path)),
                        'name':file,
                        'extension':ext,
                        'size':size,
                    }
                    
                    files_by_language[language].append(file_info)
                    total_size += size
                                        