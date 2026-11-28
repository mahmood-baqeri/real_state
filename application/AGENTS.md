# AGENTS.md — Global Development Rules & Project Context

# PART 1 — GLOBAL INSTRUCTIONS
## Reusable Rules for All Projects

This section is universal and must remain reusable across different projects.

Do not add project-specific information to this section.

Do not modify or remove these global rules unless explicitly requested by the user.

## 1. Core Principles

- Prioritize correctness, security, maintainability, and code quality.
- Minimize unnecessary token and context consumption without sacrificing engineering quality.
- Never scan the entire repository unless explicitly necessary.
- Identify relevant files before reading their contents.
- Read only the required sections of large files.
- Avoid repeatedly reading unchanged files.
- Reuse verified findings from previous tasks.
- Do not repeat completed analysis without a technical reason.
- Never modify unrelated code.

## 2. Project Understanding

At the beginning of a task:

1. Read this AGENTS.md file.
2. Identify the project-specific context section in PART 2.
3. Read only the project context relevant to the requested task.
4. Identify affected modules, dependencies, interfaces, and tests.
5. Expand the investigation only when necessary.

Do not load the entire project context for every task.

## 3. Persistent Project Context Management

PART 2 of this file is the project's persistent engineering knowledge base.

Its purpose is to preserve verified technical knowledge, avoid repeated repository exploration, and reduce unnecessary token consumption.

### Mandatory Context Maintenance

After every meaningful investigation, debugging session, implementation, or architectural change:

1. Identify newly discovered information that will be useful in future tasks.
2. Determine which project context subsection should contain it.
3. Update the relevant subsection in PART 2.
4. Correct outdated information when new evidence disproves it.
5. Remove duplicated, obsolete, or contradictory information.
6. Preserve important historical decisions when they explain the current implementation.

Context maintenance is part of task completion, not an optional future activity.

Do not update the context for trivial operations that introduce no reusable knowledge.

### Context Accuracy

Every important technical statement must have a clear evidence status:

- VERIFIED: Confirmed by source code, tests, or execution.
- INFERRED: Derived from available evidence but not fully verified.
- UNKNOWN: Requires further investigation.

Never record assumptions as verified facts.

Prefer current source code and verified test results over outdated documentation.

Record relevant source file paths for important architectural findings.

### Context Update Rules

- Update only the relevant subsection.
- Do not rewrite the entire PART 2 after every task.
- Do not duplicate information across subsections.
- Do not copy entire source files, logs, or large implementation details.
- Keep records concise, structured, and useful for future development.
- If existing context becomes inaccurate, correct it.
- If a discovery changes an architectural decision, update both the current architecture and the decision record when necessary.
- If no reusable information was discovered, no context update is required.

## 4. Task Execution

For every task:

1. Understand the requested outcome.
2. Identify the smallest reasonable investigation scope.
3. Inspect necessary files and dependencies.
4. Identify potential side effects.
5. Implement the required changes.
6. Run targeted tests first.
7. Run broader integration tests when justified.
8. Update the relevant project context in PART 2.
9. Provide a concise completion report.

Do not expand the task scope without a technical reason.

## 5. Dependency and Impact Analysis

Investigate dependencies necessary for correctness.

Depending on the task, examine:

- Direct consumers.
- Related services and models.
- API contracts.
- Database changes.
- Permissions and security.
- External integrations.
- Frontend consumers.
- Relevant tests.

For cross-module or architectural changes, investigate all affected consumers.

Never sacrifice necessary dependency analysis to reduce token consumption.

## 6. Terminal and Tool Efficiency

- Avoid unnecessary full directory listings.
- Avoid printing entire source files or logs.
- Limit command output to relevant information.
- Extract relevant errors and stack traces.
- Avoid repeatedly executing expensive commands.
- Prefer targeted searches and tests.
- Use agents and additional tools only when they provide a clear benefit.

## 7. Testing and Quality

- Never skip necessary tests to save tokens.
- Start with the smallest relevant test scope.
- Expand testing according to change impact and risk.
- Consider regression, security, concurrency, and data integrity.
- Clearly report tests that could not be executed and explain why.
- Never claim tests passed unless they were actually executed.

## 8. Documentation and Code Comments

- Write comments only when they explain responsibility, non-obvious logic, constraints, or important decisions.
- Avoid redundant comments that merely repeat the code.
- Follow the project's language and documentation conventions.
- Update existing documentation when implementation changes make it inaccurate.

## 9. Completion Report

At the end of every meaningful task, report:

