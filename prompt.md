You are an expert Python developer. Build a complete, working, deployable web application for me called "CV Tailor". Follow every instruction below carefully. Work step by step, and STOP to ask me questions wherever this prompt tells you to.

==================================================
1. PURPOSE
==================================================
I paste a job description (JD). The app uses free AI models to generate a tailored, ATS-friendly CV and a cover letter based ONLY on my real stored information. I can also log my daily work so my profile stays up to date. Finally, I can email the CV and cover letter directly from my Gmail account.

==================================================
2. TECH STACK (keep it simple and free)
==================================================
- Language: Python 3.11+
- UI: Streamlit (single app, multiple pages via sidebar)
- Database: Supabase (free Postgres). Use the supabase-py client.
- Document generation: python-docx for DOCX; generate PDF from the same content (use a reliable library that works on Streamlit Community Cloud, e.g. reportlab or fpdf2, with the same layout as the DOCX).
- Email: Python's built-in smtplib + email libraries, Gmail SMTP (smtp.gmail.com, port 587, STARTTLS) using a Gmail App Password.
- Hosting target: Streamlit Community Cloud (free).
- All secrets read from st.secrets (and from a local .env file during development via python-dotenv). NEVER hardcode any key or password.

==================================================
3. FEATURES
==================================================

3.1 Login protection
- Simple password gate at app start. Password stored in secrets as APP_PASSWORD.
- No page is accessible without login.

3.2 Master Profile page
- Form to create/edit my full profile: name, phone, email, location, LinkedIn, GitHub/portfolio, professional summary, skills (grouped by category), work experience (company, title, location, start/end date, bullet points), projects (name, tech stack, description, bullets, link), education, certifications, languages.
- This is the single source of truth. Every CV is built ONLY from this data.
- Also allow importing my existing CV (DOCX or PDF upload): extract the text, use AI to convert it into the profile JSON structure, show it to me for review, and save only after I click "Approve".

3.3 Daily Update page
- A text box where I write what I did today in plain language (English or Bangla).
- Save as a dated log entry.
- Show the history of entries.
- A button "Suggest profile updates": AI reads all unprocessed log entries and proposes specific changes to the Master Profile (new skills, new achievement bullets, new projects). Show each suggestion with Approve / Edit / Reject buttons. Only approved items are written to the profile. Mark processed logs as processed.
- The AI must NOT exaggerate. If I wrote "fixed a bug in login", it must not become "architected an enterprise authentication system".

3.4 Generate CV + Cover Letter page
- Inputs: job description (text area), company name, job title, optional hiring manager name, optional recruiter email.
- Pipeline:
  Step A - JD analysis: AI extracts JSON: {job_title, company, required_skills[], preferred_skills[], responsibilities[], experience_level, keywords[]}.
  Step B - Matching: AI compares JD with my profile and decides which experience, projects and skills are most relevant, and their order.
  Step C - CV content: AI returns CV content as strict JSON (schema in section 5). It may reorder, select, and rephrase my real content using JD keywords, but must not add anything that does not exist in my profile.
  Step D - Validation (done in Python code, not by AI): compare every skill, tool, company, job title, degree, and number in the generated CV against the Master Profile. Anything not found must be removed or flagged with a visible warning for me to review.
  Step E - Cover letter content as strict JSON (schema in section 6).
  Step F - Show an editable preview of both. I can edit any field before export.
  Step G - Export buttons: download CV as DOCX and PDF, cover letter as DOCX and PDF.
- My information does NOT need to match the JD 100%. For requirements I don't fully meet, highlight related or transferable experience honestly. Never claim a skill I don't have.
- Save each generated application (JD, company, date, CV JSON, cover letter JSON) to the database so I can view history.

3.5 Send Email page / section
- After generating, I can send the application by email.
- Fields: To (pre-filled from recruiter email if given), CC (optional), Subject (AI-suggested, editable, e.g. "Application for [Job Title] - [My Name]"), Body (AI-generated short professional email, editable), attachments (CV PDF and cover letter PDF by default; option to choose DOCX instead).
- Show a full preview and require a "Confirm & Send" click. Never send automatically.
- Use Gmail SMTP with GMAIL_ADDRESS and GMAIL_APP_PASSWORD from secrets.
- Handle errors clearly: wrong app password (SMTPAuthenticationError), network/port blocked, invalid recipient. Show a friendly message for each.
- Log every sent email (to, subject, date, application id, status) in the database.
- Add a "Send test email to myself" button in a Settings page to verify the Gmail connection.

3.6 Settings page
- Show which AI providers are configured (key present or missing) - never display the keys themselves.
- Test buttons: "Test AI providers" and "Test Gmail connection".

==================================================
4. MULTI-MODEL AI WITH AUTOMATIC FALLBACK
==================================================
- Create a module llm.py with a single function, e.g. generate_json(system_prompt, user_prompt, schema_name) -> dict.
- Providers in priority order (all have free tiers; read keys from secrets, skip any provider whose key is missing):
  1. Google Gemini API (GEMINI_API_KEY)
  2. Groq (GROQ_API_KEY) - Llama models
  3. OpenRouter free models (OPENROUTER_API_KEY) - models ending in ":free"
  4. Mistral (MISTRAL_API_KEY)
  5. Cerebras (CEREBRAS_API_KEY)
