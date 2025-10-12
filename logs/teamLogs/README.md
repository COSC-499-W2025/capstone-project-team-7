# Capstone Team 7 Logs

## Week 6 (October 6 - 12)

This week our focus was on getting our project setup in place and updating some of our main documents. We started by creating a GitHub Project to organize all our tasks and make progress tracking easier with its built-in burnup chart. 

All previous tasks and the new Milestone 1 requirements were added as issues, each labeled by category and assigned story points so the chart reflects effort more accurately. After that, we worked on updating our Level 1 DFD. Some of the key changes included adding a consent gate, splitting the analysis process into local and external parts, keeping the user more involved through the UI loop, and showing more detail on how data moves into the database. We also cleaned up the process descriptions and arrows so the flow is easier to follow. We also updated our System Architecture diagram to reflect the changes brought by the new requirements, specifically the disctintion between the local and external analysis options. The Work Breakdown Structure was also expanded to cover all the specific tasks and deliverables from Milestone 1, before, it was more general and based on our early understanding of the requirements. Morevoer, the repo was setup with all of our initialy directories so we can start working on our backend. FInally, A Dockerfile was also added to standardize the environment setupand the README was updated to match the current directory structure and now includes direct links to our main documentation: Work Breakdown Structure, Data flow diagrams, and System Architecture.

<p align="center">
  <img src="./charts/w6burnup.png" alt="Week 6 Burnup Chart width="400"/>
</p>

## Week 5 (September 29 - October 5)

This week our focus was on the Data Flow Diagrams (Level 0 and 1).

We started off the week with listing down some simple processes from the start to the end in our google document. This process then led to us discovering some other interconnected processes which allowed us to narrow down onto the 7 main processes that would control the entire flow of data in our diagram. From here we had to just draw the shapes for each one of them and add appropriate description. The next steps were collective efforts into deciding the process flow directions for the different processes and their inputs and outputs. The end step was to add into picture the data storage aspect and connect it to the rest of the diagram. The shapes were then adjusted to match the notation from lecture so the diagram looked clear and consistent, and copies were printed to share with other groups. When comparing diagrams, it became clear that some groups had missing or inconsistent data stores, which made their flows harder to follow and less organized. We also checked over our own diagram to make sure the data stores were being reused correctly across processes. Finally, the repo was reorganized by moving the logs directory out of the docs folder and into its correct place, making the structure consistent with class practices.

<p align="center">
  <img src="./charts/w5burnup.png" alt="Week 5 Burnup Chart width="400"/>
</p>


## Week 4 (September 22 - 28)

This week we focused on the system architecture and the project proposal.

For the architecture, we first made a detailed component diagram that broke down each layer and described the components inside them. While it helped us see exactly what pieces exist in the system, the problem was that the flow of information wasn’t obvious, the arrows just went from one layer to the next without showing how data would actually move. After discussing, we made a second diagram that was less detailed but much clearer in terms of flow. The first diagram works well for showing system structure, while the second works better for understanding process flow. Together they allow for a pretty good understanding of the system.

We also finished the project proposal, which included:
- Usage scenario (Samarth)  
- Proposed solution (Vlad)  
- Use cases (Joaquin & Jacob) – covering artifact discovery, analysis, privacy, reporting, search/filter, etc.  
- Requirements & testing (Om & Aaron) – both functional and non-functional, linked to test frameworks (Jest, Playwright, etc.), with difficulty levels assigned.  

## Week 3 (September 15 - 21)

We worked on developing ideas for the functional and non-functional requirements for the Project Requirements document. Additionally, we added information regarding the target user group and usage scenarios. We also spent time discussing the requirements in class and learning about other teams' requirements as well. One thing we noticed we did not do that other teams did was define a tech stack, but we think it would be better to define our tech stack once we have more defined project specifications.