- Root cause or objective.
- Files inspected when relevant.
- Files modified.
- Implemented changes.
- Tests executed and their results.
- Remaining risks or unresolved issues.
- Project context sections updated.

Keep reports concise and avoid repeating information already documented in PART 2.


####################################################################################
####################################################################################
####################################################################################
##############################    Jost Section 2  For Any Project 

# PART 2 — PROJECT-SPECIFIC CONTEXT
## Exclusive Knowledge Base for the Current Project

IMPORTANT:

Everything in this section belongs exclusively to the current project.

Do not treat this information as universal rules.

Use this section as the primary persistent engineering knowledge base for this project.

Update it continuously as the project evolves.

Never move project-specific information into PART 1.

Do not replace this section with generic information.

---

## 2.1 Project Identity

Project Name:
بنیان ملک

Project Purpose:
مدیریت فایل ملک، مشتری، بازدید، قرارداد و امور مالی آژانس‌های املاک.

Main Technologies:
Django، FastAPI، PostgreSQL، Redis و Next.js با TypeScript.

Project Root:
`app/` در فضای کار، استخراج‌شده از آرشیو پایهٔ جاری.

Project Status:
نتایج آزمون و موارد باز هر فاز در `IMPLEMENTATION_PLAN.md` ثبت شده‌اند.

---

## 2.2 Project Structure and Entry Points

- VERIFIED — ورودی توسعهٔ بک‌اند `backend/run.py` است. ثبت مسیرهای API در `backend/fastapi_core/app/main.py` و برنامه‌ها و مهاجرت‌های Django در `backend/django_core/apps/` قرار دارند. رابط Next.js از `frontend/src/app/` آغاز می‌شود.

Record the actual repository structure and important entry points.

Include:

- Main application directories.
- Backend and frontend locations.
- Main configuration files.
- API registration points.
- Authentication entry points.
- Database and migration locations.
- Shared services and integrations.
- Important scripts and infrastructure.

Keep this section concise and update it when the structure changes.

---

## 2.3 Architecture and System Communication

Record verified information about:

- Main application components.
- Responsibilities of each component.
- Communication between services.
- API request and response flow.
- Authentication and authorization flow.
- Database architecture.
- Shared services.
- External integrations.
- Important cross-module dependencies.

For important relationships, record the relevant source file paths.

---

## 2.4 Modules and Business Logic

- VERIFIED در سورس — بارگذاری تصویر ملک در `frontend/src/app/dashboard/properties/[id]/page.tsx` از `SecureFileUploader` استفاده می‌کند. گزینهٔ `allowImagePaste` چسباندن تصویر را فقط در ناحیهٔ بارگذاری همان فرم فعال می‌کند و فایل را وارد صف اعتبارسنجی و پیش‌نمایش می‌کند.

Maintain a structured inventory of the project's main modules.

For each important module, record:

- Module name.
- Business responsibility.
- Main models and entities.
- Main services.
- API endpoints.
- Frontend components and pages.
- Dependencies on other modules.
- Important business rules.
- Known limitations.

Do not document every source file. Focus on information that prevents repeated investigation.

---

## 2.5 Technical Decisions and Constraints

Record important decisions that affect future development.

For each decision, include:

- Decision.
- Reason.
- Alternatives considered, when relevant.
- Technical constraints.
- Consequences.
- Current status: ACTIVE, DEPRECATED, or REPLACED.

Preserve decisions that prevent previous bugs or rejected implementation approaches from being reintroduced.

---

## 2.6 Security and Business Rules

- VERIFIED در سورس — این استقرار فقط ذخیره‌ساز فایل `local` و PostgreSQL روی loopback دارد. سیاست در `backend/django_core/config/settings/base.py` و رجیستری ذخیره‌ساز در `backend/django_core/integrations/registry.py` اعمال می‌شود. ریشهٔ فایل عمومی و خصوصی مجزا هستند.

Record project-specific security and business constraints, including:

- Authentication.
- Authorization.
- Ownership and access control.
- Tenant isolation.
- Data validation.
- Financial and transactional rules.
- Data privacy.
- File access.
- External integration security.

Update this section when important security or business rules are discovered or changed.

---

## 2.7 Testing and Verification

- VERIFIED — تست Django از `backend/django_core` با `python -m pytest` اجرا می‌شود. برای تست FastAPI از `backend/fastapi_core`، مسیر Django را به `PYTHONPATH` اضافه کنید و `DJANGO_SETTINGS_MODULE=config.settings.test` و `TEST_DATABASE_URL` را به محیط آزمایشی تنظیم کنید. گردش WebSocket به Redis آزمایشی نیاز دارد.
- VERIFIED — در `frontend`، `npm test` تست واحد، `npm run lint` بررسی نوع و `npm run build` ساخت تولیدی را اجرا می‌کند.

