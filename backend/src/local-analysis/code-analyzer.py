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