# Changelog fragments

Every user-visible 0.x change needs one fragment named `<issue>.<type>.md`, where type is `feature`, `bugfix`, `security`, or `doc`. Use a numeric GitHub issue or pull-request identifier so generated links remain valid.

Use one fragment per issue and change type. A single sentence is preferred for one outcome. When one issue delivers several closely related user-visible outcomes, write a short introductory sentence followed by concise Markdown bullets; Towncrier preserves that formatting in the generated section. Do not copy implementation steps or unfinished work into a fragment: future work belongs in the backlog, and unrelated release-note entries need their own issue and fragment.

Before handoff or release, render the pending notes with `towncrier build --draft --version <target-version>` and inspect the complete generated section for grouping, links, punctuation, and readability.
