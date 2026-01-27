"""Integration tests for Forms service."""

import pytest


@pytest.mark.integration
class TestFormsService:
    """Integration tests for FormsService."""

    @pytest.fixture
    def test_form(self, google_forms):
        """Create a test form and clean it up after."""
        form = google_forms.forms.create_form("Test_EasyGoogleAPI_Form")
        yield form
        # Note: Forms API can't delete, would need Drive API

    def test_create_form(self, google_forms):
        """Test creating a form."""
        form = google_forms.forms.create_form("Test_Create_Form")
        assert "formId" in form
        assert form["info"]["title"] == "Test_Create_Form"

    def test_get_form(self, google_forms, test_form):
        """Test getting a form."""
        form = google_forms.forms.get_form(test_form["formId"])
        assert "formId" in form
        assert "info" in form

    def test_list_responses_empty(self, google_forms, test_form):
        """Test listing responses (empty form)."""
        responses = google_forms.forms.list_responses(test_form["formId"])
        assert isinstance(responses, list)
        # New form should have no responses
        assert len(responses) == 0

    def test_batch_update_add_question(self, google_forms, test_form):
        """Test adding a question via batch update."""
        form_id = test_form["formId"]

        requests = [
            {
                "createItem": {
                    "item": {
                        "title": "What is your name?",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "textQuestion": {
                                    "paragraph": False,
                                },
                            }
                        },
                    },
                    "location": {"index": 0},
                }
            }
        ]

        result = google_forms.forms.batch_update(form_id, requests)
        assert "replies" in result

        # Verify question was added
        form = google_forms.forms.get_form(form_id)
        assert "items" in form
        assert len(form["items"]) > 0
