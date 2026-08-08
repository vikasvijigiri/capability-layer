# LLM and Repository Environment Rules

- Always use `groq LLM` with the `opengpt oss 120B` model for the repo's language-model workflows.
- Keep repository-level environment variable documentation in a root `.env.example` or `.env.template` file so manual inputs are visible and discoverable.
- Do not commit real secret values into `.env`; the repo should contain only placeholders and descriptions for manual values.
- If the repo requires manual inputs, document them at the root level and avoid scattering them across source files or hidden directories.
- Any exception to using `opengpt oss 120B` must be approved explicitly and documented in `CLAUDE.md` rather than treated as a general rule.
