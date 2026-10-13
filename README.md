# CV Tailor

A private, single-user Streamlit application that tailors a CV and cover letter from
reviewed facts, keeps daily work logs, exports DOCX/PDF, and sends applications through Gmail.

## Run locally

Python 3.11 or newer is required.

```bash
cd '/home/gh/piash/word/auto job apply'
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# For a fresh checkout only; preserve an existing configured .env:
cp .env.example .env
streamlit run app.py
```

The current workspace already has a private `.env` containing both supplied AI
accounts, the selected Gmail sender, and a randomly generated APP_PASSWORD. Do not
replace it with the example. Open `.env` privately to read or change APP_PASSWORD.
The Supabase URL and server-side API key are configured locally, and the database
schema has been initialized and verified. Open http://localhost:8501 and sign
in with APP_PASSWORD. The Settings page works before Supabase is configured.

## Set up Supabase

1. Sign in at https://supabase.com and create a free project. Save the database password privately.
2. Open the project's SQL Editor. Paste all of `schema.sql` and click Run.
3. In the project's Connect dialog or API settings, copy the project URL.
4. In Settings → API Keys, get a **secret key** (`sb_secret_...`) or the legacy
   **service_role** key. Use it only in this Python server. A publishable/anon key
   will not work with this application's intentionally private tables.
5. Edit `.env`:

   ```dotenv
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-server-side-secret-key
   ```

6. Restart Streamlit. In Settings, click Test database connection.

