
# Jacob Damery

## Week 10 (November 3rd – 9th)

I expanded our local media analyzer so every modality—images, video frames, and now audio—produces meaningful insights entirely offline. A new PyTorch helper loads TorchVision’s ResNet for visual labels and Torchaudio + Librosa for wav2vec2 transcription, BPM estimation, spectral centroid, and heuristic genre tags. Those labels, summaries, tempo stats, and transcript excerpts now flow through the scanner, MediaAnalyzer, CLI tables, and JSON output, giving reviewers immediate context without calling external APIs.

### Reflection

- **What went well:** The PyTorch/Torchaudio modules plugged into the existing scanner pipeline with minimal refactors, analyzer metrics automatically picked up the new fields, and the CLI felt more useful once tempo/genre summaries appeared next to each clip.
- **What didn’t go well:** Librosa’s extra dependencies slowed down the first install, torchaudio emitted deprecation warnings during MP3 loads, and full `pytest` runs still choke on Supabase config because the upstream tests require real credentials.

### Next Steps

1. Add a cache/weights preloader so the first CLI run doesn’t stall while wav2vec2 downloads.  
2. Offer a “lightweight” mode that skips transcription when users only need tempo/genre.  
3. Update repository tests to mock Supabase so the full suite can run headless.



## Week 9 October 27th - November 2nd
This week I worked on the full media analysis flow: the scanner now extracts structured metadata for images, audio, and video; a deterministic MediaAnalyzer rolls it into insights/issues (with tests and docs); and a Rich/Questionary CLI lets teammates explore results interactively. I experimented with a CLIP/Whisper “advanced” layer but parked it because the dependency stack was heavy. Most friction came from polishing the CLI (handling non-TTY prompts, default paths, exit behavior) and keeping everything Python 3.9-compatible
<img width="720" height="431" alt="Screenshot 2025-11-02 at 7 36 57 PM" src="https://github.com/user-attachments/assets/36d3b3b7-73c6-4bab-b7e2-53aa91b78d5e" />

## Week 8: October 19 - October 26

*This week, I worked on integrating Supabase into our Portfolio Manager backend. I set up the environment with the project URL and anon key, and began building out the database schema and storage policies. I also started creating an upload test to verify file and metadata storage, but ran into bugs that prevented it from running successfully. I wasn’t able to finish the work or open a PR this week, but made progress on the Supabase integration that I’ll continue next week.*
<img width="1101" height="649" alt="Screenshot 2025-10-26 at 11 36 32 PM" src="https://github.com/user-attachments/assets/7386e278-1bfb-433c-9a3b-b04cbbc3575d" />

## Week 7: October 12 - October 19

*This week, I worked on implementing the consent management module which provides the logic for handling user permissions when interacting with external services such as LLMs. This module involved creating functions that allow the system to request consent, save the user’s decision, check if consent has been given, and allow consent to be withdrawn. The module also integrates a detailed privacy notice so that users are informed about data transmission and storage risks before giving permission. I then implemented a set of unit tests (5 in total) that verify both the positive and negative paths (agree/decline), default behavior when no record exists, and the withdrawal process. Finally, I resolved rebase conflicts with main to ensure the consent module and tests were properly integrated into the backend, and I prepared a structured PR documenting these changes.*
<img width="1101" height="649" alt="Screenshot 2025-10-26 at 11 36 32 PM" src="https://github.com/user-attachments/assets/12e8d7d4-b5f6-4516-a2ae-1c89f491527a" />

## Week 6: October 6th - 12th

This week, I put my efforts into establishing the file hierarchy within the development environment we are working on. The creation of the first folders and files required for the project took place along with the addition of inline documentation to each file. The documentation covers the file's purpose, the functionality aimed at, and any future implementations that might need to be added are written as comments. Team collaboration will be simpler with this structure, as it will be clear for everybody through the documentation where each part is going to be placed while the system is still being built.

![Tasks Completed](./assets/Week6Jacob.png)

## Week 5: September 29 - October 5

I was absent on Monday but joined the team on Wednesday when we were finalizing our Data Flow Diagrams (Levels 0 and 1). During that session, I helped review the process connections and verified that all data stores, inputs, and outputs were correctly linked. I also contributed to checking for any missing internal processes and ensuring that the diagrams accurately reflected the system’s workflow*

![Tasks Completed](./assets/omistry_Week5.png)

## Week 4: September 22 - 28

*This week, I examined integration and compatibility options for several third-party APIs and backend systems. I analyzed the potential impact of various authentication models, data structures, and rate-limiting behaviors on our architecture, identifying integration risks and outlining strategies for risk mitigation. At the same time, I made considerable progress on expanding the use-case section of our project proposal.*


<img width="1340" height="766" alt="image" src="https://github.com/user-attachments/assets/bcf11b48-a62f-451b-b450-1d1ab8998066" />

# Week 3: September 15 - 21
This week I explored possible tools and backend libraries that could support our app, comparing their features and suitability.

<img width="1124" height="660" alt="image" src="https://github.com/user-attachments/assets/58ff1649-a295-4006-8681-36cae01a27fd" />
