from app.categorize import categorize


def field_map(result):
    return {field["name"]: field for field in result["fields"]}


def test_labels_explicit_values_and_keeps_evidence():
    result = categorize(
        [
            {
                "number": 1,
                "native_text": """
                Consent Form
                Name: Ada Lovelace
                Email: ADA@example.com
                Phone: +1 202-555-0123
                Purpose: Product updates
                Privacy Notice Version: 3.2
                I consent: Yes
                Signature
                """,
                "text": "",
                "confidence": 96.0,
                "widgets": [],
            }
        ]
    )

    fields = field_map(result)
    assert fields["name"]["value"] == "Ada Lovelace"
    assert fields["email"]["value"] == "ada@example.com"
    assert fields["phone"]["value"] == "+1 202-555-0123"
    assert fields["purpose"]["value"] == "Product updates"
    assert fields["notice_version"]["value"] == "3.2"
    assert fields["consent_choice"]["value"] == "yes"
    assert fields["consent"]["page"] == 1
    assert fields["signature"]["value"] is None
    assert fields["signature"]["missing_reason"] == "ambiguous"


def test_blank_labels_do_not_create_customer_data():
    result = categorize(
        [
            {
                "number": 1,
                "native_text": "Name: ______\nEmail: ______\nPhone: ______\nSignature",
                "text": "",
                "confidence": None,
                "widgets": [],
            }
        ]
    )

    fields = field_map(result)
    assert fields["name"]["value"] is None
    assert fields["email"]["value"] is None
    assert fields["phone"]["value"] is None
    assert fields["consent"]["value"] is None
    assert fields["consent_choice"]["value"] is None
    assert fields["signature"]["value"] is None


def test_nonempty_signature_widget_sets_consent_choice():
    result = categorize(
        [
            {
                "number": 2,
                "native_text": "I consent: No\nAuthorized signature",
                "text": "",
                "confidence": None,
                "widgets": [{"name": "ApplicantSignature", "value": "signed-data"}],
            }
        ]
    )

    fields = field_map(result)
    signature = fields["signature"]
    assert signature["value"] == "present"
    assert signature["provenance"] == "pdf_widget"
    assert fields["consent_choice"]["value"] == "yes"
    assert fields["consent_choice"]["raw_value"] == "signature present"
    assert fields["consent_choice"]["page"] == 2
    assert fields["consent_choice"]["provenance"] == "signature_consent_rule"
    assert "configured business rule" in fields["consent_choice"]["evidence"]
    assert "authenticate" in result["warnings"][-1]


def test_recovers_positioned_pdf_values_and_signed_declaration():
    result = categorize(
        [
            {
                "number": 1,
                "native_text": """
                Account Opening Form
                R  A  H  U  L       T  E  S  T  K  U  M  A  R       S  H  A  R  M  A
                R  A  H  U  L  .  T  E  S  T  @  E  X  A  M  P  L  E  .  C  O  M
                """,
                "text": """
                I/We agree to the account terms.
                R.T.Sharma
                Signature of Sole Applicant
                """,
                "confidence": 88.0,
                "widgets": [],
            }
        ]
    )

    fields = field_map(result)
    assert fields["name"]["value"] == "RAHUL TESTKUMAR SHARMA"
    assert fields["email"]["value"] == "rahul.test@example.com"
    assert fields["consent"]["value"] == "I/We agree to the account terms."
    assert fields["signature"]["value"] == "present"
    assert fields["consent_choice"]["value"] == "yes"
    assert fields["consent_choice"]["provenance"] == "signature_consent_rule"
    assert fields["purpose"]["value"] == "Open a savings account"
