# Samarth Grover (@Samarth-G)

## Week 9: October 27 - November 2

This week I integrated the LLM analysis module into the main application workflow. I started by modifying client.py to add the `summarize_scan_with_ai()` method, which orchestrates the entire analysis process by reading file contents from scan results, analyzing individual files using `summarize_tagged_file()`, and generating project overviews through `analyze_project()`. <br>
Next, I enhanced `app.py` with the complete AI analysis menu system, adding it as option 5 in the main menu with the constant MENU_AI_ANALYSIS. I implemented session-level state management by adding `_llm_client` and `_llm_api_key` variables to maintain API credentials in memory throughout the user's session. <br>
After which, I built `_handle_ai_analysis()` as the main handler function, which performs sequential validation checks including login verification, external services consent confirmation, and scan existence validation before prompting users for their API key and executing the analysis pipeline. <br>
On top of that, I created `_render_ai_analysis_results()` to display analysis results using Rich panel formatting with color-coded sections and professional styling, along with `_export_ai_analysis()` to save results as formatted markdown reports. <br>
Finally, I implemented comprehensive privacy and security measures by ensuring API keys are never persisted to disk, requiring explicit consent before sending data to external services, and automatically filtering out binary files so only text content is analyzed. 

![Week 9 Image](./assets/SamarthG-W9.png)

## Week 8: October 20 - October 26

This week I implemented the LLM-powered summarization and analysis capabilities for the project. I started by building the `summarize_tagged_file()` function, which returns structured outputs with key insights including Summary, Core Functionality, and Notable Patterns. It detects when a file exceeds 2000 tokens and automatically applies chunking. <br>
Next, I added `analyze_project()`, designed to generate resume-ready reports summarizing a project’s technical and qualitative aspects including an executive summary, technical highlights, tech stack used, and project quality assessment. <br>
After which, I implemented a helper function to handle large files efficiently `chunk_and_summarize()`, which splits text into 2000-token chunks with 100-token overlaps, summarizes each part independently, and merges the results into a coherent final output. On top of that, I added `suggest_feedback()` to provide personalized, career-aligned insights based on both local and AI results. <br>
Finally, I built supporting functions like `_count_tokens()` (using tiktoken with a character-count fallback) and `_make_llm_call()` to standardize LLM interactions. These functions will be used together in the app workflow to make up the LLM analysis module, with more functions that we might add in the future.

![Week 8 Image](./assets/SamarthG-W8.png)

## Week 7: October 13 - October 19

This week I focused on setting up the LLM integration for the project. I started by building the LLMClient class, which wraps around the OpenAI API and handles everything from API key verification to error management. It validates keys up front, handles authentication, and keeps configuration clean through a shared global client state. <br>
Once the client was in place, I added new REST endpoints under /api/llm/ for verifying keys, checking model info, clearing credentials, and viewing service status.
To make sure everything was reliable, I wrote 30+ automated tests spanning both the client and the routes, covering initialization, key validation, failure cases, and full integration workflows. This sets up a solid foundation for future AI-driven analysis features.

![Week 7 Image](./assets/SamarthG-W7.png)

## Week 6: October 6 - October 12

This week my team and I worked on amending our project to match the milestone 1 requirements and worked on setting up the basic code repo for the python backend. I personally worked on creating the basic Docker container setup and wrote the code for the needed dockerfiles. I also updated the System Architecture diagram based on the criteria of the milestone 1 requirements. Through the week I also took part in several discussions to map out our teams project setup and how we're going to approach all the different requirements listed as part of milestone 1.

![Week 6 Image](./assets/SamarthG-W6.png)

## Week 5: September 29 - October 5

This week I worked with my team to develop the Data Flow Diagrams for Level 0 and Level 1. We began by listing out all the core processes in a shared document and refining them into the seven main processes that defined the overall data flow in our system. Once finalized, we used a tool called Lucidchart as a collabrative platform to create the visual diagrams. During this process we iterated through a few designs and variations, ensuring that the connections, inputs and outputs between processes were logically accurate. The final step for us was fixing up the shapes we used in our diagram based on the ones mentioned in lecture.

![Week 5 Image](./assets/SamarthG-W5.png)

## Week 4: September 22 - 28

This week I worked with my team to brainstorm and iterate through the System Architecture Diagram. We first settled on a more information heavy diagram but later pivoted to a more visual diagram that was easier to understand, while using the older diagram as a reference for a detailed component breakdown. I also worked on the Project Scope and Usage Scenario section of the Project Proposal to layout the concrete outline for what our project aims to achieve. 

![Week 4 Image](./assets/SamarthG-W4.png)

## Week 3: September 15 - 21 
This week I worked alongside my team to set up the foundation for the project including the git repository and docs setup. We discussed the project overview and wrote out the functional and non-functional requirements by going in depth and understanding what was needed to build the project.

Missed lecture due to sickness during this week.

![Week 3 Image](./assets/SamarthG-W3.png)