Record reusable testing knowledge:

- Test commands.
- Test configuration.
- Required environment variables.
- Database requirements.
- Integration test requirements.
- Important regression tests.
- Known test limitations.
- Tests that require special infrastructure.

Distinguish permanent testing instructions from individual test execution results.

Do not treat an old successful test result as proof that the current code still passes.

---

## 2.8 Current Development Status

Maintain a concise snapshot of the current project state.

Include:

- Current development phase.
- Completed major capabilities.
- Work in progress.
- Known bugs.
- Important blockers.
- Pending architectural work.
- Important acceptance criteria.

Update this section when meaningful development progress occurs.

Avoid maintaining a detailed chronological history of every small change.

---

## 2.9 Known Issues and Lessons Learned

- VERIFIED — در `backend/fastapi_core/app/api/v1/negotiations.py` برای استفاده از کش `prefetch_related` پیشنهادها و فعالیت‌ها از `.all()` خوانده و در حافظه مرتب می‌شوند. `.order_by()` روی مدیر رابطه، پرس‌وجوی تازه می‌فرستد.
- VERIFIED — ابزار مشترک جدول در `frontend/src/lib/table-utils.ts` یک `Intl.Collator("fa")` را بین مقایسه‌ها به‌کار می‌برد. معیار و نتایج سنجش محلی در `IMPLEMENTATION_PLAN.md` آمده‌اند.

Record important discoveries that can prevent future mistakes:

- Root causes of significant bugs.
- Previously failed implementation approaches.
- Important compatibility issues.
- Hidden dependencies.
- Non-obvious framework behavior.
- Important edge cases.
- Technical limitations.

Only retain information with future engineering value.

Remove entries when they are no longer relevant.

---

## 2.10 Context Update Log

Maintain a short record of meaningful context updates.

Format:

| Date | Updated Section | Summary | Evidence |
|---|---|---|---|
| YYYY-MM-DD | Architecture | Description of change | Source paths or test |
| YYYY-MM-DD | Testing | Description of discovery | Test name |
| 2026-11-28 | 2.9 | استفاده از کش پیش‌بارگذاری مذاکره و مقایسه‌گر مشترک فارسی جدول | سنجش قبل و بعد در IMPLEMENTATION_PLAN.md |
| 2026-11-28 | 2.1، 2.2، 2.7 | ثبت هویت پروژه، نقاط ورود و شرایط اجرای آزمون پذیرش | backend/run.py، app/main.py، package.json و اجرای محلی |

Do not record every file modification.

Only record meaningful changes to persistent project knowledge.


####################################################################################
####################################################################################
####################################################################################
##############################

# PART 3 — INITIALIZATION AND MAINTENANCE RULES

## 3.1 Initial Project Discovery

When this file is first introduced into a project:

1. Inspect the repository structure.
2. Identify the technology stack.
3. Identify the main application entry points.
4. Understand the high-level architecture.
5. Identify important modules and their responsibilities.
6. Inspect existing documentation.
7. Identify security and business constraints.
8. Identify testing infrastructure.
9. Record verified findings in PART 2.
10. Mark unknown or unverified information clearly.

Perform discovery incrementally.

Do not read every source file or scan every module in detail.

Start with high-level structure and follow actual dependencies.

## 3.2 Ongoing Context Maintenance

After every meaningful task:

1. Review newly discovered information.
2. Compare it with the existing project context.
3. Update the relevant subsection in PART 2.
4. Correct outdated information.
5. Remove contradictions and duplication.
6. Update the context update log when appropriate.
7. Verify that PART 1 remains unchanged.

## 3.3 Before Starting a New Task

Before investigating a new task:

1. Read the task-relevant parts of PART 2.
2. Reuse previously verified findings.
3. Identify what is already known.
4. Investigate only missing or outdated information.

Do not repeat previous repository discovery without justification.

## 3.4 Final Requirement

A meaningful task is not fully completed until:

- The implementation has been verified to the appropriate extent.
- Relevant project documentation has been updated when necessary.
- New reusable engineering knowledge has been saved in PART 2.
- The completion report accurately describes the work.

If context cannot be updated, explicitly report the reason.

Never claim that project context was updated unless the file was actually modified and verified.

---

END OF AGENTS.md
