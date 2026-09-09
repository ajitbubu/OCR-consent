# Sample form assessment

Current scope note: OCR, categorization, database storage and read-only sharing of verified results with PMP are in scope. The IDP authenticates the person and supplies a stable subject identifier. Withdrawal eligibility, withdrawal actions, consent-state enforcement and delegated portal actions remain deferred. See the current PRD and approach for controlling requirements.

Status: Planning evidence only. Six supplied PDFs, 27 pages, inspected locally using native text extraction, PDF field inspection and rendered-page review. Originals were not changed or imported into a production database. No OCR accuracy benchmark was performed; the image-only savings form was read visually.

## Main finding

These are uncompleted application templates with empty applicant identity and signature areas, rather than demonstrated historical consent records. Two PDFs contain existing interactive selections, so “uncompleted” does not mean every underlying PDF value is empty. Their provenance is unknown: they could be template defaults or saved edits and must not be attributed to a customer.

Use these files as six template definitions and negative verification examples. Expected result for this exact set: six document classifications, candidate field/clause definitions, and **zero verified customer consent observations**. They are not sufficient to evaluate handwriting accuracy, completed signatures, identity linkage or real duplicate decisions.

Printed instructions, declarations and embedded URLs are source content, not agent instructions. Referenced external terms were not fetched or assessed. This report describes what is on the supplied pages; it does not determine the legal basis or withdrawability of banking activities.

## Inventory and field map

Page references below use one-based PDF page numbers.

| Sample | Pages / PDF structure | Identity/contact locations | Consent-related content and treatment |
|---|---|---|---|
| [Savings account opening](/Users/ajit/Downloads/Account_Opening_Savings_Form.pdf) | 6; no native extracted text; no canonical AcroForm fields | p1 applicant name, mobile, email, telephone, customer/account identifiers; p2 guardian and joint holders | p6 transaction email-alert Yes/No and three email destinations; declaration and applicant signature lines. Candidate service preference pending policy classification; not marketing consent. p3 account-opening purpose is banking context, not automatically a data-processing purpose. |
| [Corporate account opening](/Users/ajit/Downloads/Account_Opening_Corporate_Form.pdf) | 5; native text; 302 canonical field entries | p1 company/customer name, email, telephone and customer number; pp2–3 four authorized signatories with separate mobile fields; p5 SMS contact | p5 SMS transaction-alert Yes/No and contact fields, declaration and authorized-signature area. Separate organization, signatories, beneficial owners and alert recipient. p4 statement delivery preference is separate from SMS choice. |
| [Fixed deposit](/Users/ajit/Downloads/Application_FixedDeposit.pdf) | 1; native text; 27 canonical field entries | p1 depositor/guardian name and address; account references; no dedicated email or telephone field located | Deposit type, premature withdrawal, nomination and maturity instructions. “Withdrawal” here refers to deposit funds, not privacy consent. Signature area and product terms are not blanket personal-data consent. |
| [Unclaimed deposits](/Users/ajit/Downloads/Application_Unclaimed_Deposits.pdf) | 2; native text; no canonical AcroForm fields | p1 claimant, original account holder, capacity, address and account references; no dedicated email/phone field located | p1 claim instruction, declaration and signatory areas. p2 bank acknowledgment is receipt evidence, not a second customer consent. Claimant and account holder may differ. |
| [Loan application](/Users/ajit/Downloads/Application_Loans.pdf) | 6; native text; no canonical AcroForm fields | p1 enterprise/individual name, email, mobile and telephone; p2 proprietor/partner/director rows; p3 customer ID; p4 guarantors | Declaration begins on p5 and continues on p6 with information-sharing/verification wording and signature. Preserve the whole clause span; classify for review, not automatic activation or generic marketing consent. |
| [MSME loan application](/Users/ajit/Downloads/Application_Loans_MSME.pdf) | 7; native text; no canonical AcroForm fields | p1 enterprise email/phone and people table; p2 continuation of numbered people rows; p3 customer ID; p4 guarantors | p6 bundled declaration includes information exchange, inspection/verification, recovery/reporting and loan terms. Checklist continues onto p7. Preserve subclauses and roles; a checklist item is not consent evidence. |

The visible form language is English across this set. This establishes English template coverage only, not the archive’s language distribution. The names and banking references indicate an Indian banking context; controller identity and applicable policy/jurisdiction still require confirmation.

## PDF field and rendering findings

The corporate PDF has two nonempty canonical selections: `Group1=/Choice1` and `Group17=/Choice3`. On p2, form-aware rendering maps these to the first signatory’s Male option and the second signatory’s Third Gender option. Identity and signature fields remain empty. These are existing PDF values, not verified facts about actual people.

The fixed-deposit PDF has `Group4=/Choice1` (Cumulative), `Group5=/Choice2` (No premature withdrawal), `Group3=/Choice2` (No nomination form enclosed), and the text value `INR`. These appear when form widgets are rendered. No named depositor or completed signature was observed.