- Put model names in one config list so I can change them easily, because free model names and limits change often.
- Fallback rules: on rate limit (HTTP 429), quota exhausted, timeout, server error, or invalid/unparseable JSON, automatically try the next provider. Retry JSON parsing once (strip markdown fences) before moving on.
- Validate every response against a Pydantic model. If validation fails, treat it as a failure and fall back.
- Temperature 0.2-0.3 for all calls.
- Show in the UI which model produced the result.
- If all providers fail, show a clear error message, don't crash.

==================================================
5. CV RULES AND JSON SCHEMA
==================================================
The AI only produces content. The layout is ALWAYS created by my fixed Python template, so the format is identical no matter which model is used.

CV JSON schema:
{
  "summary": "2-3 sentences",
  "skills": [{"category": "string", "items": ["string"]}],
  "experience": [{"company": "", "title": "", "location": "", "start": "", "end": "", "bullets": ["3-5 bullets"]}],
  "projects": [{"name": "", "tech": [""], "bullets": [""], "link": ""}],
  "education": [{"institution": "", "degree": "", "start": "", "end": "", "details": ""}],
  "certifications": [{"name": "", "issuer": "", "year": ""}]
}
(Contact info is inserted by code directly from the profile, not by AI.)

Fixed section order:
1. Name + contact line
2. Professional Summary
3. Skills
4. Work Experience (reverse chronological)
5. Projects
6. Education
7. Certifications (only if present)

ATS formatting rules for the template:
- Single column. No tables, images, icons, text boxes, columns, or graphics.
- Nothing important in header/footer areas.
- Font: Calibri or Arial, body 10.5-11pt, name 16-18pt, section headings 12pt bold.
- Standard section headings exactly as written above.
- Simple round bullets. Consistent date format (e.g. "Jan 2024 - Present").
- Margins about 0.7-1 inch. Target 1 page, maximum 2 pages.
- Clean, professional, nothing unusual or decorative.

Content rules (include these in the AI system prompts):
- Use ONLY facts from the provided profile. Never invent companies, titles, dates, skills, tools, certifications, metrics, or numbers.
- You may rephrase and use JD keywords only where they truthfully describe my real work.
- Start bullets with strong action verbs. Keep numbers only if they exist in my profile.
- Prioritize the content most relevant to the JD.
- Banned words/phrases: "passionate", "rockstar", "ninja", "guru", "go-getter", "synergy", "world-class", "results-driven", "think outside the box", and similar clichés.
- Professional, clear, concise English.

==================================================
6. COVER LETTER TEMPLATE AND JSON SCHEMA
==================================================
Cover letter JSON schema:
{
  "greeting": "Dear Hiring Manager," (or the given name),
  "opening": "1 paragraph: the role I'm applying for and a one-line reason I'm a strong fit",
  "body_experience": "1 paragraph: my real experience matching the 2-3 most important JD requirements, with specific examples",
  "body_skills": "1 paragraph: relevant skills/projects and what I can contribute to this company",
  "closing": "1 short paragraph: interest, request for an interview, thanks",
  "sign_off": "Sincerely,"
}
- Fixed layout by code: my name and contact at top, date, company name, then the sections above in order, then my name.
- Total 250-350 words. Specific to the job, no generic filler, no exaggeration, same factual rules as the CV.
- Same font and style as the CV.

==================================================
7. DATABASE
==================================================
Provide a schema.sql file for Supabase with tables:
- profile (single row, JSON column for the full profile, updated_at)
- daily_logs (id, date, content, processed boolean, created_at)
- applications (id, company, job_title, jd_text, cv_json, cover_letter_json, model_used, created_at)
- email_logs (id, application_id, to_email, subject, status, error, sent_at)

==================================================
8. SECURITY
==================================================
- All secrets in st.secrets / .env only. Provide .env.example and .streamlit/secrets.toml.example with placeholder values.
- Add .env and .streamlit/secrets.toml to .gitignore.
- Never print, log, or display any key or password.
- Login gate on every page.

==================================================
9. PROJECT STRUCTURE AND DELIVERABLES
==================================================
Deliver the complete code with this structure (adjust if needed):
- app.py (entry + login)
- pages/ (Profile, Daily Update, Generate, Send Email, History, Settings)
- llm.py (fallback logic)
- prompts.py (all AI system prompts in one place)
- schemas.py (Pydantic models)
- validator.py (anti-hallucination checks)
- cv_template.py and cover_letter_template.py (DOCX + PDF rendering)
- emailer.py (Gmail SMTP)
- db.py (Supabase functions)
- schema.sql, requirements.txt, .gitignore, .env.example, secrets.toml.example
- README.md with step-by-step instructions in simple language: creating each free API key, setting up Supabase, creating a Gmail App Password, running locally, and deploying to Streamlit Community Cloud (including where to paste secrets).

==================================================
10. QUESTIONS YOU MUST ASK ME (STOP AND WAIT)
==================================================
Before writing the code, ask me:
1. Do you want me to make any change to this plan?
2. Which AI provider API keys do you already have?

When you reach the email feature, STOP and ask me:
"Please provide your Gmail address and your 16-character Gmail App Password. (Create it at: Google Account > Security > 2-Step Verification > App passwords.)"
When I give them, do NOT write them inside any code file. Instead, tell me exactly where to put them:
- Locally: in the .env file as GMAIL_ADDRESS and GMAIL_APP_PASSWORD
- On Streamlit Cloud: in App Settings > Secrets
Then help me run the "Send test email to myself" check.

Also ask me for the Supabase URL and key at the database setup step, following the same rule (secrets only, never in code).

==================================================
11. QUALITY
==================================================
- Code must run without errors. Include error handling everywhere.
- Add short comments explaining important parts.
- After finishing, give me a checklist to test every feature end to end.
