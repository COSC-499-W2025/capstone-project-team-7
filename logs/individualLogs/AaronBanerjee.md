# Aaron Banerjee (@aaronbanerjee123)

## Week 10: November 4 - November 9

This week, I integrated the code quality analysis system into our interactive CLI application (app.py), making code analysis accessible through the same workflow as PDF, Git, and Media analysis. The integration follows the established pattern used by other analysis types, offering users code quality analysis after scanning a project and providing a dedicated menu option to view detailed results. I implemented state management for analysis results using self._code_analysis_result and created two core methods: _analyze_code_from_scan() which initializes the CodeAnalyzer with user preferences and runs analysis on the target directory, and _handle_code_analysis_option() which displays results by reusing the existing display_analysis_results() function from code_cli.py. The integration respects user configuration settings, pulling max file size limits from their profile and excluding standard directories like node_modules and .git. I added detection logic that checks parse_zip results for code files (checking 18 different extensions including .py, .js, .ts, .tsx, .java, .cpp, .go, .rs, .rb, .php, .cs, and more), and only offers analysis when code files are present and dependencies are available. The feature includes comprehensive error handling with graceful degradation - if tree-sitter dependencies are missing, it provides clear installation instructions and continues with other CLI features. I also ensured the analysis offer appears at the correct point in the workflow (after PDF analysis but before the "Scan completed successfully" message) so users actually see the prompt before the menu appears.

**Technical Challenges & Solutions
Import Path Issues**

Problem: The code analysis integration initially failed silently with CODE_ANALYSIS_AVAILABLE = False, preventing the feature from appearing at all. The root cause was in code_cli.py line 15, which used from code_parser import CodeAnalyzer instead of a relative import. This worked fine when code_cli.py was run as a standalone script, but failed when imported as a module from app.py because Python couldn't find code_parser in sys.path.
Solution: Changed the import to from .code_parser import CodeAnalyzer to use Python's relative import syntax. This was a critical lesson in understanding the difference between running a file as a script versus importing it as a module - the same code works differently in each context. I implemented debug logging (print(f"CODE_ANALYSIS_AVAILABLE = {CODE_ANALYSIS_AVAILABLE}")) to quickly identify when imports were failing, which proved essential for diagnosing the issue. This experience reinforced the importance of using relative imports consistently within a package structure.
Learning: Module imports require careful attention to relative vs absolute paths. Always test imports both as standalone scripts and as imported modules. Adding debug logging at import time helps catch these issues early.*

<img width="1461" height="798" alt="image" src="https://github.com/user-attachments/assets/b8403b50-c069-4115-8e2c-908a46d9dd29" />




## Week 9: October 27 - November 3

*This week, I worked on integrating local code analysis capabilities into our project parsing system. I created a comprehensive code parser module (code_parser.py) that leverages tree-sitter to analyze code quality across 14+ programming languages including Python, JavaScript, TypeScript, Java, C++, Go, Rust, and more. The parser calculates maintainability scores (0-100 scale) based on complexity penalties, comment ratios, and function length, and identifies refactoring candidates by analyzing cyclomatic complexity, function metrics, and code patterns. I also built an interactive CLI tool (code_cli.py) that provides a user-friendly interface for running code analysis, displaying detailed metrics including security issues, TODOs, complex functions needing refactoring, and overall project health assessments. To integrate this with our existing scanning infrastructure, I refactored the parse_zip.py main CLI to support a new --analyze flag that runs static code analysis alongside normal project parsing. I implemented proper error handling throughout, replacing print statements with Python's logging module and adding comprehensive null/error checks for analysis results serialization. This included defensive programming techniques like safe attribute access with getattr(), method existence checking with hasattr(), and wrapping potentially failing operations in try-except blocks. I also added detailed documentation comments explaining the maintainability score calculation formula, including the specific penalty factors (complexity, comment ratio, and function length) that contribute to the scoring system. These enhancements enable users to get actionable insights on code quality, identify high-priority refactoring targets, and detect potential security issues across their entire codebase.*

<img width="1415" height="752" alt="image" src="https://github.com/user-attachments/assets/46266cc0-8a4d-463b-ba2c-b885f8ae09b4" />



