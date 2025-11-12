⚡ Prime Context & Engineering Guide

This document outlines the primary instructions for analyzing a codebase and the best practices for constructing prompts.

🤖 Context Engineering Best Practices

When building prompts (especially for Python tasks), follow these principles:

    Use Clear XML Delimiters: Claude is specifically trained to recognize XML tags. Do not use ambiguous symbols (like ---, ###, or ***) to separate parts of your prompt. Always wrap instructions, context, code, and examples in clear tags.

        Good: <code>\nprint("hello")\n</code>

        Bad: ***Code Here:***\nprint("hello")

    Be Explicit and Direct: Clearly state your requirements.

        Python: Specify versions (use Python 3.10), libraries (use pandas for this, not a loop), and standards (follow PEP 8, include Google-style docstrings).

        Output: Define the exact format you need (e.g., Respond only with the Python code, Provide your answer in a JSON object).

    Use an Agentic Approach for Complex Tasks: Don't ask the model to do everything at once. Break down complex problems into a "chain of thought" or a multi-step plan.

        Example: "First, outline the classes needed for this project. Second, write the __init__ method for each class. Finally, write the methods for the User class."

        This is what "use agents when needed" means in practice: using the model as a collaborator in a step-by-step process.

    Provide Examples (Few-Shot Prompting): If you need a specific style or format, provide a clear example of the input and the desired output.

        Example: When I provide a docstring, convert it to a_snake_case_function_name. <example_input>Fetches user data from API.</example_input> <example_output>fetches_user_data_from_api</example_output>

    Manage Context Size: For large projects, don't paste thousands of lines of code. Instead, use the tree command and provide only the key files relevant to the specific task.

    Use the Right Model & Endpoint: Ensure you are using the correct model for your needs (e.g., Opus for complex reasoning, Haiku for speed/cost). For production applications, use official, streaming-capable API endpoints for the best user experience.

📂 Project Analysis Task

Your task is to analyze the provided project context and give me a clear, high-level summary.

1. Initial Review

    Use the output of the tree command to understand the project's directory structure.

    Start by reading the CLAUDE.md file if it exists. This file may contain specific instructions or context for you.

    Next, read the README.md file to understand the project's purpose, setup, and usage.

2. Code-Level Review

    Read key files in the src/ directory (or the root directory, if src/ doesn't exist) to understand the core logic.

    Identify primary configuration files (e.g., config.py, .env.example, settings.py).

    Identify dependency files (e.g., requirements.txt, pyproject.toml).

3. Report Back

After your review, explain the following back to me in a clear, structured response:

    Project Structure: A brief overview of the directory layout.

    Project Purpose: What does this project do? What problem does it solve?

    Key Files: A list of the most important files/modules and their purpose.

    Key Dependencies: Any crucial external libraries it relies on.

    Key Configuration: Any important configuration files or environment variables.