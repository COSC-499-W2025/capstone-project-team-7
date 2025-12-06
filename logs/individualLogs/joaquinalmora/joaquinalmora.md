# Joaquin Almora / @joaquinalmora

## Week 14 (December 1st - 7th)

## Week 13 (November 24th - 30th)
This week focused on strengthening our project-level analytics by improving the skill-progression pipeline, tightening contribution scoring, and cleaning up several Supabase-related issues. Most of the work landed through **PR [#172 – “Skill progression”](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/172)** and **PR [#162 – “Contribution importance + supabase cleanup”](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/162)**. Together, these changes made the analysis flow feel more accurate, more consistent across state and export, and better grounded in real Git data.

A big portion of the week went into refining the skill progression timeline. I unified filtering, scoring, and contributor attribution around a single user identity (`PORTFOLIO_USER_EMAIL`), fixing several inconsistencies we had before. I also enriched each timeline period with commit messages, top files, activity types, per-period languages, and contributor counts extracted directly from `git log`. A small progress indicator was added so long-running progression tasks feel more responsive. I also tightened the LLM summary prompt so summaries now consistently mention languages, overall trends, and top skills instead of producing generic output.

On the contribution side, I restored the scoring fields in `ProjectsService` and integrated them cleanly into our existing state and export paths. I added a Supabase migration to index projects by `user_id` and `contribution_score`, improving sorted query performance. The project-sorting toggle in the TUI now includes a helper label so the active mode is always visible. Schema updates and RLS rule changes landed safely, and quick pytest coverage helped keep everything stable.

I also spent time hardening the reliability of our analysis features. JSON validation is now stricter and rejects hallucinated values like “no commits,” invented languages, or unrealistic totals. I added raw-dump support for debugging malformed LLM responses. Vendor paths like `lib/` and tree-sitter bindings are now excluded from language stats, which fixed the random “C” hallucinations in summaries. Contributor counts are now calculated correctly per month, and all 13 timeline tests are currently passing.

### Reflection

**What went well:**  
Skill progression and contribution scoring integrated smoothly once everything was unified around a single user email. The expanded timeline evidence greatly improved summary quality. Supabase indexing and RLS updates landed without issues, and the updated sort toggle makes the TUI feel more predictable. The new validators and regression tests significantly reduced hallucinations and made debugging faster.

**What didn’t go well:**  
Several older tests expected outdated contributor logic and needed careful updates. The “contributors” field originally had two meanings (list vs. int), so untangling that was tricky. Optional Textual/PyPDF dependencies required stubbing in tests. Importing `textual_app` directly required mocking generics due to ModalScreen and binding types. LLM outputs still hallucinated even with grounding rules tightened, and without live scans it was harder to iterate on real behavior. Supabase CLI and Docker friction slowed early schema verification. Contribution scoring still depends on Git author emails matching the Supabase email. I also briefly corrupted `textual_app.py` during iteration and had to restore it manually.

### Next Steps

- Practice the presentation  
- Record the video demo  
- Finalize the team contract  

![Peer Eval](./images/w13peer.png)

## Week 12 (November 17th - 23rd)
This week focused on polishing the Textual workflow, tightening up the UI, and improving the reliability of our scan and authentication flows. Most of the work centered on scan configuration, archive caching, preferences layout, and a long overdue fix to our Supabase session logic. Together, these changes made the TUI feel more responsive, predictable, and much smoother to use for repeated scans. All of this shipped through **PR [#145 – ‘Dupe scanner’](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/145)** and **PR [#151 – ‘Deleting insights + stale quitting fix’](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/151)**.

A big portion of the week went into improving the scan experience. I reworked the scan configuration dialog so “Relevant files only” now uses a proper Textual `Switch` with a label and full validation wiring. The dialog also remembers past choices, avoiding the constant re-toggle loop during consecutive scans. I added live progress feedback to the scan itself, including a timer, a progress bar, and per-phase status text updated through a lightweight heartbeat task, which makes long scans feel far less frozen.

Repeated scans received a major speed boost thanks to archive caching. Directories are no longer re-zipped or re-processed when nothing has changed. The caching layer stores snapshots in `.tmp_archives/` and compares file counts and mtimes before rebuilding, which made a noticeable difference on larger repos.

I also cleaned up the preferences screen by removing unnecessary containers, reorganizing items into two clear columns, and standardizing spacing, margins, and button styles. The entire dialog now fits on smaller terminals without scrolling, with all key controls—profile creation, deletion, file size limits, and symlink toggles—easy to reach. During the merge phase, I kept our branch’s versions of `.env`, analyzer work, the previous skills flow, and contribution metrics.

A major reliability fix came from updating Supabase authentication. Previously, only access tokens were persisted, which meant sessions silently expired. I added full refresh-token support with a new session model, persistent storage, expiry checks, a refresh-on-demand flow, and tests to cover everything. Long-running sessions now behave consistently.

Finally, I advanced incremental scanning by introducing a durable file-cache layer, allowing repeated scans to skip unchanged files and reuse stored media info. The UI now displays “Cached skips” to make the optimization visible. This required balancing offline behavior, everything still works without Supabase—and keeping the schema lightweight so it doesn’t inflate storage.

### Reflection

**What went well:**  
The UI work landed smoothly, and Textual made it pretty fast to iterate on spacing, layout, and responsiveness. The refresh-token changes fit cleanly into the existing async session service, and the incremental scan cache hooked nicely into the parser loop. Tests were easy to extend, especially for Supabase helpers, which made the new logic feel stable right away.

**What didn’t go well:**  
Getting layout spacing correct without Textual’s built-in gap utilities took more trial and error than expected. Tracing token-refresh behavior through every consent path was also surprisingly detailed, since missing even one branch would cause new requests to fail. The caching layer also required careful backwards compatibility handling so offline users weren’t broken by schema changes.

### Next Steps

- Clean up and reorganize our Supabase tables, and add missing documentation so the schema is easier for teammates to work with.  
- Retrieve previously generated portfolio information and surface it cleanly inside the TUI.  
- Add all local analyses to the external analysis workflow so reports stay consistent across both paths.  
- Implement a ranking layer that orders projects based on the user’s contribution levels.

![Peer Eval](./images/w12peer.png)

## Reading Break (November 10th - 16th)

This week was all about pulling everything together and turning the Textual CLI into the single, unified interface for the whole project. Most of the work went into **[PR #134 – ‘Textual UI + Refactoring’](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/134)**, which wrapped up weeks of smaller improvements into one clean, cohesive update. PDF analysis is now fully integrated into the workflow, media analysis works reliably even offline, and code analysis finally lives inside the TUI as its own feature. I also removed the old CLI completely, which cleaned up a lot of clutter and made the repo feel much more focused.

A big part of the week was reorganizing the backend. I introduced new service modules like `scan_service`, `session_service`, `preferences_service`, `ai_service`, and `code_analysis_service`, which helped pull logic out of `textual_app.py` and make everything easier to maintain. I added unit tests for these services too, so future refactors feel less risky. On the UI side, users can now tweak AI settings like temperature and max tokens directly in the Textual dialog, and the verification toast actually reflects those choices. PDF analysis now appears in a Textual modal but keeps the familiar format from the old CLI, and media summaries include offline insights like content labels, sample descriptions, tempo stats, and transcript snippets.

I also spent time cleaning up the repo. I removed the entire legacy CLI, along with old runner scripts, unused parsing files, outdated document handlers, and related tests. Both READMEs now describe the Textual-first workflow, and the runner script works properly when a virtual environment is already active. I also fixed dependency issues caused by Python version drift by fully standardizing on Python 3.12, which restored compatibility for modules like `tiktoken`, Torch, and torchaudio.

### Reflection

**What went well:**  
Shifting fully to Textual made the whole architecture a lot cleaner and easier to reason about. Splitting logic into service modules paid off, and the new tests give us real protection from regressions. Getting PDF, media, and code analysis all running inside one UI felt like a big milestone. Once I locked everything to Python 3.12, installs and imports became smooth again.

**What didn’t go well:**  
I hit a lot of friction early in the week from Python version mismatches. Missing dependencies and broken installs forced me to rebuild my environment several times before things stabilized. An early refactor of `textual_app.py` was also too aggressive and introduced a few regressions, including a stray `_debug_log` that caused an AttributeError. Debugging AI verification was tough because Textual hides stdout and stderr, and the key dialog kept reopening without proper feedback. These got sorted out eventually, but they slowed down progress.

### Next Steps

- Stabilize AI verification with clearer logs and user-facing success messages, and make sure `openai` and `tiktoken` behave consistently on Python 3.12.  
- Merge the teammate’s code-analysis branch and resolve the remaining conflicts, then run everything inside Textual to confirm the UI hooks.  
- Continue the refactor by moving dialog logic into `screens.py` and setting up a dedicated AI debug log file.  
- Revisit heavy dependencies once AI is stable and see if libraries like Torch or librosa can be trimmed.

## Week 10 (November 3rd - 9th)

This week I wrapped up the integration of our Git and Media analyzers into the interactive workflow and completed the transition from the legacy CLI to a fully functional Textual TUI, all shipped through **[PR #120 - '
added git/media analysis to workflow'](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/120)** and **[PR #122- 'added TUI'](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/122)**.

On the analysis side, both Git and Media modules are now fully exposed through the post-scan menus, and their outputs flow into the JSON export alongside the rest of the scan data. I also expanded the “all” scanning profile so media types are included by default, and cleaned up noisy info logs from local analyzers.

Most of the week went toward the Textual UI. I replaced our old prompt-based CLI with modal-driven screens for configuration, consent, results, and follow-up actions. I rebuilt the results view using full-screen modals, independent scroll regions, and a restored `DataTable` for horizontal scrolling and selection. Action handlers now run in the background to keep the interface responsive, and I tightened the action bar layout so it fits cleanly on smaller terminals. I also removed a committed venv and updated `.gitignore` so the repo stays clean and consistent.

### Reflection

What went well: integrating the analyzers into the new UI was straightforward, and the shift to Textual gave me a lot more control over layout, responsiveness, and modularity. The JSON export also adapted smoothly to the additional insights.

What didn’t go well: before trying textual, my initial attempt with pytermgui wasn’t compatible with our synchronous workflow and produced unstable terminal states. Then, some Textual quirks around scrolling, padding, and CSS grammar added extra iteration, and the macOS “externally managed” Python environment created friction around venv setup. All of these were addressed by fully switching to Textual, reverting to `DataTable`, cleaning up layout rules, and standardizing the environment.

### Next Steps

Next week I’ll focus on keyboard shortcuts, better focus states, and small color accents. I also want to explore toast-like notifications for long-running tasks and look into simple snapshot testing so UI updates are easier to verify. Also, going to try and implement all features my teammates worked on into the TUI, so that we can get rid of the old CLI.

![Peer Eval](./images/w10peer.png)

## Week 9 (October 27th - November 2nd)
This week I focused on making the CLI fully interactive and connected to the main Supabase workflow through **[PR #108 — “CLI workflow”](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/108)** and **[PR #106 — “scanning preferences through parser”](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/106)**.

I built a new interactive interface in `src/cli/app.py` that walks users through login, consent, and scanning preferences, all tied to their Supabase profiles so settings load automatically. The CLI now has a polished terminal layout with headers, spinners, and menus, and it maintains session persistence via `~/.portfolio_cli_session.json` so users stay logged in between runs.  

I also implemented support for user-defined scanning preferences, letting users choose which folders, file types, and size limits to include. These preferences are wired through the CLI configuration and flow all the way into the parser (`ensure_zip` / `parse_zip`), ensuring consistent behavior across the workflow.

Additional updates include the `scripts/run_cli.sh` helper, a new `CLI_GUIDE.md` with usage instructions, and automated tests to validate the flow. Altogether, these changes make the CLI easier to use, visually clearer, and better integrated with the backend. Next week, I plan to document what’s stored in the session file and prepare a short demo showing the complete login-to-scan flow.

![Peer Eval](./images/w9peer.png)

## Week 8 (October 20th - 26th)
This week I focused on improving the CLI for parsing as part of **[PR #90 — “made it to parse”](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/90)**.

I replaced my previous zip shelling with a safer `ensure_zip` helper that skips unnecessary files like `.venv` and `node_modules`, and now writes ZIP64 archives so large assets don’t cause errors. The CLI was refactored to include reusable helpers for displaying table outputs, making the interface more consistent and readable.

I also added two new flags:
- `--relevant-only`: filters and includes only important files within a directory, helping future LLM parsing skip unnecessary files.
- `--code`: generates a language breakdown for a given project, excluding non-code files such as documents or images, and reports per-language file and byte percentages.

Everything is wired through `src.cli.parse_zip` and `scripts/parse_archive.py`, and the `README.md` was updated to document the new flags with examples. I also added tests to cover the new functionality (language breakdown, auto-zip exclusions), and confirmed that the updated command passes both manual runs and `pytest`.

![Peer Eval](./images/w8peer.png)

## Week 7 (October 13th - 19th)
This week I focused on implementing the archive ingestion pipeline and tying everything together for **[PR #75 — “file parsing and tests”](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/75)**.

Most of my time went into building the main parser in `backend/src/scanner/parser.py`, which now:
- Validates archive paths
- Checks that files exist and end with `.zip`
- Safely blocks traversal attempts so nothing escapes its directory

Each file inside an archive is transformed into a `FileMetadata` object, and the parser aggregates all bytes and issues into a clean summary.

I also added structure to the models by defining:
- `FileMetadata`
- `ParseIssue`
- `ParseResult`

All of these are in `backend/src/scanner/models.py` and use `@dataclass(slots=True)` to keep things lightweight and predictable.

To improve error handling, I introduced two specific error types in `backend/src/scanner/errors.py`:
- `UnsupportedArchiveError`
- `CorruptArchiveError`

These make it easier to tell when something’s missing versus actually broken.

For local testing, I wrote a small CLI script (`scripts/parse_archive.py`) that zips a directory, runs it through the parser, and prints either a readable table or JSON output. Finally, I updated the `README.md` with usage notes so the rest of the team can try out the parser easily.

![Peer Eval](./images/w7peer.png)

## Week 6 (October 6th - 12th)
This week I started by trying to automate a burndown chart that would generate based on our GitHub issues, before realizing that GitHub Projects already provides a built-in burnup chart—so I could’ve saved a couple hours if I had just created a project from the start. 
After, I went and created issues for all the past work we've done, so that the burnup chart would be accurate, and also created issues for the new Milestone 1 Requirements that were released this week, and moved everything into our new GitHub project. I also set up the labels to categorize the issues by type, most of them right now are backend, and I also added a story point field to quantify effort and make our burnup chart accurate, since it tracks total points instead of just issue counts. Once that was done, I worked on updating our Level 1 DFD. Some of the main changes included adding a consent gate, splitting the analysis process into local vs. external analysis, keeping the user more involved through the UI loop, and specifying in more detail what data gets transferred into the database. I also refined the process descriptions and made the flow arrows clearer. Finally, I focused on cleaning up our file structure. Jacob had initially set up the directories, so I kept the relevant ones to the current milestone (mostly backend) to avoid clutter and removed redundant or unnecessary files (like the .env file that shouldn’t have been pushed). I then updated the README to reflect the current directory structure and added quick-access links to our main documentation: WBS, DFD diagram, and System Architecture.

![Peer Eval](./images/w6peer.png)

## Week 5 (September 29th - October 5th)
This week I worked on the data flow diagram and on fixing our repo structure. On Monday me and my group finished designing the DFD level 0 which was super simple, and we began discussing what our level 1 diagram would look like. Instead of drawing right away, I suggested it'd be better to first define our processes and writing down the interactions between them. At the end of Monday's class we had the diagram on paper (text) and we had used Lucid Chart to draw Level 0 and the first few nodes of Level 1. Before Wednesday's class, I went over the finished version of our diagram and changed the shapes we used to make sure they matched the ones given in the lecture, and printed the diagrams to share with other groups. When we compared diagrams, we noticed that some groups had issues like missing data stores or not reusing the same store across processes, which made their flows harder to follow. Also, during that class I realized we had improperly placed our logs directory in the docs directory, so I spent part of that class moving our stuff into its correct place and making sure everything stayed as is.

![Peer Eval](./images/w5peer.png)

## Week 4 (September 22nd - 28th)
This week I worked on creating the first version of our system diagram using mermaid.live. In the next class, I discussed it with other groups and compared our architecture with theirs, which helped me see where our flow wasn’t very clear. After that, we talked as a team about how we were going to split the project proposal, and then I focused on the UML use case diagram and use case scenarios alongside Jacob. Making the diagram readable was a bit challenging with all the arrows and interactions, but we managed to get it done and I added the updated architecture diagram to our repo.

![Peer Eval](./images/w4peer.png)

## Week 3 (September 15th - 21st)
This week I worked on defining the requirements and setting up our repo and our Google Drive folder for our documentation, adding the link to it on our README file. Also, I focused on improving our target user group and the usage scenarios. I based off the initial project details given on canvas and worked on turning them into more specific requirements. Then, in class, I discussed with members of other groups about our requirements and theirs, and looked like all groups were more or less on the same page, except most of them had defined a tech stack while we had not.

![Peer eval](./images/w3peer.png)