## Week 8: October 19 - October 26

*This week, I worked on implementing the database connection to the config manager class. This consisted of refactoring the config manager class to utilize the supabase db in all the CRUD methods. Then I had to update RLS policies for our database so that certain triggers would occur upon a new user being added such as default user configs being added. I then made a test suite for my refactored and new changes to verify that when a new user is made, they can modify their scanning configuration profiles via any CRUD method and our config manager works. The tests all passed. I also reviewed my teammate, Samarths PR for llm integration in analysis. Lastly, I began working towards a new pr in regard to local analysis of coding files in a branch called "local-analysis-coding". This pr isn't finished but so will allow a user to get key metrics and insights on coding files once finished.

<img width="1304" height="683" alt="image" src="https://github.com/user-attachments/assets/10068db4-4b1f-48e5-a20c-92e133f6abb5" />


## Week 7: October 12 - October 19

*This week, I worked on implementing the ConfigManager class which provides the user configuraiton profile logic. This class involved methods that allowed the user to create, delete, and switch between various file configs. The configs allow the user to scan for specific files based on the config they select. For example, the "all" config will scan for all the file extensions that exist, but the documents_only config only iterates through files with extensions like .txt or .md. I then implemented comprehensive testing (about 18 tests) to ensure validity and that the ConfigManager class works in all cases including edge cases. I also reviewed my teammate's pr (Om) for the consent validation module and approved it.*

<img width="1349" height="675" alt="image" src="https://github.com/user-attachments/assets/d8a14dcd-3bae-4c23-9f65-bb7a00a25f43" />




## Week 6: October 6 - October 12

*This week, I spent lots of time studying Docker documentation and understanding how to implement it in our project. Aside from that, I made a code contribution which involed including a template for our fast api backend service. The commit I made will allow our team to move forward with implementing our backend api routes in the future. It involved ensuring using the FastAPI library and uvicorn to test our routes on a default ip to ensure we get a 200 status code. Apart from that, I discussed refinements we can make to our DFD and System architecture diagrams.*

<img width="1438" height="765" alt="image" src="https://github.com/user-attachments/assets/e7ae96fb-b70a-4447-b079-b7e3bd16bcfa" />





## Week 5: September 29 - October 5

*This week, my team and I worked on our DFD level 0 and level 1 diagrams. This entailed us identifying all the key proccees our application would have, and how these processes would communicate with one another. Next, we used a program called Lucid chart to define all the key entities in our DFD's. We then connected all our processes through the key entities, such as connecting the authentication entity to manage the configuration entity, as the user should only be able to manage scanning settings if they are authenticated. On Wednesday, I discussed the DFD's with team 4, team 13, and team 18. I learned some key points from each team during these discussions such as how to better improve our data flow.*


<img width="1180" height="665" alt="Screenshot 2025-10-05 215059" src="https://github.com/user-attachments/assets/219872f7-b4e9-4d4c-8845-6217b57f561f" />



## Week 4: September 22 - 28

*This week, I focused on designing the system architecture diagram with my team. I assisted in figuring out the different layers we would be utilizing and the technologies within each layer. For example, for the service layer, we decided to use REST API. I then worked on the "Requirements, Testing, Requirement Verification" with om in which I worked on the non functional requirements, test cases, and difficulty levels* 


<img width="1340" height="766" alt="image" src="https://github.com/user-attachments/assets/bcf11b48-a62f-451b-b450-1d1ab8998066" />


## Week 3: September 15 - 21 
This week, I worked on defining the non-functional requirements and Work Breakdown Structure (WBS) for our personal artifact discovery and portfolio system. I established performance benchmarks like scanning 1GB of data within 5 seconds and supporting up to 10,000 files, along with security requirements ensuring all user data stays local and encrypted. For the WBS, I organized the project into four phases over 16 weeks: Foundation (research and requirements), System Architecture Design, Database & API Design, and User Interface & Integration. Each phase has clear deliverables and timelines to guide our development of this portfolio tool for graduating students. This planning work provides the technical foundation and project roadmap we need to move forward with implementation.

<img width="1342" height="756" alt="image" src="https://github.com/user-attachments/assets/be4ade06-f6a2-4493-92c2-dac350ff54d5" />