RLS is enabled on every table and no public/browser policies are granted. The
server key bypasses RLS. A single login in `app.py` protects every page, including
direct links. Sign in once per browser session; sidebar navigation shares that login.
Sign out ends access to the whole app.
The daily review operation saves the profile and processes logs in one database transaction.
See [Supabase RLS documentation](https://supabase.com/docs/guides/database/postgres/row-level-security).

## Get AI API keys

You need at least one working provider. The others are optional. Free allowances
and models change, and some services require enabling a free/experimental plan.
Do not assume any provider has unlimited use.

- **Gemini:** open https://aistudio.google.com/apikey, sign in, create/select a
  project and create a key. Store as GEMINI_API_KEY.
- **Groq:** open https://console.groq.com/keys, sign in, create a key and store
  as GROQ_API_KEY. Pick an available model from https://console.groq.com/docs/models.
- **OpenRouter:** open https://openrouter.ai/keys, create a key and store as
  OPENROUTER_API_KEY. This application accepts only model IDs ending in `:free`;
  choose a currently available JSON-capable free model from
  https://openrouter.ai/collections/free-models. The keys labeled “Open ai” in
  the supplied document have OpenRouter format; there is no OpenAI API adapter here.
- **Mistral:** open https://console.mistral.ai, enable Studio's free plan if offered,
  create a key in API Keys and store as MISTRAL_API_KEY. See
  [Mistral setup](https://docs.mistral.ai/getting-started/quickstarts/developer/first-api-request).
- **Cerebras:** open https://cloud.cerebras.ai, create an account and an API key,
  then store as CEREBRAS_API_KEY. Confirm the model and account allowance in the dashboard.

For each provider, a second account uses the same variable with `_2`, for example:

```dotenv
GEMINI_API_KEY=first-account-key
GEMINI_API_KEY_2=second-account-key
GROQ_API_KEY=first-account-key
GROQ_API_KEY_2=second-account-key
```

Fallback order is Gemini 1 → Gemini 2 → Groq 1 → Groq 2 → OpenRouter 1 →
OpenRouter 2 → Mistral 1/2 → Cerebras 1/2. Missing accounts are skipped.
Each request starts at the first configured account. HTTP failures, exhausted quota,
timeouts, malformed JSON and schema violations all move to the next account.
Account quotas may be shared across projects; switching accounts is not a guarantee
of extra capacity. A successful stage records its actual model/account in the UI.

Current local defaults were checked against live provider APIs: Gemini 3.8 Flash,
Groq GPT OSS 120B, and OpenRouter Apodex 1.1 Mini (free). The older Llama default
was unavailable on Groq, so an available model is used. You can choose any supported
model later.

Defaults live in `config.py` in one PROVIDERS list. You can override them in secrets
without editing code: GEMINI_MODEL, GROQ_MODEL, OPENROUTER_MODEL, MISTRAL_MODEL,
CEREBRAS_MODEL. OpenRouter overrides must end in `:free`.
Test AI providers in Settings. A green key-present indicator only means configured;
it does not mean the provider has accepted a live request.
See [Gemini REST API](https://ai.google.dev/api/generate-content) and
[Groq API reference](https://console.groq.com/docs/api-reference).

## Set up Gmail

1. Sign in to the Gmail account used as sender.
2. Google Account → Security → enable 2-Step Verification.
3. Search Google Account for App passwords (or visit https://myaccount.google.com/apppasswords).
4. Create an app password for CV Tailor.
5. Put these values in `.env`, never in a Python file:

   ```dotenv
   GMAIL_ADDRESS=your-email@gmail.com
   GMAIL_APP_PASSWORD=your-16-character-app-password
   ```

6. Restart the app. Settings → Test Gmail connection verifies authentication
   without sending. Once Supabase is configured, Send test email to myself
   sends one test email and records the attempt.

The current local sender is the requested `sardarpiash8@gmail.com`. SMTP uses
smtp.gmail.com:587 with STARTTLS. Some cloud hosts block outbound SMTP; if the
connection test fails with a network/port message, deploy on a host that allows
587 or run locally. The app shows friendly errors; it does not silently switch
email providers or send from the other account.

## Workflow

1. Master Profile: enter name/contact/summary and your factual structured sections.
   Use the field editors and Add/Remove entry buttons; all fields are editable.
2. Optional: upload a text PDF or DOCX, let AI propose a structured profile,
   review every field and click Approve imported profile. Approval replaces the
   current profile. Scanned PDFs need external OCR first.
3. Daily Update: save English/Bangla work logs with dates. Suggest profile updates
   proposes changes with source log IDs/evidence. Approve, edit and approve, or
   reject each item. Finish the batch to save approved changes and mark logs processed.
4. Generate: paste JD and company/title. The pipeline separately analyzes the JD,
   matches experience, generates CV, runs Python checks, then writes a cover letter
   and an editable email. All content is saved with a profile snapshot.
5. Edit the CV/cover letter fields in the preview editor. Review the factual claims,
   tick the review checkbox and save before exporting. Contact details come from
   the saved profile snapshot. New applications pick up later profile changes.
6. Download any of the four DOCX/PDF files. CV export/email is blocked when the PDF
   exceeds two pages; shorten it in the editor. DOCX uses Arial and PDF uses Arial
   or its Liberation Sans substitute, then Helvetica as a fallback. They share
   content, font sizes, margins and section layout; pagination can differ by viewer.
7. Send Email: choose application, edit To/CC/subject/body, choose PDF or DOCX,
   download attachment previews, check confirmation, then click Confirm & Send.
8. History: revisit, edit/export applications and inspect email outcomes.

Python checks remove unsupported structured skills/tools, employers/titles,
education and certifications; restore profile dates/contact identifiers; and
flag unsupported numbers. Free text is checked for new numbers and JD skill
leakage, and every changed paragraph/bullet is explicitly flagged for review.
These checks cannot prove that a paraphrased achievement is true or identify every
new proper noun. Human review is required for every application. AI suggestions
from work logs similarly require review; the log text is the evidence.

Email attempts are recorded before sending. If the database is down, sending is
blocked. Accepted sends have a session duplicate guard. SMTP acceptance does not
prove inbox delivery. A network failure after Gmail accepted data can have an
uncertain outcome; check Sent Mail before retrying a failed or pending attempt.

## Deploy on Streamlit Community Cloud

1. Push the source files to a GitHub repository. Keep `.env`, `.venv`, and
   `.streamlit/secrets.toml` out of Git. The example files are safe placeholders.
2. Open https://share.streamlit.io → Create app, choose repository/branch,
   set the entrypoint to `app.py`, and select Python 3.11 or newer.
3. Open Advanced settings → Secrets during creation, or App Settings → Secrets
   after deployment. Paste TOML following `.streamlit/secrets.toml.example`.
   Copy actual secret values privately from your local `.env`; dotenv syntax
   is different from TOML, so wrap TOML string values in quotes.
4. Set APP_PASSWORD, both Supabase values, Gmail values, and your AI keys.
5. Deploy. Sign in, open Settings, and test database/AI/Gmail connections.
6. If SMTP is blocked by the hosting network, CV generation and downloads still
   work; the SMTP email feature requires a host/network that permits Gmail 587.

Do not paste keys into GitHub source or publish the document containing credentials.
See [Streamlit deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
and [secrets management](https://docs.streamlit.io/deploy/concepts/secrets).

## Automated checks

```bash
source .venv/bin/activate
python -m pytest -q
```

Tests cover strict JSON/account fallback, sanitization, unsupported entities and
numbers, reverse chronological order, document rendering/import, daily suggestion
application, SMTP attachment handling, and logged-out/authenticated page rendering.
External calls are mocked in tests. Live Supabase requires your project credentials.

## End-to-end checklist

- [ ] Set APP_PASSWORD; wrong password fails and all pages require login.
- [ ] Run schema.sql, configure server-side Supabase key, and pass database test.
- [ ] Test both accounts for every configured AI provider; fix models/quota as needed.
- [ ] Save a full profile; reload the page and verify all fields persist.
- [ ] Import DOCX and text PDF; inspect the proposed fields; approve only correct facts.
- [ ] Save English and Bangla daily logs; verify dated history.
- [ ] Review a suggestion batch using Approve, Edit and approve, and Reject.
- [ ] Finish review; confirm approved facts persist and logs become processed.
- [ ] Generate an application; review JD analysis, honest gaps and model trace.
- [ ] Insert a fake skill/employer/degree/metric in CV edits; verify removal/warnings.
- [ ] Edit both previews; approve factual review and save; reload in History.
- [ ] Download four files; check fonts, contact, dates, bullets, section order and page counts.
- [ ] Confirm CV over two PDF pages is blocked until shortened.
- [ ] Pass Gmail connection test, then click Send test email to myself and check inbox/log.
- [ ] Prepare a real application email; inspect recipients, message and attachments.
- [ ] Confirm & Send; verify Sent Mail and the database email history.
- [ ] Retry same send in the same session; verify the duplicate guard.
- [ ] Sign out; verify profile data and application pages are inaccessible.
- [ ] Repeat Settings tests after deployment, especially SMTP connectivity.