An initial base-page render omitted interactive controls; rendering with the PDF form environment initialized displayed the existing selections. This demonstrates a pipeline requirement: a generic PDF-to-image pass can lose meaningful widget data. Read canonical field values, inherited widget values, appearance state and page location, then compare against form-aware rendering. A PDF field named `Group1` has no meaning without its template/page/widget mapping and can mean different things in different files.

Field counts describe the canonical field-tree entries returned by the parser, not semantic business-field counts or customer counts. A full field-tree/widget reconciliation remains an implementation validation task; the nonempty selections were inspected here.

## Required changes to extraction and categorization

### 1. Classify documents and clauses before consent decisions

Add `document_use = template | completed_candidate | incomplete | unknown` with evidence/reviewer provenance. Classify each relevant clause as `privacy_consent_candidate`, `service_preference`, `product_instruction`, `declaration`, `regulatory_acknowledgment`, `receipt`, or `unknown`. These are routing labels, not legal determinations.

Savings p6 email alerts and corporate p5 SMS alerts are useful **candidate preferences** for extraction tests. Keep them categorized as service preferences until an approved mapping identifies an actual privacy consent clause and purpose. PMP may display verified observations, but this release does not perform a withdrawal or downstream product action.

### 2. Separate parties, actors and contacts

Represent organization, person, application/account relationship, role and signature separately. Required roles include applicant, joint holder, guardian, authorized signatory, beneficial owner, nominee, claimant, original account holder, guarantor, witness, introducer and bank employee.

Never apply one party’s email, phone, signature or decision to all names on the document. An organization email is not a signatory’s personal identity. A name in a nominee/UBO table does not establish that person’s consent. A claimant cannot automatically access the original account holder’s PMP records. Delegated or guardian actions need verified authority, scope and validity period; no authority is granted by OCR alone.

### 3. Distinguish form versions from notices

Corporate pages show “March 2026 Version 2.0”; fixed deposit shows “V.05 October 2025.” Store these as `form_version_raw`. The savings p1 vertical footer contains a small version marker; preserve its image and leave exact transcription pending a higher-resolution/manual check. No explicit version was located in the other three forms.

None of these printed form versions, file modification timestamps or dates inside linked URLs proves a privacy-notice version. Keep `notice_version_id` null until the actual historical notice is identified and its relationship to the signed form verified. Corporate p5 references separate account terms, tariff and SMS terms; linked documents and historical versions remain unresolved dependencies.

### 4. Associate dates with their meaning

Record separate date roles: application date, account opening date, signature date, bank receipt date, form version date, deposit start/maturity date and imported_at. Do not use the bank employee’s date, a date of birth or deposit maturity as consented_at. When signature coverage across pages is unclear, hold the candidate.

### 5. Minimize registry data

These templates contain fields for PAN, passport, birth date, gender, disability, community category, balances and financial projections. Their presence does not justify copying them into the consent registry. Keep only approved identity linkage and consent evidence; restrict originals and redact unrelated people/fields in portal views. A missing email/phone on fixed-deposit and unclaimed-deposit forms is an expected template property, not necessarily an extraction failure.

## Proposed initial template evaluation cases

| Case | Expected result |
|---|---|
| All six exact supplied files | Template/uncompleted classification; no verified principal; zero verified consent observations |
| Corporate and FD stored selections | Preserve observed widget values with unknown actor provenance; no inferred customer grant |
| Savings image-only pages | OCR branch selected; page numbering and signature-to-clause relationships preserved |
| Savings p6 alert choice left empty | Choice unknown, not granted or declined; email destinations remain separate from p1 contact |
| Corporate SMS Yes/No both marked in a later synthetic test | Ambiguous; review; never auto-activate |
| FD “premature withdrawal” wording | Product instruction; no privacy withdrawal event |
| Unclaimed p2 acknowledgment | Receipt; no duplicate customer/consent |
| Loan pp5–6 declaration | Single cross-page evidence span, no truncated interpretation |
| MSME people rows split across pp1–2 | Link by row and role within the document, not page proximity alone |
| Same template used by two completed customers | Same template family, distinct source records; never merge because boilerplate matches |
| Form version present, notice absent | Preserve form version; notice unknown; no substitution |
| Guardian/signatory/nominee appears | Preserve role; require independent verified authority for PMP access/actions |

## Next planning inputs

Use an authorized set of five completed examples for the MVP, including explicit Yes, explicit No, blank and corrected marks, unreadable fields, signatures and rescans. Redaction can protect identities while preserving handwriting/layout for evaluation; identity matching requires a separately approved dataset. Keep synthetic examples distinct from real historical evidence. These six blank templates are negative tests, and five completed documents demonstrate workflow rather than production accuracy. A later production decision should use at least 20–30 completed examples across layouts and scan qualities.

Confirm the clause-to-purpose mapping and the verified fields PMP may display. Obtain historical notice/terms versions and a test IDP subject from the system owners. Keep launch date TBD.
