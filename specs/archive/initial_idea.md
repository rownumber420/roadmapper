I use two agents (Gemini CLI and OpenCode) with free models for vibe coding.
I found that free models can actually be useful, but only when asked to implement small testable changes or atomic simple features.
If I ask to implement several features at once, they usually fail or introduce many bugs.

That is why I find it useful to describe to an agent what needs to be implemented and ask the agent to create a roadmap with tasks.
Each task should be as atomic as possible, as simple as possible, and include steps to test the implementation.
Tasks should include short code examples if possible - this also helps a lot.

When an agent (for example OpenCode with Big Pickle model) creates roadmap.md I ask another agent (Gemini CLI with one of its models) to check if the roadmap is correct, bug-free and can be implemented.
And usually it finds issues. Then I copy-paste Gemini's findings to OpenCode, which usually agrees they are valid and fixes the roadmap. Then I repeat these steps until both agents agree that roadmap is correct.

So I'd like to automate this workflow.
My thoughts:
I know LangGraph can be used for agents orchestration, so probably this is a good tool for it.
I'd prefer to run agents in docker containers with mounted dir with codebase of the project to be sure that agents will be constrained to the directory with the code.
I'd like agents to save their communication to the database (also dockerized) to be able to check it later. Is this the same as persisting state in LangGraph to a database?
I'd like to have some GUI tool to navigate logs in this database, probably also dockerized.
Agents should have prompts stating that they should only work (create/review) on the roadmap file, they should not write the code.
I should be able to configure a Writer agent and its model and a Reviewer agent and its model.

Desired workflow:
1. I create somewhere a file with initial task.
2. I trigger the workflow somehow (how?).
3. Writer agent creates an initial version of the roadmap.
4. Reviewer agent creates their feedback.
5. Writer reads feedback and makes changes if they make sense.
Steps 4 and 5 are repeated until roadmap is stable. According to my experience it can take up to 6 iterations.
6. Workflow is finished.
