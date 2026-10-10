# <area>/CLAUDE.md

<!-- Loads only when Claude reads or edits files under <area>/. Under ~40 lines. Only rules for this area. -->

- Entry points: `<path>` (<what>), `<path>` (<what>).
- Test this area: `<cmd ./<area>/...>`; integration tests need `<scratch service>` (`octl port reserve`).
- Conventions: <naming, error handling, logging>.
- Security: <authz check every handler must call>; <every query is scoped by tenant/owner>; <no raw user input in shell/SQL>.
- Generated files (do not edit by hand): `<path>` - regenerate with `<cmd>`.
