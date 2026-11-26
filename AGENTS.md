# Project collaboration rules

Public GitHub content is a curated technical deliverable, not a mirror of the internal working directory.

- Publish task definitions, core implementation, architecture, verification mechanisms, research methods, necessary experimental evidence, limitations, and reproducible usage.
- Keep personal deployment details, license status, installation failures, machine migrations, temporary debugging, and operational records in ignored private research storage (for example `.local/`). If infrastructure affects experiment validity, publish only the necessary classification and denominator information.
- Never conceal genuine research failures, fabricate success, or delete original experiment records to improve presentation.
- Preserve historical frozen task contracts, evidence, and experiment inputs. New methods, tools, or observations require explicit versions and separate evidence. Do not rewrite Git history.
- Before publication, inspect the whole pending diff and artifacts. Exclude secrets, commercial tool/library contents, private test vectors, machine configuration, builds, and repetitive raw logs. Review existing explanatory documentation for unnecessary operational details without invalidating historical evidence.
- Use actual positive/negative controls and independent terminal verification before claiming new capabilities work. Tool availability, synthesis success, or equivalence to a candidate's own netlist does not establish task correctness.

## Human-readable documentation

- Follow [Documentation guidelines](docs/documentation-guidelines.md) when creating or updating human-facing documents; machine-readable data and frozen evidence retain their own contracts.
- Organize around the reader's purpose: establish context and relationships before implementation detail, and connect conclusions to evidence. Choose a structure suited to the document, not a fixed template or development chronology.
- Support scanning, understanding, and verification through clear hierarchy, purposeful diagrams, concise comparisons, and explicit links. Explain unfamiliar terms in context; keep essential limits and failures visible.
- Use the README SVGs as the visual reference: stable semantic colors, deliberate layout and boundaries, readable typography, maintainable source and alternative text. Prefer SVG for important diagrams; use simpler forms when they communicate better.
- Review reading flow, accuracy, links, and rendering separately after writing; check relevant light/dark and narrow-screen views when possible, and report unverified conditions. Never improve presentation by changing frozen evidence or overstating capabilities.
- Apply incrementally to new and touched documents; keep this file concise and detailed methods in the linked guidelines.
